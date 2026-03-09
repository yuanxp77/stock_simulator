#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite 数据库操作：建表、写入回测结果、查询"""

import sqlite3
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class StockDatabase:

    def __init__(self, db_path: str = "stock_simulator.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"连接数据库: {db_path}")

    def close(self):
        if self.conn:
            self.conn.close()

    def initialize_database(self):
        """执行 SQL 脚本创建表结构"""
        try:
            with open('stock_simulator.sql', 'r', encoding='utf-8') as f:
                self.conn.cursor().executescript(f.read())
                self.conn.commit()
            print("数据库初始化完成")
        except FileNotFoundError:
            print("SQL脚本文件不存在")
        except Exception as e:
            print(f"初始化数据库失败: {e}")

    def add_backtest_result(self, strategy_name: str, start_date: str, end_date: str,
                            total_return: float, annual_return: float, max_drawdown: float,
                            max_drawdown_ratio: float, win_rate: float, profit_loss_ratio: float,
                            total_trades: int, winning_trades: int, losing_trades: int,
                            sharpe_ratio: float, volatility: float, final_equity: float,
                            max_equity: float, min_equity: float, data_source: str = "akshare") -> int:
        sql = """
        INSERT INTO backtest_results
        (strategy_name, start_date, end_date, total_return, annual_return,
         max_drawdown, max_drawdown_ratio, win_rate, profit_loss_ratio,
         total_trades, winning_trades, losing_trades, sharpe_ratio, volatility,
         final_equity, max_equity, min_equity, data_source, backtest_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (strategy_name, start_date, end_date, total_return, annual_return,
                             max_drawdown, max_drawdown_ratio, win_rate, profit_loss_ratio,
                             total_trades, winning_trades, losing_trades, sharpe_ratio, volatility,
                             final_equity, max_equity, min_equity, data_source))
        self.conn.commit()
        return cursor.rowcount

    def get_backtest_results(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM backtest_results ORDER BY backtest_time DESC")
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
