#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票模拟交易回测系统主程序
集成所有量化策略，进行历史数据回测和结果分析
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import seaborn as sns
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import os
import platform

def _setup_chinese_font():
    system = platform.system()
    if system == 'Darwin':
        candidates = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
    elif system == 'Windows':
        candidates = ['Microsoft YaHei', 'SimHei', 'SimSun']
    else:
        candidates = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Droid Sans Fallback']
    
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams['font.sans-serif'] = [name, 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            return
    plt.rcParams['axes.unicode_minus'] = False

_setup_chinese_font()

# 导入自定义模块
from database import StockDatabase
from data_generator import StockDataGenerator
from strategies.base_strategy import BaseStrategy
from strategies.dual_ma_strategy import DualMAStrategy
from strategies.bollinger_bands_strategy import BollingerBandsStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.ma_reversal_strategy import MAReversalStrategy


class StockBacktestSystem:
    """股票模拟交易回测系统"""
    
    def __init__(self, db_path: str = "stock_simulator.db"):
        """
        初始化回测系统
        
        Args:
            db_path: 数据库文件路径
        """
        self.db = StockDatabase(db_path)
        self.strategies = {}
        self.backtest_results = {}
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def initialize_database(self):
        """初始化数据库"""
        self.db.initialize_database()
        self.logger.info("数据库初始化完成")
        
    def generate_test_data(self, start_date: str = "2019-01-01", end_date: str = "2024-12-31"):
        """
        生成测试数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        self.logger.info(f"生成测试数据：{start_date} 至 {end_date}")
        
        os.makedirs("data", exist_ok=True)
        
        generator = StockDataGenerator(start_date, end_date)
        
        # 沪深300成分股列表（部分）
        stock_list = [
            {'code': '600519', 'name': '贵州茅台', 'price': 2000, 'volatility': 0.015},
            {'code': '000858', 'name': '五粮液', 'price': 150, 'volatility': 0.020},
            {'code': '601318', 'name': '中国平安', 'price': 50, 'volatility': 0.025},
            {'code': '600036', 'name': '招商银行', 'price': 40, 'volatility': 0.018},
            {'code': '000333', 'name': '美的集团', 'price': 60, 'volatility': 0.022},
            {'code': '600276', 'name': '恒瑞医药', 'price': 80, 'volatility': 0.028},
            {'code': '601888', 'name': '中国国旅', 'price': 45, 'volatility': 0.024},
            {'code': '600887', 'name': '伊利股份', 'price': 35, 'volatility': 0.020},
            {'code': '000651', 'name': '格力电器', 'price': 55, 'volatility': 0.026},
            {'code': '600028', 'name': '中国石化', 'price': 6, 'volatility': 0.030}
        ]
        
        # 生成股票数据
        stock_data = generator.generate_multiple_stocks(stock_list, "data/stock_data.csv")
        
        # 生成指数数据
        index_data = generator.generate_index_data("沪深300", 3000, 0.015)
        index_data.to_csv("data/index_data.csv", index=False, encoding='utf-8')
        
        self.logger.info("测试数据生成完成")
        return stock_data, index_data
        
    def initialize_strategies(self):
        """初始化所有策略"""
        self.logger.info("初始化策略...")
        
        # 双均线策略
        self.strategies['双均线策略'] = DualMAStrategy({
            'short_ma': 5,
            'long_ma': 20
        })
        
        # 布林带策略
        self.strategies['布林带策略'] = BollingerBandsStrategy({
            'bb_period': 20,
            'bb_std': 2
        })
        
        # RSI超买超卖策略
        self.strategies['RSI超买超卖策略'] = RSIStrategy({
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70
        })
        
        # 海龟交易策略
        self.strategies['海龟交易策略'] = TurtleStrategy({
            'breakout_period': 20,
            'exit_period': 10,
            'stop_loss_pct': 0.02
        })
        
        # 简单均线反转策略
        self.strategies['简单均线反转策略'] = MAReversalStrategy({
            'ma_period': 60,
            'volume_change_pct': 0.5
        })
        
        self.logger.info(f"已初始化 {len(self.strategies)} 个策略")
        
    def run_backtest(self, stock_code: str = '600519', start_date: str = '2019-01-01', 
                    end_date: str = '2024-12-31', initial_capital: float = 100000.0):
        """
        运行回测
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
        """
        self.logger.info(f"开始回测：股票 {stock_code}，时间 {start_date} 至 {end_date}")
        
        # 读取股票数据
        try:
            stock_data = pd.read_csv('data/stock_data.csv', dtype={'stock_code': str})
            stock_data = stock_data[stock_data['stock_code'] == stock_code]
            
            if len(stock_data) == 0:
                self.logger.error(f"未找到股票 {stock_code} 的数据")
                return
                
            # 筛选日期范围
            stock_data['date'] = pd.to_datetime(stock_data['date'])
            mask = (stock_data['date'] >= start_date) & (stock_data['date'] <= end_date)
            stock_data = stock_data[mask].sort_values('date')
            
            if len(stock_data) == 0:
                self.logger.error(f"在指定日期范围内未找到数据")
                return
                
        except FileNotFoundError:
            self.logger.error("数据文件不存在，请先生成测试数据")
            return
            
        # 对每个策略进行回测
        for strategy_name, strategy in self.strategies.items():
            self.logger.info(f"正在回测策略：{strategy_name}")
            
            try:
                # 执行回测
                result = strategy.backtest(stock_data, initial_capital)
                
                # 保存结果
                self.backtest_results[strategy_name] = result
                
                # 保存到数据库
                self.save_backtest_result(strategy_name, result, start_date, end_date)
                
                self.logger.info(f"策略 {strategy_name} 回测完成")
                
            except Exception as e:
                self.logger.error(f"策略 {strategy_name} 回测失败：{e}")
                
    def save_backtest_result(self, strategy_name: str, result: Dict, start_date: str, end_date: str):
        """
        保存回测结果到数据库
        
        Args:
            strategy_name: 策略名称
            result: 回测结果
            start_date: 开始日期
            end_date: 结束日期
        """
        equity_curve = pd.DataFrame(result['equity_curve'])
        
        self.db.add_backtest_result(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            total_return=result['total_return'],
            annual_return=result['annual_return'],
            max_drawdown=result['max_drawdown'],
            max_drawdown_ratio=result['max_drawdown_ratio'],
            win_rate=result['win_rate'],
            profit_loss_ratio=result['profit_loss_ratio'],
            total_trades=result['total_trades'],
            winning_trades=result['winning_trades'],
            losing_trades=result['losing_trades'],
            sharpe_ratio=result['sharpe_ratio'],
            volatility=result['volatility'],
            final_equity=result['final_equity'],
            max_equity=equity_curve['equity'].max(),
            min_equity=equity_curve['equity'].min(),
            data_source="模拟数据"
        )
        
    def generate_results_report(self, output_file: str = "results/backtest_report.csv"):
        """
        生成回测结果报告
        
        Args:
            output_file: 输出文件路径
        """
        self.logger.info("生成回测结果报告...")
        
        # 获取所有回测结果
        results = self.db.get_backtest_results()
        
        if not results:
            self.logger.warning("没有回测结果")
            return
            
        # 转换为DataFrame
        df = pd.DataFrame(results)
        
        # 保存到CSV
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        self.logger.info(f"回测结果报告已保存到：{output_file}")
        return df
        
    def visualize_results(self, output_dir: str = "results/visualizations"):
        """
        可视化回测结果
        
        Args:
            output_dir: 输出目录
        """
        self.logger.info("生成可视化图表...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取回测结果
        results = self.db.get_backtest_results()
        
        if not results:
            self.logger.warning("没有回测结果")
            return
            
        # 创建对比图表
        self._create_performance_comparison_chart(results, output_dir)
        self._create_risk_return_chart(results, output_dir)
        self._create_drawdown_chart(results, output_dir)
        
        self.logger.info(f"可视化图表已保存到：{output_dir}")
        
    def _create_performance_comparison_chart(self, results: List[Dict], output_dir: str):
        """创建性能对比图表"""
        df = pd.DataFrame(results)
        
        plt.figure(figsize=(12, 8))
        
        # 年化收益率 vs 总收益率
        plt.subplot(2, 2, 1)
        plt.bar(df['strategy_name'], df['annual_return'] * 100)
        plt.title('年化收益率 (%)')
        plt.xticks(rotation=45)
        plt.ylabel('收益率 (%)')
        
        # 最大回撤
        plt.subplot(2, 2, 2)
        plt.bar(df['strategy_name'], df['max_drawdown_ratio'] * 100)
        plt.title('最大回撤 (%)')
        plt.xticks(rotation=45)
        plt.ylabel('回撤 (%)')
        
        # 胜率
        plt.subplot(2, 2, 3)
        plt.bar(df['strategy_name'], df['win_rate'] * 100)
        plt.title('胜率 (%)')
        plt.xticks(rotation=45)
        plt.ylabel('胜率 (%)')
        
        # 夏普比率
        plt.subplot(2, 2, 4)
        plt.bar(df['strategy_name'], df['sharpe_ratio'])
        plt.title('夏普比率')
        plt.xticks(rotation=45)
        plt.ylabel('夏普比率')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/performance_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_risk_return_chart(self, results: List[Dict], output_dir: str):
        """创建风险收益散点图"""
        df = pd.DataFrame(results)
        
        plt.figure(figsize=(10, 8))
        
        # 年化收益率 vs 最大回撤
        plt.scatter(df['max_drawdown_ratio'] * 100, df['annual_return'] * 100, 
                   s=100, alpha=0.7, c=df['sharpe_ratio'], cmap='viridis')
        
        # 添加标签
        for i, txt in enumerate(df['strategy_name']):
            plt.annotate(txt, (df['max_drawdown_ratio'].iloc[i] * 100, 
                            df['annual_return'].iloc[i] * 100),
                        xytext=(5, 5), textcoords='offset points')
        
        plt.xlabel('最大回撤 (%)')
        plt.ylabel('年化收益率 (%)')
        plt.title('风险收益散点图')
        plt.colorbar(label='夏普比率')
        plt.grid(True, alpha=0.3)
        
        plt.savefig(f"{output_dir}/risk_return_scatter.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_drawdown_chart(self, results: List[Dict], output_dir: str):
        """创建回撤对比图表"""
        df = pd.DataFrame(results)
        
        plt.figure(figsize=(12, 8))
        
        # 最大回撤 vs 最小回撤
        plt.subplot(1, 2, 1)
        plt.bar(df['strategy_name'], df['max_drawdown_ratio'] * 100, alpha=0.7, label='最大回撤')
        plt.bar(df['strategy_name'], df['min_equity'] / df['max_equity'] * 100, alpha=0.7, label='最小回撤')
        plt.title('回撤对比')
        plt.xticks(rotation=45)
        plt.ylabel('回撤 (%)')
        plt.legend()
        
        # 波动率
        plt.subplot(1, 2, 2)
        plt.bar(df['strategy_name'], df['volatility'] * 100)
        plt.title('年化波动率 (%)')
        plt.xticks(rotation=45)
        plt.ylabel('波动率 (%)')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/drawdown_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def get_strategy_recommendations(self) -> Dict:
        """
        获取策略推荐
        
        Returns:
            策略推荐字典
        """
        if not self.backtest_results:
            return {}
            
        # 获取回测结果
        results = self.db.get_backtest_results()
        df = pd.DataFrame(results)
        
        # 计算综合评分
        df['score'] = (
            df['annual_return'] * 0.3 +      # 年化收益率权重 30%
            (1 - df['max_drawdown_ratio']) * 0.3 +  # 最大回撤权重 30%
            df['sharpe_ratio'] * 0.2 +      # 夏普比率权重 20%
            df['win_rate'] * 0.2            # 胜率权重 20%
        )
        
        # 排序并获取推荐
        df_sorted = df.sort_values('score', ascending=False)
        
        recommendations = {
            'best_strategy': df_sorted.iloc[0]['strategy_name'],
            'best_score': df_sorted.iloc[0]['score'],
            'strategies_ranking': df_sorted[['strategy_name', 'annual_return', 'max_drawdown_ratio', 
                                           'sharpe_ratio', 'win_rate', 'score']].to_dict('records'),
            'analysis': self._analyze_strategies(df)
        }
        
        return recommendations
        
    def _analyze_strategies(self, df: pd.DataFrame) -> str:
        """分析各策略特点"""
        analysis = []
        
        # 分析最佳策略
        best = df.iloc[0]
        analysis.append(f"**最佳策略：{best['strategy_name']}**")
        analysis.append(f"- 年化收益率：{best['annual_return']:.2%}")
        analysis.append(f"- 最大回撤：{best['max_drawdown_ratio']:.2%}")
        analysis.append(f"- 夏普比率：{best['sharpe_ratio']:.2f}")
        analysis.append(f"- 胜率：{best['win_rate']:.2%}")
        analysis.append("")
        
        # 分析各策略特点
        analysis.append("**策略特点分析：**")
        
        for _, row in df.iterrows():
            strategy_name = row['strategy_name']
            
            if '双均线' in strategy_name:
                analysis.append(f"- **{strategy_name}**：适合趋势明显的市场，但在震荡市中可能产生频繁交易")
            elif '布林带' in strategy_name:
                analysis.append(f"- **{strategy_name}**：适合震荡市行情，能够捕捉超买超卖机会")
            elif 'RSI' in strategy_name:
                analysis.append(f"- **{strategy_name}**：适合震荡市，能够识别超买超卖状态")
            elif '海龟' in strategy_name:
                analysis.append(f"- **{strategy_name}**：趋势跟踪能力强，适合中长期趋势交易")
            elif '均线反转' in strategy_name:
                analysis.append(f"- **{strategy_name}**：结合价格和成交量双重确认，避免频繁交易")
                
        analysis.append("")
        analysis.append("**优化建议：**")
        analysis.append("1. 可以考虑多策略组合，分散风险")
        analysis.append("2. 根据市场环境调整策略参数")
        analysis.append("3. 加入止损机制控制风险")
        analysis.append("4. 考虑交易成本对收益的影响")
        
        return "\n".join(analysis)


def main():
    """主函数"""
    print("股票模拟交易回测系统")
    print("=" * 50)
    
    # 创建回测系统
    backtest_system = StockBacktestSystem()
    
    try:
        # 初始化数据库
        backtest_system.initialize_database()
        
        # 生成测试数据
        backtest_system.generate_test_data()
        
        # 初始化策略
        backtest_system.initialize_strategies()
        
        # 运行回测
        backtest_system.run_backtest(
            stock_code='600519',  # 贵州茅台
            start_date='2019-01-01',
            end_date='2024-12-31',
            initial_capital=100000.0
        )
        
        # 生成结果报告
        results_df = backtest_system.generate_results_report()
        
        # 可视化结果
        backtest_system.visualize_results()
        
        # 获取策略推荐
        recommendations = backtest_system.get_strategy_recommendations()
        
        # 打印结果
        print("\n" + "=" * 50)
        print("回测结果汇总")
        print("=" * 50)
        
        if results_df is not None and not results_df.empty:
            print(results_df.to_string(index=False))
        else:
            print("没有回测结果数据")
        
        if recommendations:
            print("\n" + "=" * 50)
            print("策略推荐")
            print("=" * 50)
            print(f"最佳策略：{recommendations['best_strategy']}")
            print(f"综合评分：{recommendations['best_score']:.2f}")
            print("\n策略排名：")
            for i, strategy in enumerate(recommendations['strategies_ranking'], 1):
                print(f"{i}. {strategy['strategy_name']} - 年化收益率：{strategy['annual_return']:.2%}, "
                      f"最大回撤：{strategy['max_drawdown_ratio']:.2%}, 夏普比率：{strategy['sharpe_ratio']:.2f}")
            
            print("\n" + "=" * 50)
            print("策略分析")
            print("=" * 50)
            print(recommendations['analysis'])
        
        print("\n" + "=" * 50)
        print("回测完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"回测过程中发生错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()