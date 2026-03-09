#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
布林带策略
股价跌破布林带下轨买入，突破上轨卖出
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_strategy import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """布林带策略"""
    
    def __init__(self, parameters: Dict):
        """
        初始化布林带策略
        
        Args:
            parameters: 策略参数
        """
        super().__init__("布林带策略", parameters)
        
        # 策略参数
        self.bb_period = parameters.get('bb_period', 20)  # 布林带周期
        self.bb_std = parameters.get('bb_std', 2)       # 标准差倍数
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算布林带指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含布林带指标的数据
        """
        df = data.copy()
        
        # 计算布林带
        rolling_mean = df['close'].rolling(window=self.bb_period).mean()
        rolling_std = df['close'].rolling(window=self.bb_period).std()
        
        df['bb_middle'] = rolling_mean
        df['bb_upper'] = rolling_mean + (rolling_std * self.bb_std)
        df['bb_lower'] = rolling_mean - (rolling_std * self.bb_std)
        
        # 计算布林带宽度
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 计算价格在布林带中的位置
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 计算布林带突破信号
        df['bb_breakout_up'] = (df['close'] > df['bb_upper']).astype(int)
        df['bb_breakout_down'] = (df['close'] < df['bb_lower']).astype(int)
        
        return df
        
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含布林带指标的数据
            
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
                'reason': ''
            }
            
            # 检查从布林带下轨反弹（买入信号）
            if (previous_row['close'] <= previous_row['bb_lower'] and
                current_row['close'] > current_row['bb_lower']):
                signal['signal'] = 'BUY'
                signal['reason'] = f'股价从布林带下轨反弹，买入信号'
                
            # 检查突破布林带上轨（卖出信号）
            elif (previous_row['close'] < previous_row['bb_upper'] and
                  current_row['close'] >= current_row['bb_upper']):
                signal['signal'] = 'SELL'
                signal['reason'] = f'股价突破布林带上轨，卖出信号'
                
            # 检查从布林带上轨回调（买入信号）
            elif (previous_row['close'] >= previous_row['bb_upper'] and
                  current_row['close'] < current_row['bb_upper']):
                signal['signal'] = 'BUY'
                signal['reason'] = f'股价从布林带上轨回调，买入信号'
                
            # 检查跌破布林带下轨（卖出信号）
            elif (previous_row['close'] > previous_row['bb_lower'] and
                  current_row['close'] <= current_row['bb_lower']):
                signal['signal'] = 'SELL'
                signal['reason'] = f'股价跌破布林带下轨，卖出信号'
                
            signals.append(signal)
            
        return signals
        
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        return f"""
        布林带策略
        策略名称：{self.strategy_name}
        策略参数：
          - 布林带周期：{self.bb_period}
          - 标准差倍数：{self.bb_std}
        
        策略逻辑：
          1. 当股价从布林带下轨反弹时，产生买入信号
          2. 当股价突破布林带上轨时，产生卖出信号
          3. 当股价从布林带上轨回调时，产生买入信号
          4. 当股价跌破布林带下轨时，产生卖出信号
        
        优点：
          - 能够捕捉超买超卖机会
          - 适合震荡市行情
          - 有明确的支撑位和阻力位参考
        
        缺点：
          - 在强趋势市场中可能过早反转
          - 需要结合其他指标确认信号
          - 参数设置对结果影响较大
        """