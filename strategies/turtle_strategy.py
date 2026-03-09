#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""海龟交易策略：突破N日最高价买入，跌破M日最低价卖出，带止损"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_strategy import BaseStrategy


class TurtleStrategy(BaseStrategy):

    def __init__(self, parameters: Dict):
        super().__init__("海龟交易策略", parameters)
        self.breakout_period = parameters.get('breakout_period', 20)
        self.exit_period = parameters.get('exit_period', 10)
        self.stop_loss_pct = parameters.get('stop_loss_pct', 0.02)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['high_n'] = df['high'].rolling(window=self.breakout_period).max()
        df['low_m'] = df['low'].rolling(window=self.exit_period).min()
        df['breakout_up'] = (df['close'] > df['high_n'].shift(1)).astype(int)
        df['breakout_down'] = (df['close'] < df['low_m'].shift(1)).astype(int)
        return df

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []
        for i in range(1, len(data)):
            cur, prev = data.iloc[i], data.iloc[i - 1]
            sig = 'HOLD'

            if prev['breakout_up'] == 0 and cur['breakout_up'] == 1:
                sig = 'BUY'
            elif prev['breakout_down'] == 0 and cur['breakout_down'] == 1:
                sig = 'SELL'

            signals.append({'date': cur['date'], 'stock_code': cur.get('stock_code', ''),
                            'close': cur['close'], 'signal': sig})
        return signals

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 position_ratio: float = 0.8, stop_loss: float = None) -> Dict:
        if stop_loss is None:
            stop_loss = self.stop_loss_pct
        return super().backtest(data, initial_capital, position_ratio, stop_loss)
