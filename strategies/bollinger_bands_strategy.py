#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布林带策略：股价跌破下轨买入，突破上轨卖出"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_strategy import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):

    def __init__(self, parameters: Dict):
        super().__init__("布林带策略", parameters)
        self.bb_period = parameters.get('bb_period', 20)
        self.bb_std = parameters.get('bb_std', 2)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        mean = df['close'].rolling(window=self.bb_period).mean()
        std = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = mean + std * self.bb_std
        df['bb_lower'] = mean - std * self.bb_std
        return df

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []
        for i in range(1, len(data)):
            cur, prev = data.iloc[i], data.iloc[i - 1]
            sig = 'HOLD'

            # 从下轨反弹 → 买入
            if prev['close'] <= prev['bb_lower'] and cur['close'] > cur['bb_lower']:
                sig = 'BUY'
            # 突破上轨 → 卖出
            elif prev['close'] < prev['bb_upper'] and cur['close'] >= cur['bb_upper']:
                sig = 'SELL'
            # 从上轨回调 → 买入
            elif prev['close'] >= prev['bb_upper'] and cur['close'] < cur['bb_upper']:
                sig = 'BUY'
            # 跌破下轨 → 卖出
            elif prev['close'] > prev['bb_lower'] and cur['close'] <= cur['bb_lower']:
                sig = 'SELL'

            signals.append({'date': cur['date'], 'stock_code': cur.get('stock_code', ''),
                            'close': cur['close'], 'signal': sig})
        return signals
