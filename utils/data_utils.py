#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据工具模块
提供数据加载、预处理、分析等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
import json
from datetime import datetime


class DataLoader:
    """数据加载器"""
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir
        self.stock_data = None
        self.index_data = None
        
    def load_stock_data(self, file_path: str = "stock_data.csv") -> pd.DataFrame:
        """
        加载股票数据
        
        Args:
            file_path: 数据文件路径
            
        Returns:
            股票数据DataFrame
        """
        file_path = os.path.join(self.data_dir, file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"股票数据文件不存在：{file_path}")
            
        self.stock_data = pd.read_csv(file_path)
        
        # 数据预处理
        self.stock_data['date'] = pd.to_datetime(self.stock_data['date'])
        self.stock_data = self.stock_data.sort_values(['stock_code', 'date'])
        
        return self.stock_data
        
    def load_index_data(self, file_path: str = "index_data.csv") -> pd.DataFrame:
        """
        加载指数数据
        
        Args:
            file_path: 数据文件路径
            
        Returns:
            指数数据DataFrame
        """
        file_path = os.path.join(self.data_dir, file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"指数数据文件不存在：{file_path}")
            
        self.index_data = pd.read_csv(file_path)
        
        # 数据预处理
        self.index_data['date'] = pd.to_datetime(self.index_data['date'])
        self.index_data = self.index_data.sort_values('date')
        
        return self.index_data
        
    def get_stock_data(self, stock_code: str, start_date: str = None, 
                      end_date: str = None) -> pd.DataFrame:
        """
        获取指定股票的数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指定股票的数据
        """
        if self.stock_data is None:
            self.load_stock_data()
            
        data = self.stock_data[self.stock_data['stock_code'] == stock_code].copy()
        
        if start_date:
            data = data[data['date'] >= start_date]
        if end_date:
            data = data[data['date'] <= end_date]
            
        return data
        
    def get_index_data(self, index_name: str = None, start_date: str = None,
                      end_date: str = None) -> pd.DataFrame:
        """
        获取指定指数的数据
        
        Args:
            index_name: 指数名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指定指数的数据
        """
        if self.index_data is None:
            self.load_index_data()
            
        data = self.index_data.copy()
        
        if index_name:
            data = data[data['index_name'] == index_name]
        if start_date:
            data = data[data['date'] >= start_date]
        if end_date:
            data = data[data['date'] <= end_date]
            
        return data


