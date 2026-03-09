#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本
用于验证系统各模块的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import StockDatabase
from data_generator import StockDataGenerator
from strategies.dual_ma_strategy import DualMAStrategy
from strategies.bollinger_bands_strategy import BollingerBandsStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.ma_reversal_strategy import MAReversalStrategy
import pandas as pd
from datetime import datetime


def test_database():
    """测试数据库功能"""
    print("测试数据库功能...")
    
    try:
        # 创建数据库实例
        db = StockDatabase("test_stock.db")
        
        # 初始化数据库
        db.initialize_database()
        
        # 测试获取策略参数
        params = db.get_strategy_parameters("双均线策略")
        print(f"双均线策略参数: {params}")
        
        # 关闭数据库
        db.disconnect()
        
        print("✅ 数据库测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


def test_data_generator():
    """测试数据生成器"""
    print("测试数据生成器...")
    
    try:
        # 创建数据生成器
        generator = StockDataGenerator("2023-01-01", "2023-12-31")
        
        # 生成测试数据
        stock_list = [
            {'code': '600519', 'name': '贵州茅台', 'price': 2000, 'volatility': 0.015},
            {'code': '000858', 'name': '五粮液', 'price': 150, 'volatility': 0.020}
        ]
        
        stock_data = generator.generate_multiple_stocks(stock_list, "test_stock_data.csv")
        
        print(f"生成股票数据: {len(stock_data)} 条记录")
        print(f"数据列: {list(stock_data.columns)}")
        
        # 清理测试文件
        if os.path.exists("test_stock_data.csv"):
            os.remove("test_stock_data.csv")
            
        print("✅ 数据生成器测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据生成器测试失败: {e}")
        return False


def test_strategies():
    """测试策略功能"""
    print("测试策略功能...")
    
    try:
        # 创建测试数据
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        test_data = pd.DataFrame({
            'date': dates,
            'stock_code': '600519',
            'stock_name': '贵州茅台',
            'open': [2000 + i*0.1 for i in range(len(dates))],
            'high': [2050 + i*0.1 for i in range(len(dates))],
            'low': [1950 + i*0.1 for i in range(len(dates))],
            'close': [2020 + i*0.1 for i in range(len(dates))],
            'volume': [1000000 + i*1000 for i in range(len(dates))]
        })
        
        # 测试双均线策略
        dual_ma = DualMAStrategy({'short_ma': 5, 'long_ma': 20})
        dual_ma_result = dual_ma.backtest(test_data)
        print(f"双均线策略回测结果: 年化收益率={dual_ma_result['annual_return']:.2%}")
        
        # 测试布林带策略
        bb = BollingerBandsStrategy({'bb_period': 20, 'bb_std': 2})
        bb_result = bb.backtest(test_data)
        print(f"布林带策略回测结果: 年化收益率={bb_result['annual_return']:.2%}")
        
        # 测试RSI策略
        rsi = RSIStrategy({'rsi_period': 14, 'oversold': 30, 'overbought': 70})
        rsi_result = rsi.backtest(test_data)
        print(f"RSI策略回测结果: 年化收益率={rsi_result['annual_return']:.2%}")
        
        # 测试海龟策略
        turtle = TurtleStrategy({'breakout_period': 20, 'exit_period': 10, 'stop_loss_pct': 0.02})
        turtle_result = turtle.backtest(test_data)
        print(f"海龟策略回测结果: 年化收益率={turtle_result['annual_return']:.2%}")
        
        # 测试均线反转策略
        ma_reversal = MAReversalStrategy({'ma_period': 60, 'volume_change_pct': 0.5})
        ma_reversal_result = ma_reversal.backtest(test_data)
        print(f"均线反转策略回测结果: 年化收益率={ma_reversal_result['annual_return']:.2%}")
        
        print("✅ 策略测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 策略测试失败: {e}")
        return False


def test_integration():
    """集成测试"""
    print("进行集成测试...")
    
    try:
        # 创建数据库
        db = StockDatabase("integration_test.db")
        db.initialize_database()
        
        # 创建数据生成器
        generator = StockDataGenerator("2023-01-01", "2023-12-31")
        
        # 生成测试数据
        stock_list = [
            {'code': '600519', 'name': '贵州茅台', 'price': 2000, 'volatility': 0.015}
        ]
        stock_data = generator.generate_multiple_stocks(stock_list, "integration_test_data.csv")
        
        # 运行回测
        from main_backtest import StockBacktestSystem
        
        backtest_system = StockBacktestSystem("integration_test.db")
        backtest_system.initialize_strategies()
        backtest_system.run_backtest(
            stock_code='600519',
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=100000.0
        )
        
        # 生成报告
        results_df = backtest_system.generate_results_report("integration_test_report.csv")
        
        print(f"集成测试完成，生成 {len(results_df)} 个策略的回测结果")
        
        # 清理测试文件
        test_files = ["integration_test.db", "integration_test_data.csv", "integration_test_report.csv"]
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)
        
        print("✅ 集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("股票模拟交易回测系统 - 测试脚本")
    print("=" * 50)
    
    tests = [
        ("数据库功能", test_database),
        ("数据生成器", test_data_generator),
        ("策略功能", test_strategies),
        ("集成测试", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
        else:
            print(f"测试失败: {test_name}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 50)
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查相关模块。")
        return 1


if __name__ == "__main__":
    sys.exit(main())