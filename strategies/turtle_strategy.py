#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海龟交易策略
突破20日最高价买入，跌破10日最低价卖出，设置2%止损
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_strategy import BaseStrategy


class TurtleStrategy(BaseStrategy):
    """海龟交易策略"""
    
    def __init__(self, parameters: Dict):
        """
        初始化海龟策略
        
        Args:
            parameters: 策略参数
        """
        super().__init__("海龟交易策略", parameters)
        
        # 策略参数
        self.breakout_period = parameters.get('breakout_period', 20)  # 突破周期
        self.exit_period = parameters.get('exit_period', 10)        # 退出周期
        self.stop_loss_pct = parameters.get('stop_loss_pct', 0.02)   # 止损比例
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算海龟策略指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含海龟指标的数据
        """
        df = data.copy()
        
        # 计算20日最高价和10日最低价
        df['high_20'] = df['high'].rolling(window=self.breakout_period).max()
        df['low_10'] = df['low'].rolling(window=self.exit_period).min()
        
        # 计算ATR（平均真实波幅）
        df['atr'] = self._calculate_atr(df, 14)
        
        # 计算止损位
        df['stop_loss'] = df['close'] * (1 - self.stop_loss_pct)
        
        # 计算突破信号
        df['breakout_up'] = (df['close'] > df['high_20'].shift(1)).astype(int)
        df['breakout_down'] = (df['close'] < df['low_10'].shift(1)).astype(int)
        
        return df
        
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算ATR指标（平均真实波幅）
        
        Args:
            data: OHLC数据
            period: 计算周期
            
        Returns:
            ATR序列
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
        
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含海龟指标的数据
            
        Returns:
            交易信号列表
        """
        signals = []
        
        for i in range(1, len(data)):
            current_row = data.iloc[i]
            previous_row = data.iloc[i-1]
            
            signal = {
                'date': current_row['date'],
                'stock_code': current_row.get('stock_code', 'UNKNOWN'),
                'close': current_row['close'],
                'signal': 'HOLD',
                'reason': '',
                'high_20': current_row['high_20'],
                'low_10': current_row['low_10']
            }
            
            # 检查突破20日最高价（买入信号）
            if (previous_row['breakout_up'] == 0 and 
                current_row['breakout_up'] == 1):
                signal['signal'] = 'BUY'
                signal['reason'] = f'突破{self.breakout_period}日最高价，买入信号'
                
            # 检查跌破10日最低价（卖出信号）
            elif (previous_row['breakout_down'] == 0 and 
                  current_row['breakout_down'] == 1):
                signal['signal'] = 'SELL'
                signal['reason'] = f'跌破{self.exit_period}日最低价，卖出信号'
                
            # 检查止损（卖出信号）
            elif (self.is_position and 
                  current_row['close'] <= current_row['stop_loss']):
                signal['signal'] = 'SELL'
                signal['reason'] = f'触发{self.stop_loss_pct*100}%止损，卖出信号'
                
            signals.append(signal)
            
        return signals
        
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 position_ratio: float = 0.8, stop_loss: float = None) -> Dict:
        """
        海龟策略回测（重写以支持止损逻辑）
        
        Args:
            data: 历史数据
            initial_capital: 初始资金
            position_ratio: 仓位比例
            stop_loss: 止损比例（使用策略内置的止损比例）
            
        Returns:
            回测结果
        """
        # 使用策略内置的止损比例
        if stop_loss is None:
            stop_loss = self.stop_loss_pct
            
        return super().backtest(data, initial_capital, position_ratio, stop_loss)
        
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        return f"""
        海龟交易策略
        策略名称：{self.strategy_name}
        策略参数：
          - 突破周期：{self.breakout_period}日
          - 退出周期：{self.exit_period}日
          - 止损比例：{self.stop_loss_pct*100}%
        
        策略逻辑：
          1. 当股价突破{self.breakout_period}日最高价时，产生买入信号
          2. 当股价跌破{self.exit_period}日最低价时，产生卖出信号
          3. 当股价触及{self.stop_loss_pct*100}%止损位时，强制卖出
        
        优点：
          - 趋势跟踪能力强，能够捕捉大行情
          - 有明确的止损机制，控制风险
          - 适合中长期趋势交易
        
        缺点：
          - 在震荡市中可能产生频繁交易
          - 突破信号可能产生假突破
          - 止损可能被短期波动触发
        """