class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        """初始化数据分析器"""
        pass
        
    def calculate_basic_stats(self, data: pd.DataFrame) -> Dict:
        """
        计算基本统计信息
        
        Args:
            data: 数据DataFrame
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_days': len(data),
            'start_date': data['date'].min(),
            'end_date': data['date'].max(),
            'price_range': {
                'min': data['close'].min(),
                'max': data['close'].max(),
                'mean': data['close'].mean(),
                'std': data['close'].std()
            },
            'volume_stats': {
                'mean': data['volume'].mean(),
                'std': data['volume'].std(),
                'min': data['volume'].min(),
                'max': data['volume'].max()
            },
            'volatility': data['close'].pct_change().std() * np.sqrt(252)
        }
        
        return stats
        
    def calculate_technical_indicators(self, data: pd.DataFrame, 
                                    indicators: List[str] = None) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 原始数据
            indicators: 要计算的指标列表
            
        Returns:
            包含技术指标的数据
        """
        if indicators is None:
            indicators = ['ma5', 'ma20', 'ma60', 'rsi', 'macd']
            
        df = data.copy()
        
        # 移动平均线
        if 'ma5' in indicators:
            df['ma5'] = df['close'].rolling(window=5).mean()
        if 'ma20' in indicators:
            df['ma20'] = df['close'].rolling(window=20).mean()
        if 'ma60' in indicators:
            df['ma60'] = df['close'].rolling(window=60).mean()
            
        # RSI
        if 'rsi' in indicators:
            df['rsi'] = self._calculate_rsi(df['close'])
            
        # MACD
        if 'macd' in indicators:
            df['macd'], df['macd_signal'], df['macd_histogram'] = self._calculate_macd(df['close'])
            
        # 布林带
        if 'bollinger' in indicators:
            df['bb_middle'], df['bb_upper'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
            
        return df
        
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        
        return macd, macd_signal, macd_histogram
        
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2):
        """计算布林带指标"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return sma, upper, lower
        
    def analyze_market_conditions(self, data: pd.DataFrame) -> Dict:
        """
        分析市场条件
        
        Args:
            data: 市场数据
            
        Returns:
            市场条件分析结果
        """
        # 计算收益率
        returns = data['close'].pct_change()
        
        # 计算波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 计算趋势
        ma20 = data['close'].rolling(window=20).mean()
        ma60 = data['close'].rolling(window=60).mean()
        trend = '上涨' if ma20.iloc[-1] > ma60.iloc[-1] else '下跌'
        
        # 计算RSI
        rsi = self._calculate_rsi(data['close'])
        rsi_status = '超买' if rsi.iloc[-1] > 70 else '超卖' if rsi.iloc[-1] < 30 else '正常'
        
        # 计算成交量变化
        volume_ma = data['volume'].rolling(window=20).mean()
        volume_ratio = data['volume'].iloc[-1] / volume_ma.iloc[-1]
        volume_status = '放量' if volume_ratio > 1.2 else '缩量' if volume_ratio < 0.8 else '正常'
        
        return {
            'volatility': volatility,
            'trend': trend,
            'rsi_status': rsi_status,
            'rsi_value': rsi.iloc[-1],
            'volume_status': volume_status,
            'volume_ratio': volume_ratio,
            'current_price': data['close'].iloc[-1],
            'price_change': returns.iloc[-1]
        }


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        """初始化数据验证器"""
        pass
        
    def validate_stock_data(self, data: pd.DataFrame) -> Dict:
        """
        验证股票数据
        
        Args:
            data: 股票数据
            
        Returns:
            验证结果
        """
        issues = []
        
        # 检查必要列
        required_columns = ['date', 'stock_code', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            issues.append(f"缺少必要列：{missing_columns}")
            
        # 检查数据完整性
        if data.isnull().sum().sum() > 0:
            issues.append("数据包含空值")
            
        # 检查价格合理性
        if (data['high'] < data['low']).any():
            issues.append("存在最高价低于最低价的数据")
            
        if (data['close'] < 0).any():
            issues.append("存在负收盘价")
            
        # 检查成交量合理性
        if (data['volume'] < 0).any():
            issues.append("存在负成交量")
            
        # 检查日期连续性
        data_sorted = data.sort_values('date')
        date_diffs = data_sorted['date'].diff().dropna()
        if (date_diffs > pd.Timedelta(days=2)).any():
            issues.append("日期不连续，可能缺少数据")
            
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'data_shape': data.shape,
            'date_range': (data['date'].min(), data['date'].max())
        }
        
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        清理数据
        
        Args:
            data: 原始数据
            
        Returns:
            清理后的数据
        """
        # 删除重复数据
        data = data.drop_duplicates()
        
        # 删除空值
        data = data.dropna()
        
        # 确保数据类型正确
        data['date'] = pd.to_datetime(data['date'])
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
            
        # 删除异常值
        data = data[data['high'] >= data['low']]
        data = data[data['close'] > 0]
        data = data[data['volume'] >= 0]
        
        return data


def create_sample_data():
    """创建示例数据"""
    from data_generator import StockDataGenerator
    
    # 创建数据生成器
    generator = StockDataGenerator("2019-01-01", "2024-12-31")
    
    # 示例股票列表
    stock_list = [
        {'code': '600519', 'name': '贵州茅台', 'price': 2000, 'volatility': 0.015},
        {'code': '000858', 'name': '五粮液', 'price': 150, 'volatility': 0.020},
        {'code': '601318', 'name': '中国平安', 'price': 50, 'volatility': 0.025}
    ]
    
    # 生成数据
    stock_data = generator.generate_multiple_stocks(stock_list, "data/sample_stock_data.csv")
    
    # 生成指数数据
    index_data = generator.generate_index_data("沪深300", 3000, 0.015)
    index_data.to_csv("data/sample_index_data.csv", index=False, encoding='utf-8')
    
    print("示例数据生成完成！")
    
    return stock_data, index_data