#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 akshare 获取 A 股/ETF 真实历史行情（东财接口）"""

import pandas as pd
from typing import Dict, List, Optional
import logging
import time
import config

logger = logging.getLogger(__name__)

STOCK_NAMES = {s['code']: s['name'] for s in config.STOCKS}

_COL_MAP = {'日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume'}
_COLS = ['date', 'open', 'high', 'low', 'close', 'volume']


class StockDataGenerator:

    def __init__(self, start_date: str = "2020-01-01", end_date: str = "2025-12-31"):
        self.start_date = start_date
        self.end_date = end_date
        self._start_fmt = start_date.replace('-', '')
        self._end_fmt = end_date.replace('-', '')

    def _fetch_stock(self, code: str) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                    start_date=self._start_fmt, end_date=self._end_fmt, adjust="qfq")
            if df is not None and not df.empty:
                df = df.rename(columns=_COL_MAP)
                logger.info(f"  股票获取 {code} 成功，{len(df)} 条")
                return df[_COLS]
        except Exception as e:
            logger.debug(f"  股票获取 {code} 失败: {e}")
        return None

    def _fetch_etf(self, code: str) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.fund_etf_hist_em(symbol=code, period="daily",
                                     start_date=self._start_fmt, end_date=self._end_fmt, adjust="qfq")
            if df is not None and not df.empty:
                df = df.rename(columns=_COL_MAP)
                logger.info(f"  ETF获取 {code} 成功，{len(df)} 条")
                return df[_COLS]
        except Exception as e:
            logger.debug(f"  ETF获取 {code} 失败: {e}")
        return None

    def fetch_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """尝试股票接口，失败则尝试 ETF 接口"""
        logger.info(f"获取 {code} ({self.start_date} ~ {self.end_date})...")
        for fn in [self._fetch_stock, self._fetch_etf]:
            df = fn(code)
            if df is not None and not df.empty:
                df['stock_code'] = code
                df['stock_name'] = STOCK_NAMES.get(code, code)
                return df[['date', 'stock_code', 'stock_name'] + _COLS[1:]]
        logger.error(f"无法获取 {code}")
        return None

    def generate_multiple_stocks(self, stock_list: List[Dict],
                                 output_file: str = "stock_data.csv") -> pd.DataFrame:
        all_data, failed = [], []
        for i, info in enumerate(stock_list):
            code, name = info['code'], info.get('name', info['code'])
            STOCK_NAMES[code] = name
            df = self.fetch_stock_data(code)
            if df is not None:
                all_data.append(df)
            else:
                failed.append(f"{code}({name})")
            if i < len(stock_list) - 1:
                time.sleep(0.5)

        if not all_data:
            logger.error("未获取到任何数据")
            return pd.DataFrame()
        if failed:
            logger.warning(f"获取失败: {', '.join(failed)}")

        combined = pd.concat(all_data, ignore_index=True)
        combined.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"数据已保存: {output_file}  共 {len(combined)} 条，覆盖 {len(all_data)} 只股票")
        return combined

    def generate_index_data(self, index_name: str = "沪深300", **_) -> pd.DataFrame:
        """获取指数日线数据"""
        symbol_map = {'沪深300': 'sh000300', '上证指数': 'sh000001',
                      '深证成指': 'sz399001', '创业板指': 'sz399006'}
        try:
            import akshare as ak
            df = ak.stock_zh_index_daily(symbol=symbol_map.get(index_name, 'sh000300'))
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)].copy()
                df['index_name'] = index_name
                logger.info(f"获取 {index_name} 成功，{len(df)} 条")
                return df[['date', 'index_name', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.warning(f"获取 {index_name} 失败: {e}")
        return pd.DataFrame()
