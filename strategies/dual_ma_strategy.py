#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双均线策略：短期均线上穿长期均线买入，下穿卖出"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_strategy import BaseStrategy


class DualMAStrategy(BaseStrategy):

    def __init__(self, parameters: Dict):
        super().__init__("双均线策略", parameters)
        self.short_ma = parameters.get('short_ma', 5)
        self.long_ma = parameters.get('long_ma', 20)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df[f'ma{self.short_ma}'] = df['close'].rolling(window=self.short_ma).mean()
        df[f'ma{self.long_ma}'] = df['close'].rolling(window=self.long_ma).mean()
        return df

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []
        short_col = f'ma{self.short_ma}'
        long_col = f'ma{self.long_ma}'

        for i in range(1, len(data)):
            cur, prev = data.iloc[i], data.iloc[i - 1]
            sig = 'HOLD'

            if prev[short_col] < prev[long_col] and cur[short_col] > cur[long_col]:
                sig = 'BUY'
            elif prev[short_col] > prev[long_col] and cur[short_col] < cur[long_col]:
                sig = 'SELL'

            signals.append({'date': cur['date'], 'stock_code': cur.get('stock_code', ''),
                            'close': cur['close'], 'signal': sig})
        return signals
