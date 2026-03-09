#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果分析模块
提供回测结果分析、策略比较、优化建议等功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import os
import json


class StrategyAnalyzer:
    """策略分析器"""
    
    def __init__(self, db_path: str = "stock_simulator.db"):
        """
        初始化策略分析器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.results = None
        
    def load_results(self) -> pd.DataFrame:
        """
        加载回测结果
        
        Returns:
            回测结果DataFrame
        """
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        self.results = pd.read_sql("SELECT * FROM backtest_results ORDER BY backtest_time DESC", conn)
        conn.close()
        
        return self.results
        
    def analyze_performance(self) -> Dict:
        """
        分析策略性能
        
        Returns:
            性能分析结果
        """
        if self.results is None:
            self.load_results()
            
        analysis = {}
        
        # 基本统计
        analysis['basic_stats'] = {
            'total_strategies': len(self.results),
            'total_trades': self.results['total_trades'].sum(),
            'avg_annual_return': self.results['annual_return'].mean(),
            'avg_max_drawdown': self.results['max_drawdown_ratio'].mean(),
            'avg_sharpe_ratio': self.results['sharpe_ratio'].mean(),
            'avg_win_rate': self.results['win_rate'].mean()
        }
        
        # 策略排名
        ranking = self.results.sort_values('annual_return', ascending=False)
        analysis['performance_ranking'] = ranking[['strategy_name', 'annual_return', 'max_drawdown_ratio', 
                                                 'sharpe_ratio', 'win_rate']].to_dict('records')
        
        # 风险收益分析
        analysis['risk_return_analysis'] = self._analyze_risk_return()
        
        # 策略特点分析
        analysis['strategy_characteristics'] = self._analyze_characteristics()
        
        return analysis
        
    def _analyze_risk_return(self) -> Dict:
        """分析风险收益特征"""
        df = self.results
        
        # 计算风险调整收益
        df['risk_adjusted_return'] = df['annual_return'] / df['max_drawdown_ratio']
        df['sortino_ratio'] = df['annual_return'] / df['volatility']
        
        # 找出最优风险收益比策略
        best_risk_return = df.loc[df['risk_adjusted_return'].idxmax()]
        
        return {
            'best_risk_return_strategy': best_risk_return['strategy_name'],
            'best_risk_return_value': best_risk_return['risk_adjusted_return'],
            'avg_risk_adjusted_return': df['risk_adjusted_return'].mean(),
            'best_sortino_strategy': df.loc[df['sortino_ratio'].idxmax()]['strategy_name'],
            'best_sortino_value': df['sortino_ratio'].max()
        }
        
    def _analyze_characteristics(self) -> Dict:
        """分析策略特征"""
        characteristics = {}
        
        for _, row in self.results.iterrows():
            strategy_name = row['strategy_name']
            
            # 根据策略名称判断类型
            if '双均线' in strategy_name:
                strategy_type = '趋势跟踪'
                market_condition = '趋势市场'
            elif '布林带' in strategy_name:
                strategy_type = '均值回归'
                market_condition = '震荡市场'
            elif 'RSI' in strategy_name:
                strategy_type = '震荡交易'
                market_condition = '震荡市场'
            elif '海龟' in strategy_name:
                strategy_type = '趋势跟踪'
                market_condition = '趋势市场'
            elif '均线反转' in strategy_name:
                strategy_type = '反转交易'
                market_condition = '震荡市场'
            else:
                strategy_type = '未知'
                market_condition = '未知'
                
            characteristics[strategy_name] = {
                'type': strategy_type,
                'best_market': market_condition,
                'annual_return': row['annual_return'],
                'max_drawdown': row['max_drawdown_ratio'],
                'sharpe_ratio': row['sharpe_ratio'],
                'win_rate': row['win_rate'],
                'total_trades': row['total_trades']
            }
            
        return characteristics
        
    def generate_recommendations(self) -> Dict:
        """
        生成策略推荐
        
        Returns:
            推荐结果
        """
        if self.results is None:
            self.load_results()
            
        # 计算综合评分
        df = self.results.copy()
        df['score'] = (
            df['annual_return'] * 0.3 +      # 年化收益率权重 30%
            (1 - df['max_drawdown_ratio']) * 0.3 +  # 最大回撤权重 30%
            df['sharpe_ratio'] * 0.2 +      # 夏普比率权重 20%
            df['win_rate'] * 0.2            # 胜率权重 20%
        )
        
        # 排序
        df_sorted = df.sort_values('score', ascending=False)
        
        recommendations = {
            'best_strategy': df_sorted.iloc[0]['strategy_name'],
            'best_score': df_sorted.iloc[0]['score'],
            'second_best': df_sorted.iloc[1]['strategy_name'] if len(df_sorted) > 1 else None,
            'worst_strategy': df_sorted.iloc[-1]['strategy_name'],
            'strategies_ranking': df_sorted[['strategy_name', 'score', 'annual_return', 
                                            'max_drawdown_ratio', 'sharpe_ratio', 'win_rate']].to_dict('records')
        }
        
        # 生成优化建议
        recommendations['optimization_suggestions'] = self._generate_optimization_suggestions(df_sorted)
        
        return recommendations
        
    def _generate_optimization_suggestions(self, df_sorted: pd.DataFrame) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 分析整体表现
        avg_return = df_sorted['annual_return'].mean()
        avg_drawdown = df_sorted['max_drawdown_ratio'].mean()
        avg_sharpe = df_sorted['sharpe_ratio'].mean()
        
        if avg_return < 0.1:  # 年化收益率低于10%
            suggestions.append("整体年化收益率偏低，建议考虑调整策略参数或尝试其他策略")
            
        if avg_drawdown > 0.2:  # 最大回撤超过20%
            suggestions.append("整体最大回撤较大，建议加强风险管理，设置止损机制")
            
        if avg_sharpe < 1.0:  # 夏普比率低于1.0
            suggestions.append("整体夏普比率偏低，建议优化策略参数或增加风险控制")
            
        # 分析最佳策略
        best = df_sorted.iloc[0]
        if best['annual_return'] > 0.15 and best['max_drawdown_ratio'] < 0.15:
            suggestions.append(f"最佳策略 {best['strategy_name']} 表现优秀，可作为主要策略使用")
            
        # 分析最差策略
        worst = df_sorted.iloc[-1]
        if worst['annual_return'] < 0.05 or worst['max_drawdown_ratio'] > 0.25:
            suggestions.append(f"策略 {worst['strategy_name']} 表现较差，建议优化参数或考虑淘汰")
            
        # 通用建议
        suggestions.append("建议考虑多策略组合，分散风险")
        suggestions.append("定期回顾策略表现，根据市场变化调整策略")
        suggestions.append("关注交易成本对收益的影响")
        
        return suggestions
        
    def create_performance_report(self, output_file: str = "results/performance_report.md"):
        """
        创建性能报告
        
        Args:
            output_file: 输出文件路径
        """
        if self.results is None:
            self.load_results()
            
        # 分析性能
        performance_analysis = self.analyze_performance()
        recommendations = self.generate_recommendations()
        
        # 生成报告内容
        report = self._generate_report_content(performance_analysis, recommendations)
        
        # 保存报告
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"性能报告已保存到：{output_file}")
        
        return report
        
    def _generate_report_content(self, performance_analysis: Dict, recommendations: Dict) -> str:
        """生成报告内容"""
        report = f"""# 股票模拟交易回测报告

