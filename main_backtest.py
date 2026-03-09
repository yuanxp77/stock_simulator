#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股票回测系统主程序：获取数据 → 多股票共享资金池回测 → 输出报告"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from datetime import datetime
from itertools import product
import logging
import os
import platform

from database import StockDatabase
from data_generator import StockDataGenerator
from strategies.dual_ma_strategy import DualMAStrategy
from strategies.bollinger_bands_strategy import BollingerBandsStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.ma_reversal_strategy import MAReversalStrategy
import config


STRATEGY_CLASS_MAP = {
    'DualMA': DualMAStrategy,
    'Bollinger': BollingerBandsStrategy,
    'RSI': RSIStrategy,
    'Turtle': TurtleStrategy,
    'MAReversal': MAReversalStrategy,
}


def _setup_chinese_font():
    candidates = {
        'Darwin': ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS'],
        'Windows': ['Microsoft YaHei', 'SimHei'],
    }.get(platform.system(), ['WenQuanYi Micro Hei', 'Noto Sans CJK SC'])
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams['font.sans-serif'] = [name, 'DejaVu Sans']
            break
    plt.rcParams['axes.unicode_minus'] = False

_setup_chinese_font()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockBacktestSystem:

    def __init__(self, db_path: str = "stock_simulator.db"):
        self.db = StockDatabase(db_path)
        self.strategies = {}
        self.backtest_results = {}

    def initialize_database(self):
        self.db.initialize_database()

    # ── 数据获取 ──

    def fetch_data(self):
        start_date = config.START_DATE
        end_date = config.END_DATE or datetime.now().strftime('%Y-%m-%d')
        logger.info(f"获取真实数据：{start_date} 至 {end_date}")
        os.makedirs("data", exist_ok=True)

        generator = StockDataGenerator(start_date, end_date)
        stock_data = generator.generate_multiple_stocks(config.STOCKS, "data/stock_data.csv")

        index_data = generator.generate_index_data("沪深300")
        index_data.to_csv("data/index_data.csv", index=False, encoding='utf-8')
        logger.info("数据获取完成")
        return stock_data, index_data

    # ── 策略初始化 ──

    def initialize_strategies(self):
        for name, cfg in config.STRATEGIES.items():
            cls = STRATEGY_CLASS_MAP.get(cfg['type'])
            if cls is None:
                logger.warning(f"未知策略类型：{cfg['type']}")
                continue
            self.strategies[name] = cls(cfg['params'])
        logger.info(f"已初始化 {len(self.strategies)} 个策略")

    # ── 多股票共享资金池回测 ──

    def run_backtest(self):
        start_date = config.START_DATE
        end_date = config.END_DATE or datetime.now().strftime('%Y-%m-%d')
        initial_capital = config.INITIAL_CAPITAL
        position_ratio = config.POSITION_RATIO
        stock_codes = [s['code'] for s in config.STOCKS]

        logger.info(f"开始多股票回测：{len(stock_codes)} 只股票，{start_date} ~ {end_date}，资金 {initial_capital}")

        try:
            all_data = pd.read_csv('data/stock_data.csv', dtype={'stock_code': str})
            all_data['date'] = pd.to_datetime(all_data['date'])
            all_data = all_data[(all_data['date'] >= start_date) &
                                (all_data['date'] <= end_date)].sort_values('date')
        except FileNotFoundError:
            logger.error("数据文件不存在，请先获取数据")
            return

        available_codes = all_data['stock_code'].unique().tolist()
        missing = set(stock_codes) - set(available_codes)
        if missing:
            logger.warning(f"以下股票无数据，跳过：{missing}")
        stock_codes = [c for c in stock_codes if c in available_codes]
        if not stock_codes:
            logger.error("没有可用的股票数据")
            return

        for strategy_name, strategy in self.strategies.items():
            logger.info(f"回测策略：{strategy_name}（{len(stock_codes)} 只股票）")
            try:
                result = self._run_shared_pool(
                    strategy, all_data, stock_codes,
                    initial_capital, position_ratio,
                )
                result['strategy_name'] = strategy_name
                self.backtest_results[strategy_name] = result
                self._save_result(strategy_name, result, start_date, end_date, stock_codes)
                logger.info(f"策略 {strategy_name} 完成 — 总收益 {result['total_return']:.2%}")
            except Exception as e:
                logger.error(f"策略 {strategy_name} 失败：{e}")
                import traceback
                traceback.print_exc()

    def _run_shared_pool(self, strategy, all_data, stock_codes,
                         initial_capital, position_ratio):
        """
        多股票共享资金池回测：
        1. 对每只股票分别计算指标 & 生成信号
        2. 按日期合并所有股票信号
        3. 用同一个资金池统一执行交易
        """
        # 为每只股票生成信号
        signals_by_stock = {}
        for code in stock_codes:
            stock_df = all_data[all_data['stock_code'] == code].copy().reset_index(drop=True)
            if stock_df.empty:
                continue
            with_indicators = strategy.calculate_indicators(stock_df)
            signals = strategy.generate_signals(with_indicators)
            for sig in signals:
                sig['stock_code'] = code
            signals_by_stock[code] = signals

        # 合并信号按日期排序
        all_signals = []
        for code, sigs in signals_by_stock.items():
            all_signals.extend(sigs)
        if not all_signals:
            return self._empty_result(initial_capital)

        signals_df = pd.DataFrame(all_signals)
        signals_df['date'] = pd.to_datetime(signals_df['date'])
        trading_days = sorted(signals_df['date'].unique())

        cash = initial_capital
        holdings = {}  # stock_code -> {'qty': int, 'cost': float}
        equity_curve = []
        trades = []
        stock_trade_counts = {code: 0 for code in stock_codes}

        for day in trading_days:
            day_signals = signals_df[signals_df['date'] == day]

            # 先处理卖出信号（回收资金）
            for _, sig in day_signals.iterrows():
                code = sig['stock_code']
                if sig['signal'] == 'SELL' and code in holdings:
                    h = holdings[code]
                    price = sig['close']
                    comm, tax = strategy._calculate_fees(price, h['qty'], '卖出')
                    profit = h['qty'] * price - h['qty'] * h['cost'] - comm - tax
                    cash += h['qty'] * price - comm - tax
                    trades.append({
                        'date': day, 'stock_code': code, 'type': '卖出',
                        'price': price, 'quantity': h['qty'], 'profit': profit,
                    })
                    stock_trade_counts[code] += 1
                    del holdings[code]

            # 再处理买入信号
            for _, sig in day_signals.iterrows():
                code = sig['stock_code']
                if sig['signal'] == 'BUY' and code not in holdings:
                    price = sig['close']
                    available = cash * position_ratio
                    qty = int(available / price)
                    if qty <= 0:
                        continue
                    comm, tax = strategy._calculate_fees(price, qty, '买入')
                    total_cost = qty * price + comm + tax
                    if total_cost > cash:
                        continue
                    cash -= total_cost
                    holdings[code] = {'qty': qty, 'cost': price}
                    trades.append({
                        'date': day, 'stock_code': code, 'type': '买入',
                        'price': price, 'quantity': qty, 'profit': 0,
                    })

            # 记录当日权益
            position_value = 0.0
            for code, h in holdings.items():
                code_day = day_signals[day_signals['stock_code'] == code]
                if not code_day.empty:
                    position_value += h['qty'] * code_day.iloc[0]['close']
                else:
                    last_price = signals_df[(signals_df['stock_code'] == code) &
                                            (signals_df['date'] <= day)].iloc[-1]['close']
                    position_value += h['qty'] * last_price

            equity_curve.append({
                'date': day, 'equity': cash + position_value,
                'cash': cash, 'position_value': position_value,
                'num_holdings': len(holdings),
            })

        # 计算最终权益（未平仓按最后价格计）
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        total_return = (final_equity - initial_capital) / initial_capital

        first_date = pd.to_datetime(trading_days[0])
        last_date = pd.to_datetime(trading_days[-1])
        years = (last_date - first_date).days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        sell_profits = [t['profit'] for t in trades if t['type'] == '卖出']
        winning = [p for p in sell_profits if p > 0]
        losing = [p for p in sell_profits if p < 0]
        win_rate = len(winning) / len(sell_profits) if sell_profits else 0.0
        avg_win = np.mean(winning) if winning else 0
        avg_loss = abs(np.mean(losing)) if losing else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

        equity_df = pd.DataFrame(equity_curve)
        cumulative_max = equity_df['equity'].cummax()
        drawdown = cumulative_max - equity_df['equity']
        max_drawdown = drawdown.max()
        max_drawdown_ratio = (drawdown / cumulative_max).max()
        equity_returns = equity_df['equity'].pct_change().dropna()
        volatility = equity_returns.std() * np.sqrt(252) if len(equity_returns) > 0 else 0
        sharpe_ratio = strategy._calculate_sharpe_ratio(equity_returns)

        return {
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'max_drawdown_ratio': max_drawdown_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': len(sell_profits),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'trades': trades,
            'equity_curve': equity_curve,
            'stock_codes': stock_codes,
            'stock_trade_counts': stock_trade_counts,
        }

    def _empty_result(self, initial_capital):
        return {
            'initial_capital': initial_capital,
            'final_equity': initial_capital,
            'total_return': 0, 'annual_return': 0,
            'max_drawdown': 0, 'max_drawdown_ratio': 0,
            'win_rate': 0, 'profit_loss_ratio': 0,
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'volatility': 0, 'sharpe_ratio': 0,
            'trades': [], 'equity_curve': [],
            'stock_codes': [], 'stock_trade_counts': {},
        }

    def _save_result(self, name, result, start_date, end_date, stock_codes):
        eq = pd.DataFrame(result['equity_curve'])
        self.db.add_backtest_result(
            strategy_name=name, start_date=start_date, end_date=end_date,
            total_return=result['total_return'], annual_return=result['annual_return'],
            max_drawdown=result['max_drawdown'], max_drawdown_ratio=result['max_drawdown_ratio'],
            win_rate=result['win_rate'], profit_loss_ratio=result['profit_loss_ratio'],
            total_trades=result['total_trades'], winning_trades=result['winning_trades'],
            losing_trades=result['losing_trades'], sharpe_ratio=result['sharpe_ratio'],
            volatility=result['volatility'], final_equity=result['final_equity'],
            max_equity=eq['equity'].max() if not eq.empty else result['initial_capital'],
            min_equity=eq['equity'].min() if not eq.empty else result['initial_capital'],
            data_source="akshare真实数据",
            stock_codes=','.join(stock_codes))

    # ── 报告 & 可视化 ──

    def generate_report(self, output_file: str = "results/backtest_report.csv"):
        results = self.db.get_backtest_results()
        if not results:
            logger.warning("没有回测结果")
            return None
        df = pd.DataFrame(results)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"报告已保存到：{output_file}")
        return df

    def visualize(self, output_dir: str = "results/visualizations"):
        results = self.db.get_backtest_results()
        if not results:
            return
        os.makedirs(output_dir, exist_ok=True)
        df = pd.DataFrame(results)

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        metrics = [
            ('annual_return', '年化收益率 (%)', 100),
            ('max_drawdown_ratio', '最大回撤 (%)', 100),
            ('win_rate', '胜率 (%)', 100),
            ('sharpe_ratio', '夏普比率', 1),
        ]
        for ax, (col, title, scale) in zip(axes.flatten(), metrics):
            ax.bar(df['strategy_name'], df[col] * scale)
            ax.set_title(title)
            ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/performance_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()

        plt.figure(figsize=(10, 8))
        plt.scatter(df['max_drawdown_ratio'] * 100, df['annual_return'] * 100,
                    s=100, alpha=0.7, c=df['sharpe_ratio'], cmap='viridis')
        for i, name in enumerate(df['strategy_name']):
            plt.annotate(name, (df['max_drawdown_ratio'].iloc[i] * 100,
                                df['annual_return'].iloc[i] * 100),
                         xytext=(5, 5), textcoords='offset points')
        plt.xlabel('最大回撤 (%)')
        plt.ylabel('年化收益率 (%)')
        plt.title('风险收益散点图')
        plt.colorbar(label='夏普比率')
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{output_dir}/risk_return_scatter.png", dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"图表已保存到：{output_dir}")

    def get_ranking(self):
        if not self.backtest_results:
            return {}
        results = self.db.get_backtest_results()
        df = pd.DataFrame(results)
        df['score'] = (df['annual_return'] * 0.3
                       + (1 - df['max_drawdown_ratio']) * 0.3
                       + df['sharpe_ratio'] * 0.2
                       + df['win_rate'] * 0.2)
        df = df.sort_values('score', ascending=False)
        return {
            'best_strategy': df.iloc[0]['strategy_name'],
            'best_score': df.iloc[0]['score'],
            'ranking': df[['strategy_name', 'annual_return', 'max_drawdown_ratio',
                           'sharpe_ratio', 'win_rate', 'score']].to_dict('records'),
        }

    # ── 参数网格搜索优化 ──

    def optimize_params(self):
        """遍历每个策略的参数搜索空间，找到夏普比率最高的参数组合"""
        start_date = config.START_DATE
        end_date = config.END_DATE or datetime.now().strftime('%Y-%m-%d')
        initial_capital = config.INITIAL_CAPITAL
        position_ratio = config.POSITION_RATIO
        stock_codes = [s['code'] for s in config.STOCKS]

        try:
            all_data = pd.read_csv('data/stock_data.csv', dtype={'stock_code': str})
            all_data['date'] = pd.to_datetime(all_data['date'])
            all_data = all_data[(all_data['date'] >= start_date) &
                                (all_data['date'] <= end_date)].sort_values('date')
        except FileNotFoundError:
            logger.error("数据文件不存在，请先获取数据")
            return {}

        available_codes = all_data['stock_code'].unique().tolist()
        stock_codes = [c for c in stock_codes if c in available_codes]
        if not stock_codes:
            logger.error("没有可用的股票数据")
            return {}

        search_space = getattr(config, 'PARAM_SEARCH_SPACE', {})
        if not search_space:
            logger.warning("未配置 PARAM_SEARCH_SPACE，跳过参数优化")
            return {}

        best_params = {}

        for strategy_name, strategy_cfg in config.STRATEGIES.items():
            stype = strategy_cfg['type']
            space = search_space.get(stype)
            if space is None:
                continue

            cls = STRATEGY_CLASS_MAP.get(stype)
            if cls is None:
                continue

            grid = space['grid']
            constraint = space.get('constraint')
            param_names = list(grid.keys())
            param_values = [grid[k] for k in param_names]

            combos = []
            for vals in product(*param_values):
                params = dict(zip(param_names, vals))
                if constraint and not constraint(params):
                    continue
                combos.append(params)

            print(f"\n{strategy_name} — 搜索 {len(combos)} 组参数...")
            results = []
            for i, params in enumerate(combos):
                strategy = cls(params)
                try:
                    result = self._run_shared_pool(
                        strategy, all_data, stock_codes,
                        initial_capital, position_ratio,
                    )
                    results.append({
                        'params': params,
                        'sharpe': result['sharpe_ratio'],
                        'annual_return': result['annual_return'],
                        'max_drawdown_ratio': result['max_drawdown_ratio'],
                        'total_return': result['total_return'],
                        'win_rate': result['win_rate'],
                        'total_trades': result['total_trades'],
                    })
                except Exception as e:
                    logger.warning(f"  参数 {params} 失败: {e}")

                if (i + 1) % 10 == 0:
                    print(f"  进度 {i + 1}/{len(combos)}")

            if not results:
                continue

            results.sort(key=lambda r: r['sharpe'], reverse=True)
            best = results[0]
            best_params[strategy_name] = best['params']

            print(f"  Top-3:")
            for rank, r in enumerate(results[:3], 1):
                param_str = ', '.join(f"{k}={v}" for k, v in r['params'].items())
                print(f"    #{rank} {param_str}  "
                      f"年化{r['annual_return']:.2%}  "
                      f"回撤{r['max_drawdown_ratio']:.2%}  "
                      f"夏普{r['sharpe']:.3f}")
            param_str = ', '.join(f"{k}={v}" for k, v in best['params'].items())
            print(f"  -> 最优: {param_str}")

        return best_params

    def apply_best_params(self, best_params):
        """用优化后的参数重新初始化策略"""
        for strategy_name, strategy_cfg in config.STRATEGIES.items():
            stype = strategy_cfg['type']
            if strategy_name not in best_params:
                continue
            cls = STRATEGY_CLASS_MAP.get(stype)
            if cls is None:
                continue
            self.strategies[strategy_name] = cls(best_params[strategy_name])
        logger.info("已用最优参数重新初始化策略")


