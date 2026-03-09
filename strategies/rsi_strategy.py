#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSI超买超卖策略
RSI<30买入，RSI>70卖出
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI超买超卖策略"""
    
    def __init__(self, parameters: Dict):
        """
        初始化RSI策略
        
        Args:
            parameters: 策略参数
        """
        super().__init__("RSI超买超卖策略", parameters)
        
        # 策略参数
        self.rsi_period = parameters.get('rsi_period', 14)  # RSI计算周期
        self.oversold = parameters.get('oversold', 30)     # 超卖阈值
        self.overbought = parameters.get('overbought', 70) # 超买阈值
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含RSI指标的数据
        """
        df = data.copy()
        
        # 计算RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # 计算RSI信号
        df['rsi_oversold'] = (df['rsi'] < self.oversold).astype(int)
        df['rsi_overbought'] = (df['rsi'] > self.overbought).astype(int)
        
        # 计算RSI趋势
        df['rsi_trend'] = df['rsi'].diff()
        
        return df
        
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            RSI序列
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 避免除零错误
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含RSI指标的数据
            
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
                'rsi': current_row['rsi']
            }
            
            # 检查RSI从超卖区反弹（买入信号）
            if (previous_row['rsi'] < self.oversold and 
                current_row['rsi'] >= self.oversold and
                current_row['rsi_trend'] > 0):
                signal['signal'] = 'BUY'
                signal['reason'] = f'RSI从超卖区({self.oversold})反弹，买入信号'
                
            # 检查RSI进入超买区（卖出信号）
            elif (previous_row['rsi'] < self.overbought and 
                  current_row['rsi'] >= self.overbought):
                signal['signal'] = 'SELL'
                signal['reason'] = f'RSI进入超买区({self.overbought})，卖出信号'
                
            # 检查RSI从超买区回调（买入信号）
            elif (previous_row['rsi'] > self.overbought and 
                  current_row['rsi'] <= self.overbought and
                  current_row['rsi_trend'] < 0):
                signal['signal'] = 'BUY'
                signal['reason'] = f'RSI从超买区({self.overbought})回调，买入信号'
                
            # 检查RSI进入超卖区（卖出信号）
            elif (previous_row['rsi'] > self.oversold and 
                  current_row['rsi'] <= self.oversold):
                signal['signal'] = 'SELL'
                signal['reason'] = f'RSI进入超卖区({self.oversold})，卖出信号'
                
            signals.append(signal)
            
        return signals
        
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        return f"""
        RSI超买超卖策略
        策略名称：{self.strategy_name}
        策略参数：
          - RSI计算周期：{self.rsi_period}
          - 超卖阈值：{self.oversold}
          - 超买阈值：{self.overbought}
        
        策略逻辑：
          1. 当RSI从超卖区({self.oversold})反弹时，产生买入信号
          2. 当RSI进入超买区({self.overbought})时，产生卖出信号
          3. 当RSI从超买区回调时，产生买入信号
          4. 当RSI进入超卖区时，产生卖出信号
        
        优点：
          - 能够识别超买超卖状态
          - 适合震荡市行情
          - 有明确的买卖参考点
        
        缺点：
          - 在强趋势市场中可能过早反转
          - RSI可能在超买超卖区持续较长时间
          - 需要结合价格走势确认信号
        """