**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**回测周期：** 2019-01-01 至 2024-12-31

## 1. 基本统计信息

### 整体表现
- 策略总数：{performance_analysis['basic_stats']['total_strategies']}
- 总交易次数：{performance_analysis['basic_stats']['total_trades']}
- 平均年化收益率：{performance_analysis['basic_stats']['avg_annual_return']:.2%}
- 平均最大回撤：{performance_analysis['basic_stats']['avg_max_drawdown']:.2%}
- 平均夏普比率：{performance_analysis['basic_stats']['avg_sharpe_ratio']:.2f}
- 平均胜率：{performance_analysis['basic_stats']['avg_win_rate']:.2%}

### 策略排名

| 排名 | 策略名称 | 年化收益率 | 最大回撤 | 夏普比率 | 胜率 |
|------|----------|------------|----------|----------|------|
"""
        
        for i, strategy in enumerate(performance_analysis['performance_ranking'], 1):
            report += f"| {i} | {strategy['strategy_name']} | {strategy['annual_return']:.2%} | {strategy['max_drawdown_ratio']:.2%} | {strategy['sharpe_ratio']:.2f} | {strategy['win_rate']:.2%} |\n"
            
        report += f"""
## 2. 风险收益分析

### 最优风险收益比策略
- 策略名称：{performance_analysis['risk_return_analysis']['best_risk_return_strategy']}
- 风险调整收益：{performance_analysis['risk_return_analysis']['best_risk_return_value']:.2f}
- 索提诺比率最优策略：{performance_analysis['risk_return_analysis']['best_sortino_strategy']}
- 索提诺比率：{performance_analysis['risk_return_analysis']['best_sortino_value']:.2f}