def main():
    print("股票回测系统（多股票共享资金池）")
    print("=" * 50)
    print(f"股票：{len(config.STOCKS)} 只")
    print(f"资金：{config.INITIAL_CAPITAL:,.0f}")
    print(f"时段：{config.START_DATE} ~ {config.END_DATE or '今天'}")
    print(f"策略：{len(config.STRATEGIES)} 个")
    print("=" * 50)

    system = StockBacktestSystem()
    try:
        system.initialize_database()
        system.fetch_data()

        # 参数优化
        print("\n" + "=" * 50)
        print("阶段一：参数网格搜索")
        print("=" * 50)
        system.initialize_strategies()
        best_params = system.optimize_params()

        if best_params:
            print("\n" + "=" * 50)
            print("阶段二：用最优参数正式回测")
            print("=" * 50)
            system.apply_best_params(best_params)
        else:
            print("\n跳过参数优化，使用默认参数回测")

        system.run_backtest()
        report_df = system.generate_report()
        system.visualize()
        ranking = system.get_ranking()

        print("\n" + "=" * 50)
        print("回测结果")
        print("=" * 50)
        if report_df is not None and not report_df.empty:
            print(report_df[['strategy_name', 'annual_return', 'max_drawdown_ratio',
                             'sharpe_ratio', 'win_rate', 'total_trades',
                             'final_equity']].to_string(index=False))

        # 每个策略的多股票交易明细
        for name, result in system.backtest_results.items():
            counts = result.get('stock_trade_counts', {})
            active = {k: v for k, v in counts.items() if v > 0}
            if active:
                detail = ', '.join(f"{c}({n}笔)" for c, n in active.items())
                print(f"\n  {name} 交易分布：{detail}")

        if ranking:
            print(f"\n最佳策略：{ranking['best_strategy']}（评分 {ranking['best_score']:.2f}）")
            print("\n策略排名：")
            for i, s in enumerate(ranking['ranking'], 1):
                print(f"  {i}. {s['strategy_name']}  "
                      f"年化{s['annual_return']:.2%}  "
                      f"回撤{s['max_drawdown_ratio']:.2%}  "
                      f"夏普{s['sharpe_ratio']:.2f}")

        print("\n" + "=" * 50)
        print("完成！")
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
