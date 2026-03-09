#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线策略
短期均线上穿长期均线买入，下穿卖出
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_strategy import BaseStrategy


class DualMAStrategy(BaseStrategy):
    """双均线策略"""
    
    def __init__(self, parameters: Dict):
        """
        初始化双均线策略
        
        Args:
            parameters: 策略参数
        """
        super().__init__("双均线策略", parameters)
        
        # 策略参数
        self.short_ma = parameters.get('short_ma', 5)  # 短期均线周期
        self.long_ma = parameters.get('long_ma', 20)   # 长期均线周期
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算双均线指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含均线指标的数据
        """
        df = data.copy()
        
        # 计算短期和长期均线
        df[f'ma{self.short_ma}'] = df['close'].rolling(window=self.short_ma).mean()
        df[f'ma{self.long_ma}'] = df['close'].rolling(window=self.long_ma).mean()
        
        # 计算均线交叉信号
        df['ma_cross'] = np.where(df[f'ma{self.short_ma}'] > df[f'ma{self.long_ma}'], 1, 0)
        df['ma_cross_signal'] = df['ma_cross'].diff()
        
        return df
        
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含均线指标的数据
            
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
            
            # 检查短期均线上穿长期均线（金叉）
            if (previous_row[f'ma{self.short_ma}'] < previous_row[f'ma{self.long_ma}'] and
                current_row[f'ma{self.short_ma}'] > current_row[f'ma{self.long_ma}']):
                signal['signal'] = 'BUY'
                signal['reason'] = f'MA{self.short_ma}上穿MA{self.long_ma}，金叉买入'
                
            # 检查短期均线下穿长期均线（死叉）
            elif (previous_row[f'ma{self.short_ma}'] > previous_row[f'ma{self.long_ma}'] and
                  current_row[f'ma{self.short_ma}'] < current_row[f'ma{self.long_ma}']):
                signal['signal'] = 'SELL'
                signal['reason'] = f'MA{self.short_ma}下穿MA{self.long_ma}，死叉卖出'
                
            signals.append(signal)
            
        return signals
        
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        return f"""
        双均线策略
        策略名称：{self.strategy_name}
        策略参数：
          - 短期均线周期：{self.short_ma}
          - 长期均线周期：{self.long_ma}
        
        策略逻辑：
          1. 当短期均线上穿长期均线时，产生买入信号（金叉）
          2. 当短期均线下穿长期均线时，产生卖出信号（死叉）
          3. 适合趋势明显的市场，在震荡市中可能产生频繁交易
        
        优点：
          - 简单易懂，容易实现
          - 能够捕捉主要趋势
          - 参数调整相对简单
        
        缺点：
          - 在震荡市中容易产生假信号
          - 滞后性较强，信号出现时价格已有一定涨幅
          - 无法避免单边趋势中的大幅回撤
        """