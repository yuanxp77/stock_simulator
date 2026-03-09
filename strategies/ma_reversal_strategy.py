#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单均线反转策略
MA60为趋势线，股价跌破MA60且成交量缩量50%买入，突破MA60且成交量放量50%卖出
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_strategy import BaseStrategy


class MAReversalStrategy(BaseStrategy):
    """简单均线反转策略"""
    
    def __init__(self, parameters: Dict):
        """
        初始化简单均线反转策略
        
        Args:
            parameters: 策略参数
        """
        super().__init__("简单均线反转策略", parameters)
        
        # 策略参数
        self.ma_period = parameters.get('ma_period', 60)      # MA趋势线周期
        self.volume_change_pct = parameters.get('volume_change_pct', 0.5)  # 成交量变化比例
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算均线反转策略指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含均线反转指标的数据
        """
        df = data.copy()
        
        # 计算MA60趋势线
        df[f'ma{self.ma_period}'] = df['close'].rolling(window=self.ma_period).mean()
        
        # 计算成交量均线
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # 计算成交量比率
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算价格与MA60的关系
        df['price_above_ma'] = (df['close'] > df[f'ma{self.ma_period}']).astype(int)
        df['price_below_ma'] = (df['close'] < df[f'ma{self.ma_period}']).astype(int)
        
        # 计算价格突破MA60的信号
        df['ma_break_up'] = ((df['close'] > df[f'ma{self.ma_period}']) & 
                           (df['close'].shift(1) <= df[f'ma{self.ma_period}'].shift(1))).astype(int)
        df['ma_break_down'] = ((df['close'] < df[f'ma{self.ma_period}']) & 
                            (df['close'].shift(1) >= df[f'ma{self.ma_period}'].shift(1))).astype(int)
        
        # 计算成交量变化信号
        df['volume_spike'] = (df['volume_ratio'] > (1 + self.volume_change_pct)).astype(int)
        df['volume_drop'] = (df['volume_ratio'] < (1 - self.volume_change_pct)).astype(int)
        
        return df
        
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含均线反转指标的数据
            
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
                f'ma{self.ma_period}': current_row[f'ma{self.ma_period}'],
                'volume_ratio': current_row['volume_ratio']
            }
            
            # 买入条件：股价跌破MA60且成交量缩量50%
            if (previous_row['price_above_ma'] == 1 and 
                current_row['price_below_ma'] == 1 and
                current_row['volume_drop'] == 1 and
                current_row['volume_ratio'] < (1 - self.volume_change_pct)):
                signal['signal'] = 'BUY'
                signal['reason'] = f'股价跌破MA{self.ma_period}且成交量缩量{self.volume_change_pct*100}%，买入信号'
                
            # 卖出条件：股价突破MA60且成交量放量50%
            elif (previous_row['price_below_ma'] == 1 and 
                  current_row['price_above_ma'] == 1 and
                  current_row['volume_spike'] == 1 and
                  current_row['volume_ratio'] > (1 + self.volume_change_pct)):
                signal['signal'] = 'SELL'
                signal['reason'] = f'股价突破MA{self.ma_period}且成交量放量{self.volume_change_pct*100}%，卖出信号'
                
            # 额外买入条件：从MA60下方反弹
            elif (previous_row['price_below_ma'] == 1 and 
                  current_row['price_above_ma'] == 1 and
                  current_row['volume_spike'] == 1):
                signal['signal'] = 'BUY'
                signal['reason'] = f'股价从MA{self.ma_period}下方反弹且成交量放量，买入信号'
                
            # 额外卖出条件：从MA60上方回调
            elif (previous_row['price_above_ma'] == 1 and 
                  current_row['price_below_ma'] == 1 and
                  current_row['volume_drop'] == 1):
                signal['signal'] = 'SELL'
                signal['reason'] = f'股价从MA{self.ma_period}上方回调且成交量缩量，卖出信号'
                
            signals.append(signal)
            
        return signals
        
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        return f"""
        简单均线反转策略
        策略名称：{self.strategy_name}
        策略参数：
          - MA趋势线周期：{self.ma_period}
          - 成交量变化比例：{self.volume_change_pct*100}%
        
        策略逻辑：
          1. 当股价跌破MA{self.ma_period}且成交量缩量{self.volume_change_pct*100}%时，产生买入信号
          2. 当股价突破MA{self.ma_period}且成交量放量{self.volume_change_pct*100}%时，产生卖出信号
          3. 当股价从MA{self.ma_period}下方反弹且成交量放量时，产生买入信号
          4. 当股价从MA{self.ma_period}上方回调且成交量缩量时，产生卖出信号
        
        优点：
          - 结合价格和成交量双重确认
          - MA{self.ma_period}作为长期趋势参考，避免频繁交易
          - 成交量变化提供额外的确认信号
        
        缺点：
          - 在强单边趋势中可能错过主要行情
          - 需要较长的数据周期计算MA{self.ma_period}
          - 成交量信号可能被虚假突破干扰
        """