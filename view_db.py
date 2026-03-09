#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看工具
提供友好的数据库内容查看界面
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime


class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self, db_path="stock_simulator.db"):
        """
        初始化数据库查看器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """连接到数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ 成功连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")
            return False
            
    def disconnect(self):
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            print("🔌 数据库连接已关闭")
            
    def show_tables(self):
        """显示所有表"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print("\n📊 数据库表列表:")
            print("=" * 40)
            for table in tables:
                print(f"• {table[0]}")
            print("=" * 40)
            
        except Exception as e:
            print(f"❌ 获取表列表失败: {e}")
            
    def show_strategies(self):
        """显示策略信息"""
        try:
            df = pd.read_sql("SELECT * FROM strategies", self.conn)
            
            print("\n🎯 策略信息:")
            print("=" * 80)
            print(df.to_string(index=False))
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ 获取策略信息失败: {e}")
            
    def show_accounts(self):
        """显示账户信息"""
        try:
            df = pd.read_sql("SELECT * FROM account", self.conn)
            
            print("\n💰 账户信息:")
            print("=" * 80)
            print(df.to_string(index=False))
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            
    def show_backtest_results(self):
        """显示回测结果"""
        try:
            df = pd.read_sql("SELECT * FROM backtest_results", self.conn)
            
            if df.empty:
                print("\n📊 暂无回测结果")
                return
                
            # 格式化数据
            df['annual_return'] = (df['annual_return'] * 100).round(2).astype(str) + '%'
            df['max_drawdown_ratio'] = (df['max_drawdown_ratio'] * 100).round(2).astype(str) + '%'
            df['win_rate'] = (df['win_rate'] * 100).round(2).astype(str) + '%'
            df['volatility'] = (df['volatility'] * 100).round(2).astype(str) + '%'
            
            print("\n📈 回测结果:")
            print("=" * 100)
            print(df.to_string(index=False))
            print("=" * 100)
            
        except Exception as e:
            print(f"❌ 获取回测结果失败: {e}")
            
    def show_trades(self, limit=10):
        """显示交易记录"""
        try:
            query = f"""
            SELECT strategy_name, stock_code, trade_type, direction, 
                   trade_price, trade_quantity, ROUND(profit, 2) as profit,
                   trade_time
            FROM trades
            ORDER BY trade_time DESC
            LIMIT {limit}
            """
            df = pd.read_sql(query, self.conn)
            
            if df.empty:
                print("\n📝 暂无交易记录")
                return
                
            print(f"\n📝 交易记录 (最新{limit}条):")
            print("=" * 100)
            print(df.to_string(index=False))
            print("=" * 100)
            
        except Exception as e:
            print(f"❌ 获取交易记录失败: {e}")
            
    def show_holdings(self):
        """显示持仓记录"""
        try:
            query = """
            SELECT strategy_name, stock_code, quantity, avg_cost, 
                   current_price, market_value, ROUND(unrealized_pnl, 2) as unrealized_pnl,
                   ROUND(unrealized_pnl_ratio, 4) as unrealized_pnl_ratio
            FROM holdings
            WHERE quantity > 0
            """
            df = pd.read_sql(query, self.conn)
            
            if df.empty:
                print("\n📦 暂无持仓记录")
                return
                
            # 格式化数据
            df['unrealized_pnl_ratio'] = (df['unrealized_pnl_ratio'] * 100).round(2).astype(str) + '%'
            
            print("\n📦 持仓记录:")
            print("=" * 100)
            print(df.to_string(index=False))
            print("=" * 100)
            
        except Exception as e:
            print(f"❌ 获取持仓记录失败: {e}")
            
    def show_strategy_ranking(self):
        """显示策略排名"""
        try:
            query = """
            SELECT strategy_name, 
                   ROUND(annual_return * 100, 2) as annual_return_pct,
                   ROUND(max_drawdown_ratio * 100, 2) as max_drawdown_pct,
                   ROUND(sharpe_ratio, 2) as sharpe_ratio,
                   total_trades,
                   ROUND(win_rate * 100, 2) as win_rate_pct
            FROM backtest_results
            ORDER BY annual_return DESC
            """
            df = pd.read_sql(query, self.conn)
            
            if df.empty:
                print("\n📊 暂无回测结果")
                return
                
            print("\n🏆 策略排名 (按年化收益率):")
            print("=" * 100)
            print(df.to_string(index=False))
            print("=" * 100)
            
        except Exception as e:
            print(f"❌ 获取策略排名失败: {e}")
            
    def show_summary(self):
        """显示数据库摘要"""
        try:
            # 获取各表记录数
            cursor = self.conn.cursor()
            
            # 策略数量
            cursor.execute("SELECT COUNT(*) FROM strategies")
            strategy_count = cursor.fetchone()[0]
            
            # 账户数量
            cursor.execute("SELECT COUNT(*) FROM account")
            account_count = cursor.fetchone()[0]
            
            # 回测结果数量
            cursor.execute("SELECT COUNT(*) FROM backtest_results")
            backtest_count = cursor.fetchone()[0]
            
            # 交易记录数量
            cursor.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]
            
            # 持仓数量
            cursor.execute("SELECT COUNT(*) FROM holdings")
            holding_count = cursor.fetchone()[0]
            
            print("\n📊 数据库摘要:")
            print("=" * 50)
            print(f"策略数量: {strategy_count}")
            print(f"账户数量: {account_count}")
            print(f"回测结果: {backtest_count}")
            print(f"交易记录: {trade_count}")
            print(f"持仓记录: {holding_count}")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 获取数据库摘要失败: {e}")
            
    def interactive_view(self):
        """交互式查看"""
        if not self.connect():
            return
            
        while True:
            print("\n" + "=" * 60)
            print("🗄️  数据库查看工具")
            print("=" * 60)
            print("1. 📊 显示所有表")
            print("2. 🎯 显示策略信息")
            print("3. 💰 显示账户信息")
            print("4. 📈 显示回测结果")
            print("5. 📝 显示交易记录")
            print("6. 📦 显示持仓记录")
            print("7. 🏆 显示策略排名")
            print("8. 📊 显示数据库摘要")
            print("9. 🔍 退出")
            print("=" * 60)
            
            choice = input("请选择操作 (1-9): ").strip()
            
            if choice == '1':
                self.show_tables()
            elif choice == '2':
                self.show_strategies()
            elif choice == '3':
                self.show_accounts()
            elif choice == '4':
                self.show_backtest_results()
            elif choice == '5':
                limit = input("显示多少条记录 (默认10): ").strip()
                limit = int(limit) if limit else 10
                self.show_trades(limit)
            elif choice == '6':
                self.show_holdings()
            elif choice == '7':
                self.show_strategy_ranking()
            elif choice == '8':
                self.show_summary()
            elif choice == '9':
                break
            else:
                print("❌ 无效选择，请重新输入")
                
            input("\n按回车键继续...")
            
        self.disconnect()


def main():
    """主函数"""
    print("🚀 数据库查看工具")
    print("=" * 40)
    
    # 检查数据库文件是否存在
    if not os.path.exists("stock_simulator.db"):
        print("❌ 数据库文件不存在，请先运行系统")
        return
        
    # 创建查看器
    viewer = DatabaseViewer()
    
    # 运行交互式查看
    viewer.interactive_view()


if __name__ == "__main__":
    main()