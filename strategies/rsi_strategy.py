#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSI超买超卖策略：RSI<30买入，RSI>70卖出"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):

    def __init__(self, parameters: Dict):
        super().__init__("RSI超买超卖策略", parameters)
        self.rsi_period = parameters.get('rsi_period', 14)
        self.oversold = parameters.get('oversold', 30)
        self.overbought = parameters.get('overbought', 70)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_trend'] = df['rsi'].diff()
        return df

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []
        for i in range(1, len(data)):
            cur, prev = data.iloc[i], data.iloc[i - 1]
            sig = 'HOLD'

            # RSI 从超卖区反弹
            if prev['rsi'] < self.oversold and cur['rsi'] >= self.oversold and cur['rsi_trend'] > 0:
                sig = 'BUY'
            # RSI 进入超买区
            elif prev['rsi'] < self.overbought and cur['rsi'] >= self.overbought:
                sig = 'SELL'
            # RSI 从超买区回调
            elif prev['rsi'] > self.overbought and cur['rsi'] <= self.overbought and cur['rsi_trend'] < 0:
                sig = 'BUY'
            # RSI 进入超卖区
            elif prev['rsi'] > self.oversold and cur['rsi'] <= self.oversold:
                sig = 'SELL'

            signals.append({'date': cur['date'], 'stock_code': cur.get('stock_code', ''),
                            'close': cur['close'], 'signal': sig})
        return signals
