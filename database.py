#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作类
用于管理股票模拟交易数据库的连接和操作
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os


class StockDatabase:
    """股票模拟交易数据库操作类"""
    
    def __init__(self, db_path: str = "stock_simulator.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.connect()
        
    def connect(self):
        """连接到SQLite数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 返回字典形式的行
            print(f"成功连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            print(f"连接数据库失败: {e}")
            raise
            
    def disconnect(self):
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            print("数据库连接已关闭")
            
    def execute_sql(self, sql: str, params: tuple = None) -> int:
        """
        执行SQL语句
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            受影响的行数
        """
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            self.conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"执行SQL失败: {e}")
            print(f"SQL语句: {sql}")
            if params:
                print(f"参数: {params}")
            raise
            
    def query_sql(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        查询SQL语句
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            查询结果列表（字典形式）
        """
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except sqlite3.Error as e:
            print(f"查询SQL失败: {e}")
            print(f"SQL语句: {sql}")
            if params:
                print(f"参数: {params}")
            raise
            
    def initialize_database(self):
        """初始化数据库，执行SQL脚本"""
        try:
            with open('stock_simulator.sql', 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            cursor = self.conn.cursor()
            cursor.executescript(sql_script)
            self.conn.commit()
            
            print("数据库初始化完成")
        except FileNotFoundError:
            print("SQL脚本文件不存在")
        except Exception as e:
            print(f"初始化数据库失败: {e}")
            
    def get_account_info(self, strategy_name: str) -> Dict:
        """
        获取账户信息
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            账户信息字典
        """
        sql = """
        SELECT * FROM account 
        WHERE strategy_name = ?
        """
        result = self.query_sql(sql, (strategy_name,))
        return result[0] if result else {}
        
    def update_account(self, strategy_name: str, available_cash: float = None, 
                      total_equity: float = None) -> int:
        """
        更新账户信息
        
        Args:
            strategy_name: 策略名称
            available_cash: 可用资金
            total_equity: 总权益
            
        Returns:
            受影响的行数
        """
        sql = """
        UPDATE account 
        SET available_cash = COALESCE(?, available_cash),
            total_equity = COALESCE(?, total_equity),
            last_update_time = CURRENT_TIMESTAMP
        WHERE strategy_name = ?
        """
        params = [available_cash, total_equity, strategy_name]
        return self.execute_sql(sql, tuple(p for p in params if p is not None))
        
    def get_holdings(self, strategy_name: str) -> List[Dict]:
        """
        获取持仓信息
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            持仓信息列表
        """
        sql = """
        SELECT * FROM holdings 
        WHERE strategy_name = ?
        ORDER BY stock_code
        """
        return self.query_sql(sql, (strategy_name,))
        
    def add_holding(self, strategy_name: str, stock_code: str, stock_name: str,
                   quantity: int, avg_cost: float, current_price: float) -> int:
        """
        添加或更新持仓
        
        Args:
            strategy_name: 策略名称
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 持仓数量
            avg_cost: 平均成本
            current_price: 当前价格
            
        Returns:
            受影响的行数
        """
        market_value = quantity * current_price
        unrealized_pnl = market_value - (quantity * avg_cost)
        unrealized_pnl_ratio = unrealized_pnl / (quantity * avg_cost) if quantity * avg_cost > 0 else 0
        
        sql = """
        INSERT OR REPLACE INTO holdings 
        (strategy_name, stock_code, stock_name, quantity, avg_cost, current_price, 
         market_value, unrealized_pnl, unrealized_pnl_ratio, last_update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (strategy_name, stock_code, stock_name, quantity, avg_cost, 
                 current_price, market_value, unrealized_pnl, unrealized_pnl_ratio)
        return self.execute_sql(sql, params)
        
    def update_holding_price(self, strategy_name: str, stock_code: str, current_price: float) -> int:
        """
        更新持仓价格
        
        Args:
            strategy_name: 策略名称
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            受影响的行数
        """
        sql = """
        UPDATE holdings 
        SET current_price = ?, 
            market_value = quantity * ?,
            unrealized_pnl = quantity * ? - (quantity * avg_cost),
            unrealized_pnl_ratio = (quantity * ? - (quantity * avg_cost)) / (quantity * avg_cost),
            last_update_time = CURRENT_TIMESTAMP
        WHERE strategy_name = ? AND stock_code = ?
        """
        params = (current_price, current_price, current_price, current_price, strategy_name, stock_code)
        return self.execute_sql(sql, params)
        
    def add_trade(self, strategy_name: str, stock_code: str, stock_name: str,
                  trade_type: str, direction: str, trade_price: float, 
                  trade_quantity: int, commission: float, stamp_tax: float,
                  profit: float = 0, profit_ratio: float = 0) -> int:
        """
        添加交易记录
        
        Args:
            strategy_name: 策略名称
            stock_code: 股票代码
            stock_name: 股票名称
            trade_type: 交易类型（买入/卖出）
            direction: 买卖方向（开仓/平仓）
            trade_price: 交易价格
            trade_quantity: 交易数量
            commission: 手续费
            stamp_tax: 印花税
            profit: 交易盈亏
            profit_ratio: 交易盈亏比例
            
        Returns:
            受影响的行数
        """
        trade_amount = trade_price * trade_quantity
        total_cost = trade_amount + commission + stamp_tax
        
        sql = """
        INSERT INTO trades 
        (strategy_name, stock_code, stock_name, trade_type, direction, 
         trade_price, trade_quantity, trade_amount, commission, stamp_tax, 
         total_cost, trade_time, trade_date, profit, profit_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, DATE(CURRENT_TIMESTAMP), ?, ?)
        """
        params = (strategy_name, stock_code, stock_name, trade_type, direction,
                 trade_price, trade_quantity, trade_amount, commission, stamp_tax,
                 total_cost, profit, profit_ratio)
        return self.execute_sql(sql, params)
        
    def get_trades(self, strategy_name: str, start_date: str = None, 
                   end_date: str = None) -> List[Dict]:
        """
        获取交易记录
        
        Args:
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易记录列表
        """
        sql = """
        SELECT * FROM trades 
        WHERE strategy_name = ?
        """
        params = [strategy_name]
        
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
            
        sql += " ORDER BY trade_time DESC"
        
        return self.query_sql(sql, tuple(params))
        
    def add_backtest_result(self, strategy_name: str, start_date: str, end_date: str,
                           total_return: float, annual_return: float, max_drawdown: float,
                           max_drawdown_ratio: float, win_rate: float, profit_loss_ratio: float,
                           total_trades: int, winning_trades: int, losing_trades: int,
                           sharpe_ratio: float, volatility: float, final_equity: float,
                           max_equity: float, min_equity: float, data_source: str = "模拟数据") -> int:
        """
        添加回测结果
        
        Args:
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            total_return: 总收益率
            annual_return: 年化收益率
            max_drawdown: 最大回撤
            max_drawdown_ratio: 最大回撤比例
            win_rate: 胜率
            profit_loss_ratio: 盈亏比
            total_trades: 总交易次数
            winning_trades: 盈利交易次数
            losing_trades: 亏损交易次数
            sharpe_ratio: 夏普比率
            volatility: 波动率
            final_equity: 最终权益
            max_equity: 最高权益
            min_equity: 最低权益
            data_source: 数据来源
            
        Returns:
            受影响的行数
        """
        sql = """
        INSERT INTO backtest_results 
        (strategy_name, start_date, end_date, total_return, annual_return, 
         max_drawdown, max_drawdown_ratio, win_rate, profit_loss_ratio,
         total_trades, winning_trades, losing_trades, sharpe_ratio, volatility,
         final_equity, max_equity, min_equity, data_source, backtest_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (strategy_name, start_date, end_date, total_return, annual_return,
                 max_drawdown, max_drawdown_ratio, win_rate, profit_loss_ratio,
                 total_trades, winning_trades, losing_trades, sharpe_ratio, volatility,
                 final_equity, max_equity, min_equity, data_source)
        return self.execute_sql(sql, params)
        
    def get_backtest_results(self) -> List[Dict]:
        """
        获取所有回测结果
        
        Returns:
            回测结果列表
        """
        sql = """
        SELECT * FROM backtest_results 
        ORDER BY backtest_time DESC
        """
        return self.query_sql(sql)
        
    def calculate_fees(self, trade_price: float, trade_quantity: int, trade_type: str) -> Tuple[float, float]:
        """
        计算交易费用（A股规则）
        
        Args:
            trade_price: 交易价格
            trade_quantity: 交易数量
            trade_type: 交易类型（买入/卖出）
            
        Returns:
            (手续费, 印花税)
        """
        trade_amount = trade_price * trade_quantity
        
        # 手续费：双向收取，按0.0003计算，最低5元
        commission = max(trade_amount * 0.0003, 5.0)
        
        # 印花税：仅卖出收取，按0.001计算
        stamp_tax = trade_amount * 0.001 if trade_type == '卖出' else 0.0
        
        return commission, stamp_tax
        
    def get_strategy_parameters(self, strategy_name: str) -> Dict:
        """
        获取策略参数
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略参数字典
        """
        sql = """
        SELECT parameters FROM strategies 
        WHERE strategy_name = ?
        """
        result = self.query_sql(sql, (strategy_name,))
        if result:
            return json.loads(result[0]['parameters'])
        return {}
        
    def update_strategy_parameters(self, strategy_name: str, parameters: Dict) -> int:
        """
        更新策略参数
        
        Args:
            strategy_name: 策略名称
            parameters: 策略参数字典
            
        Returns:
            受影响的行数
        """
        sql = """
        UPDATE strategies 
        SET parameters = ?, last_updated_time = CURRENT_TIMESTAMP
        WHERE strategy_name = ?
        """
        params = (json.dumps(parameters), strategy_name)
        return self.execute_sql(sql, params)


# 测试数据库功能
if __name__ == "__main__":
    # 创建数据库实例
    db = StockDatabase("test_stock.db")
    
    try:
        # 初始化数据库
        db.initialize_database()
        
        # 测试获取账户信息
        account_info = db.get_account_info("初始账户")
        print("账户信息:", account_info)
        
        # 测试获取策略参数
        params = db.get_strategy_parameters("双均线策略")
        print("双均线策略参数:", params)
        
    finally:
        # 关闭数据库连接
        db.disconnect()