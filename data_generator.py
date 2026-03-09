#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股历史数据生成器
用于生成模拟的A股历史数据，包含开盘价、收盘价、最高价、最低价、成交量等
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import json


class StockDataGenerator:
    """A股历史数据生成器"""
    
    def __init__(self, start_date: str = "2019-01-01", end_date: str = "2024-12-31"):
        """
        初始化数据生成器
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.trading_days = self._generate_trading_days()
        
    def _generate_trading_days(self) -> List[datetime]:
        """
        生成交易日历（排除周末和节假日）
        
        Returns:
            交易日列表
        """
        trading_days = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # 排除周末（周六=5，周日=6）
            if current_date.weekday() < 5:
                trading_days.append(current_date)
            current_date += timedelta(days=1)
            
        return trading_days
        
    def generate_stock_data(self, stock_code: str, stock_name: str, 
                          initial_price: float = 100.0, 
                          volatility: float = 0.02) -> pd.DataFrame:
        """
        生成单只股票的历史数据
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            initial_price: 初始价格
            volatility: 波动率
            
        Returns:
            股票历史数据DataFrame
        """
        # 生成基础价格走势
        prices = self._generate_price_series(initial_price, volatility)
        
        # 生成OHLCV数据
        data = []
        for i, date in enumerate(self.trading_days):
            base_price = prices[i]
            
            # 生成日内波动
            high_low_range = base_price * volatility * 1.5
            high = base_price + random.uniform(0, high_low_range)
            low = base_price - random.uniform(0, high_low_range)
            
            # 确保high > low，并且都在合理范围内
            high = max(high, base_price * 1.01)
            low = min(low, base_price * 0.99)
            
            # 开盘价在前一日收盘价基础上随机波动
            if i == 0:
                open_price = initial_price
            else:
                open_price = prices[i-1] * random.uniform(0.98, 1.02)
            
            # 收盘价在开盘价和最高价、最低价之间
            close_price = random.uniform(min(open_price, low), max(open_price, high))
            
            # 生成成交量（基于价格变动和随机因素）
            volume_factor = abs(close_price - open_price) / base_price
            base_volume = 1000000  # 基础成交量
            volume = int(base_volume * (1 + volume_factor * 10) * random.uniform(0.5, 1.5))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'stock_code': stock_code,
                'stock_name': stock_name,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
        return pd.DataFrame(data)
        
    def _generate_price_series(self, initial_price: float, volatility: float) -> List[float]:
        """
        生成价格序列
        
        Args:
            initial_price: 初始价格
            volatility: 波动率
            
        Returns:
            价格序列
        """
        prices = [initial_price]
        
        # 生成趋势（整体上涨趋势）
        trend_strength = 0.0001  # 微弱上涨趋势
        
        for i in range(1, len(self.trading_days)):
            # 基础随机游走
            random_change = np.random.normal(0, volatility)
            
            # 添加趋势
            trend_change = trend_strength
            
            # 添加季节性因素（年末效应）
            month = self.trading_days[i].month
            if month in [12, 1]:  # 年末年初
                seasonal_factor = 0.001
            else:
                seasonal_factor = 0
                
            # 计算新的价格
            new_price = prices[-1] * (1 + random_change + trend_change + seasonal_factor)
            
            # 确保价格不会变成负数
            new_price = max(new_price, 1.0)
            
            prices.append(new_price)
            
        return prices
        
    def generate_multiple_stocks(self, stock_list: List[Dict], 
                                output_file: str = "stock_data.csv") -> pd.DataFrame:
        """
        生成多只股票的历史数据
        
        Args:
            stock_list: 股票信息列表 [{'code': '600519', 'name': '贵州茅台', 'price': 2000}, ...]
            output_file: 输出文件名
            
        Returns:
            合并后的股票数据DataFrame
        """
        all_data = []
        
        for stock_info in stock_list:
            stock_data = self.generate_stock_data(
                stock_info['code'], 
                stock_info['name'],
                stock_info.get('price', 100.0),
                stock_info.get('volatility', 0.02)
            )
            all_data.append(stock_data)
            
        # 合并所有股票数据
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # 保存到CSV文件
        combined_data.to_csv(output_file, index=False, encoding='utf-8')
        print(f"股票数据已保存到: {output_file}")
        
        return combined_data
        
    def generate_index_data(self, index_name: str = "沪深300", 
                          initial_value: float = 3000.0,
                          volatility: float = 0.015) -> pd.DataFrame:
        """
        生成指数数据
        
        Args:
            index_name: 指数名称
            initial_value: 初始值
            volatility: 波动率
            
        Returns:
            指数数据DataFrame
        """
        prices = self._generate_price_series(initial_value, volatility)
        
        data = []
        for i, date in enumerate(self.trading_days):
            base_price = prices[i]
            
            # 生成日内波动
            high_low_range = base_price * volatility * 1.2
            high = base_price + random.uniform(0, high_low_range)
            low = base_price - random.uniform(0, high_low_range)
            
            # 开盘价
            if i == 0:
                open_price = initial_value
            else:
                open_price = prices[i-1] * random.uniform(0.995, 1.005)
            
            # 收盘价
            close_price = random.uniform(min(open_price, low), max(open_price, high))
            
            # 指数成交量通常很大
            volume = int(10000000 * random.uniform(0.8, 1.2))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'index_name': index_name,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
        return pd.DataFrame(data)
        
    def add_market_events(self, data: pd.DataFrame, event_prob: float = 0.01) -> pd.DataFrame:
        """
        添加市场事件（如涨停、跌停等）
        
        Args:
            data: 原始数据
            event_prob: 事件概率
            
        Returns:
            添加事件后的数据
        """
        data = data.copy()
        
        for i in range(len(data)):
            if random.random() < event_prob:
                # 10%的概率发生特殊事件
                event_type = random.choice(['涨停', '跌停', '大阳线', '大阴线'])
                
                if event_type == '涨停':
                    data.loc[i, 'high'] = data.loc[i, 'open'] * 1.10
                    data.loc[i, 'low'] = data.loc[i, 'open'] * 1.09
                    data.loc[i, 'close'] = data.loc[i, 'open'] * 1.10
                elif event_type == '跌停':
                    data.loc[i, 'high'] = data.loc[i, 'open'] * 0.91
                    data.loc[i, 'low'] = data.loc[i, 'open'] * 0.90
                    data.loc[i, 'close'] = data.loc[i, 'open'] * 0.90
                elif event_type == '大阳线':
                    data.loc[i, 'close'] = data.loc[i, 'open'] * 1.08
                elif event_type == '大阴线':
                    data.loc[i, 'close'] = data.loc[i, 'open'] * 0.92
                    
        return data


# 测试数据生成器
if __name__ == "__main__":
    # 创建数据生成器
    generator = StockDataGenerator("2019-01-01", "2024-12-31")
    
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
    stock_data = generator.generate_multiple_stocks(stock_list, "stock_data.csv")
    
    # 生成指数数据
    index_data = generator.generate_index_data("沪深300", 3000, 0.015)
    index_data.to_csv("index_data.csv", index=False, encoding='utf-8')
    
    print("数据生成完成！")
    print(f"股票数据行数: {len(stock_data)}")
    print(f"指数数据行数: {len(index_data)}")
    
    # 显示数据样本
    print("\n股票数据样本:")
    print(stock_data.head())
    
    print("\n指数数据样本:")
    print(index_data.head())