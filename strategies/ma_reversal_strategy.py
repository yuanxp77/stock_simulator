#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单均线反转策略：MA60+成交量缩放量确认买卖"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_strategy import BaseStrategy


class MAReversalStrategy(BaseStrategy):

    def __init__(self, parameters: Dict):
        super().__init__("简单均线反转策略", parameters)
        self.ma_period = parameters.get('ma_period', 60)
        self.volume_change_pct = parameters.get('volume_change_pct', 0.5)

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        ma_col = f'ma{self.ma_period}'
        df[ma_col] = df['close'].rolling(window=self.ma_period).mean()
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['price_above_ma'] = (df['close'] > df[ma_col]).astype(int)
        df['price_below_ma'] = (df['close'] < df[ma_col]).astype(int)
        df['volume_spike'] = (df['volume_ratio'] > (1 + self.volume_change_pct)).astype(int)
        df['volume_drop'] = (df['volume_ratio'] < (1 - self.volume_change_pct)).astype(int)
        return df

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        signals = []
        for i in range(1, len(data)):
            cur, prev = data.iloc[i], data.iloc[i - 1]
            sig = 'HOLD'

            # 跌破均线 + 缩量 → 买入
            if prev['price_above_ma'] == 1 and cur['price_below_ma'] == 1 and cur['volume_drop'] == 1:
                sig = 'BUY'
            # 突破均线 + 放量 → 卖出
            elif prev['price_below_ma'] == 1 and cur['price_above_ma'] == 1 and cur['volume_spike'] == 1:
                sig = 'SELL'
            # 从均线下方反弹 + 放量 → 买入
            elif prev['price_below_ma'] == 1 and cur['price_above_ma'] == 1 and cur['volume_spike'] == 1:
                sig = 'BUY'
            # 从均线上方回调 + 缩量 → 卖出
            elif prev['price_above_ma'] == 1 and cur['price_below_ma'] == 1 and cur['volume_drop'] == 1:
                sig = 'SELL'

            signals.append({'date': cur['date'], 'stock_code': cur.get('stock_code', ''),
                            'close': cur['close'], 'signal': sig})
        return signals
