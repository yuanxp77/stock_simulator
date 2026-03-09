#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股票回测系统主程序：获取数据 → 执行回测 → 输出报告"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from datetime import datetime
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

    def fetch_data(self, start_date: str = "2020-01-01", end_date: str = None):
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"获取真实数据：{start_date} 至 {end_date}")
        os.makedirs("data", exist_ok=True)

        generator = StockDataGenerator(start_date, end_date)
        stock_list = [
            {'code': '600519', 'name': '贵州茅台'},
            {'code': '000858', 'name': '五粮液'},
            {'code': '601318', 'name': '中国平安'},
            {'code': '600036', 'name': '招商银行'},
            {'code': '000333', 'name': '美的集团'},
            {'code': '600276', 'name': '恒瑞医药'},
            {'code': '601888', 'name': '中国中免'},
            {'code': '600887', 'name': '伊利股份'},
            {'code': '000651', 'name': '格力电器'},
            {'code': '600028', 'name': '中国石化'},
        ]
        stock_data = generator.generate_multiple_stocks(stock_list, "data/stock_data.csv")

        index_data = generator.generate_index_data("沪深300")
        index_data.to_csv("data/index_data.csv", index=False, encoding='utf-8')
        logger.info("数据获取完成")
        return stock_data, index_data

    # ── 策略初始化 ──

    def initialize_strategies(self):
        self.strategies = {
            '双均线策略': DualMAStrategy({'short_ma': 5, 'long_ma': 20}),
            '布林带策略': BollingerBandsStrategy({'bb_period': 20, 'bb_std': 2}),
            'RSI超买超卖策略': RSIStrategy({'rsi_period': 14, 'oversold': 30, 'overbought': 70}),
            '海龟交易策略': TurtleStrategy({'breakout_period': 20, 'exit_period': 10, 'stop_loss_pct': 0.02}),
            '简单均线反转策略': MAReversalStrategy({'ma_period': 60, 'volume_change_pct': 0.5}),
        }
        logger.info(f"已初始化 {len(self.strategies)} 个策略")

    # ── 回测执行 ──

    def run_backtest(self, stock_code: str = '600519', start_date: str = '2020-01-01',
                     end_date: str = None, initial_capital: float = 100000.0):
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"开始回测：{stock_code}，{start_date} ~ {end_date}")

        try:
            stock_data = pd.read_csv('data/stock_data.csv', dtype={'stock_code': str})
            stock_data = stock_data[stock_data['stock_code'] == stock_code]
            if stock_data.empty:
                logger.error(f"未找到股票 {stock_code} 的数据")
                return
            stock_data['date'] = pd.to_datetime(stock_data['date'])
            stock_data = stock_data[(stock_data['date'] >= start_date) &
                                    (stock_data['date'] <= end_date)].sort_values('date')
            if stock_data.empty:
                logger.error("指定日期范围内无数据")
                return
        except FileNotFoundError:
            logger.error("数据文件不存在，请先获取数据")
            return

        for name, strategy in self.strategies.items():
            logger.info(f"回测策略：{name}")
            try:
                result = strategy.backtest(stock_data, initial_capital)
                self.backtest_results[name] = result
                self._save_result(name, result, start_date, end_date)
                logger.info(f"策略 {name} 完成")
            except Exception as e:
                logger.error(f"策略 {name} 失败：{e}")

    def _save_result(self, name, result, start_date, end_date):
        eq = pd.DataFrame(result['equity_curve'])
        self.db.add_backtest_result(
            strategy_name=name, start_date=start_date, end_date=end_date,
            total_return=result['total_return'], annual_return=result['annual_return'],
            max_drawdown=result['max_drawdown'], max_drawdown_ratio=result['max_drawdown_ratio'],
            win_rate=result['win_rate'], profit_loss_ratio=result['profit_loss_ratio'],
            total_trades=result['total_trades'], winning_trades=result['winning_trades'],
            losing_trades=result['losing_trades'], sharpe_ratio=result['sharpe_ratio'],
            volatility=result['volatility'], final_equity=result['final_equity'],
            max_equity=eq['equity'].max(), min_equity=eq['equity'].min(),
            data_source="akshare真实数据")

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

        # 四宫格：年化收益率、最大回撤、胜率、夏普比率
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

        # 风险收益散点图
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
        """按综合评分排序返回策略推荐"""
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


def main():
    print("股票回测系统")
    print("=" * 50)

    system = StockBacktestSystem()
    try:
        system.initialize_database()
        system.fetch_data()
        system.initialize_strategies()
        system.run_backtest(
            stock_code='600519',
            start_date='2020-01-01',
            end_date=datetime.now().strftime('%Y-%m-%d'),
            initial_capital=100000.0,
        )
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
