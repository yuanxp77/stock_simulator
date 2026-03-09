#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""akshare 1 分钟 K 线数据源封装"""

import pandas as pd
import logging
import time

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    '时间': 'date', '开盘': 'open', '收盘': 'close',
    '最高': 'high', '最低': 'low', '成交量': 'volume',
}


def is_trading_time() -> bool:
    now = pd.Timestamp.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    morning = pd.Timestamp('09:30').time() <= t <= pd.Timestamp('11:30').time()
    afternoon = pd.Timestamp('13:00').time() <= t <= pd.Timestamp('15:00').time()
    return morning or afternoon


def fetch_latest_bars(stock_code: str, count: int = 120,
                      max_retries: int = 3) -> pd.DataFrame:
    """
    获取指定股票最近 count 根 1 分钟 K 线。
    返回标准列名 DataFrame: date/open/high/low/close/volume/stock_code
    """
    import akshare as ak

    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist_min_em(
                symbol=stock_code, period='1', adjust='qfq',
            )
            if df is None or df.empty:
                logger.warning(f"{stock_code} 返回空数据 (attempt {attempt + 1})")
                time.sleep(2)
                continue

            df = df.rename(columns=COLUMN_MAP)
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
            df['stock_code'] = stock_code
            return df.tail(count).reset_index(drop=True)

        except Exception as e:
            logger.warning(f"{stock_code} 获取失败 (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))

    logger.error(f"{stock_code} 所有重试均失败")
    return pd.DataFrame()
