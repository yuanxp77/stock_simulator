#!/bin/bash

# 数据库查看工具

echo "=== 股票模拟交易数据库查看工具 ==="
echo "1. 查看所有表"
echo "2. 查看策略信息"
echo "3. 查看账户信息"
echo "4. 查看回测结果"
echo "5. 查看交易记录"
echo "6. 查看持仓记录"
echo "7. 查看策略性能排名"
echo "8. 查看策略详细信息"
echo "9. 退出"
echo -n "请选择操作 (1-9): "
read choice

case $choice in
    1)
        echo "=== 所有表 ==="
        sqlite3 stock_simulator.db ".tables"
        ;;
    2)
        echo "=== 策略信息 ==="
        sqlite3 stock_simulator.db "SELECT strategy_id, strategy_name, strategy_type, description FROM strategies;"
        ;;
    3)
        echo "=== 账户信息 ==="
        sqlite3 stock_simulator.db "SELECT account_id, initial_capital, available_cash, total_equity, strategy_name FROM account;"
        ;;
    4)
        echo "=== 回测结果 ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, ROUND(annual_return*100,2) as 年化收益率, ROUND(max_drawdown_ratio*100,2) as 最大回撤, ROUND(sharpe_ratio,2) as 夏普比率, ROUND(win_rate*100,2) as 胜率 FROM backtest_results ORDER BY annual_return DESC;"
        ;;
    5)
        echo "=== 交易记录 (最新10条) ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, stock_code, trade_type, trade_price, trade_quantity, ROUND(profit,2) as 盈亏, trade_time FROM trades ORDER BY trade_time DESC LIMIT 10;"
        ;;
    6)
        echo "=== 持仓记录 ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, stock_code, quantity, avg_cost, current_price, market_value, ROUND(unrealized_pnl,2) as 未实现盈亏 FROM holdings WHERE quantity > 0;"
        ;;
    7)
        echo "=== 策略性能排名 ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, ROUND(annual_return*100,2) as 年化收益率, ROUND(max_drawdown_ratio*100,2) as 最大回撤, ROUND(sharpe_ratio,2) as 夏普比率, total_trades as 交易次数 FROM backtest_results ORDER BY annual_return DESC;"
        ;;
    8)
        echo "=== 策略详细信息 ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, strategy_type, description FROM strategies;"
        echo ""
        echo "=== 策略参数 ==="
        sqlite3 stock_simulator.db "SELECT strategy_name, parameters FROM strategies;"
        ;;
    9)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        ;;
esac

echo ""
echo "按回车键继续..."
read
exec "$0"