## 3. 策略特点分析

"""
        
        for strategy_name, characteristics in performance_analysis['strategy_characteristics'].items():
            report += f"""### {strategy_name}
- **策略类型：** {characteristics['type']}
- **最佳市场：** {characteristics['best_market']}
- **年化收益率：** {characteristics['annual_return']:.2%}
- **最大回撤：** {characteristics['max_drawdown_ratio']:.2%}
- **夏普比率：** {characteristics['sharpe_ratio']:.2f}
- **胜率：** {characteristics['win_rate']:.2%}
- **总交易次数：** {characteristics['total_trades']}

"""
            
        report += f"""## 4. 推荐策略

### 最佳策略
- **策略名称：** {recommendations['best_strategy']}
- **综合评分：** {recommendations['best_score']:.2f}

### 策略排名
| 排名 | 策略名称 | 综合评分 | 年化收益率 | 最大回撤 | 夏普比率 | 胜率 |
|------|----------|----------|------------|----------|----------|------|
"""
        
        for i, strategy in enumerate(recommendations['strategies_ranking'], 1):
            report += f"| {i} | {strategy['strategy_name']} | {strategy['score']:.2f} | {strategy['annual_return']:.2%} | {strategy['max_drawdown_ratio']:.2%} | {strategy['sharpe_ratio']:.2f} | {strategy['win_rate']:.2%} |\n"
            
        report += f"""
## 5. 优化建议

"""
        
        for suggestion in recommendations['optimization_suggestions']:
            report += f"- {suggestion}\n"
            
        report += f"""
## 6. 总结

本次回测测试了5种不同的量化策略，涵盖了趋势跟踪、均值回归、震荡交易等不同的交易方法。从结果来看，不同策略在不同市场环境下的表现差异较大。

**主要发现：**
1. {recommendations['best_strategy']} 表现最佳，综合评分最高
2. 趋势跟踪策略在单边趋势市场中表现较好
3. 震荡交易策略在震荡市场中表现较好
4. 风险控制对策略表现至关重要

**建议：**
1. 根据市场环境选择合适的策略
2. 考虑多策略组合，分散风险
3. 定期回顾策略表现，及时调整
4. 关注交易成本对收益的影响

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report


def main():
    """主函数"""
    # 创建策略分析器
    analyzer = StrategyAnalyzer()
    
    # 加载结果
    results = analyzer.load_results()
    
    if results.empty:
        print("没有找到回测结果")
        return
        
    # 分析性能
    performance_analysis = analyzer.analyze_performance()
    
    # 生成推荐
    recommendations = analyzer.generate_recommendations()
    
    # 创建报告
    report = analyzer.create_performance_report()
    
    print("分析完成！")
    print(f"最佳策略：{recommendations['best_strategy']}")
    print(f"综合评分：{recommendations['best_score']:.2f}")


if __name__ == "__main__":
    main()