# 数据库查看指南

## 📋 SQLite 基本命令

### 1. 连接到数据库
```bash
# 连接到股票模拟交易数据库
sqlite3 stock_simulator.db

# 如果数据库不存在，会自动创建
```

### 2. 基本数据库操作
```sql
-- 查看所有表
.tables

-- 查看表结构
.schema account
.schema holdings
.schema trades
.schema strategies
.schema backtest_results

-- 查看数据库信息
.database
```

### 3. 查看数据

#### 查看账户信息
```sql
-- 查看所有账户
SELECT * FROM account;

-- 查看特定策略账户
SELECT * FROM account WHERE strategy_name = '双均线策略';
```

#### 查看持仓信息
```sql
-- 查看所有持仓
SELECT * FROM holdings;

-- 查看特定策略持仓
SELECT * FROM holdings WHERE strategy_name = '双均线策略';

-- 查看特定股票持仓
SELECT * FROM holdings WHERE stock_code = '600519';
```

#### 查看交易记录
```sql
-- 查看所有交易记录
SELECT * FROM trades;

-- 查看特定策略交易记录
SELECT * FROM trades WHERE strategy_name = '双均线策略';

-- 查看特定股票交易记录
SELECT * FROM trades WHERE stock_code = '600519';

-- 按时间范围查询
SELECT * FROM trades 
WHERE strategy_name = '双均线策略' 
AND trade_date >= '2023-01-01' 
AND trade_date <= '2023-12-31';
```

#### 查看策略参数
```sql
-- 查看所有策略
SELECT * FROM strategies;

-- 查看特定策略参数
SELECT * FROM strategies WHERE strategy_name = '双均线策略';
```

#### 查看回测结果
```sql
-- 查看所有回测结果
SELECT * FROM backtest_results;

-- 按策略查看回测结果
SELECT * FROM backtest_results WHERE strategy_name = '双均线策略';

-- 按时间范围查看
SELECT * FROM backtest_results 
WHERE start_date >= '2023-01-01' 
AND end_date <= '2023-12-31';

-- 按收益率排序
SELECT * FROM backtest_results 
ORDER BY annual_return DESC;
```

### 4. 数据分析查询

#### 策略性能对比
```sql
-- 查看各策略的年化收益率
SELECT strategy_name, annual_return, max_drawdown_ratio, sharpe_ratio, win_rate
FROM backtest_results
ORDER BY annual_return DESC;

-- 查看收益率超过10%的策略
SELECT strategy_name, annual_return, max_drawdown_ratio
FROM backtest_results
WHERE annual_return > 0.1;
```

#### 交易统计
```sql
-- 查看各策略交易次数
SELECT strategy_name, COUNT(*) as trade_count
FROM trades
GROUP BY strategy_name;

-- 查看各策略盈利交易次数
SELECT strategy_name, 
       SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
       SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades
FROM trades
GROUP BY strategy_name;
```

#### 持仓分析
```sql
-- 查看当前持仓
SELECT strategy_name, stock_code, quantity, avg_cost, current_price, 
       market_value, unrealized_pnl, unrealized_pnl_ratio
FROM holdings
WHERE quantity > 0;

-- 查看持仓市值排名
SELECT strategy_name, stock_code, market_value
FROM holdings
ORDER BY market_value DESC;
```

### 5. 导出数据

#### 导出为CSV
```sql
-- 设置输出模式
.mode csv

-- 导出回测结果
.headers on
.output backtest_results.csv
SELECT * FROM backtest_results;
.output stdout

-- 导出交易记录
.headers on
.output trades.csv
SELECT * FROM trades;
.output stdout

-- 导出持仓记录
.headers on
.output holdings.csv
SELECT * FROM holdings;
.output stdout
```

### 6. 退出数据库
```sql
-- 退出SQLite
.quit
```

## 🎯 实用查询示例

### 1. 查看最佳策略
```sql
SELECT strategy_name, 
       ROUND(annual_return * 100, 2) as annual_return_pct,
       ROUND(max_drawdown_ratio * 100, 2) as max_drawdown_pct,
       ROUND(sharpe_ratio, 2) as sharpe_ratio,
       ROUND(win_rate * 100, 2) as win_rate_pct
FROM backtest_results
ORDER BY annual_return DESC
LIMIT 5;
```

### 2. 查看策略交易频率
```sql
SELECT strategy_name,
       COUNT(*) as total_trades,
       ROUND(AVG(CASE WHEN profit > 0 THEN 1 ELSE 0 END) * 100, 2) as win_rate_pct
FROM trades
GROUP BY strategy_name
ORDER BY total_trades DESC;
```

### 3. 查看资金变化
```sql
SELECT strategy_name,
       final_equity,
       ROUND((final_equity - 100000) / 100000 * 100, 2) as total_return_pct
FROM backtest_results
ORDER BY final_equity DESC;
```

### 4. 查看风险指标
```sql
SELECT strategy_name,
       ROUND(max_drawdown_ratio * 100, 2) as max_drawdown_pct,
       ROUND(volatility * 100, 2) as volatility_pct,
       ROUND(sharpe_ratio, 2) as sharpe_ratio
FROM backtest_results
ORDER BY max_drawdown_ratio ASC;
```

## 🔧 Python 连接数据库

如果你想在Python中查看数据库，可以使用以下代码：

```python
import sqlite3
import pandas as pd

# 连接数据库
conn = sqlite3.connect('stock_simulator.db')

# 查看回测结果
df_backtest = pd.read_sql('SELECT * FROM backtest_results', conn)
print("回测结果：")
print(df_backtest)

# 查看交易记录
df_trades = pd.read_sql('SELECT * FROM trades', conn)
print("\n交易记录：")
print(df_trades.head())

# 查看持仓记录
df_holdings = pd.read_sql('SELECT * FROM holdings', conn)
print("\n持仓记录：")
print(df_holdings.head())

# 关闭连接
conn.close()
```

## 📊 快速查看脚本

创建一个快速查看脚本：

```bash
# 创建查看脚本
cat > view_db.sh << 'EOF'
#!/bin/bash
echo "=== 数据库查看工具 ==="
echo "1. 查看所有表"
echo "2. 查看回测结果"
echo "3. 查看交易记录"
echo "4. 查看持仓记录"
echo "5. 查看策略参数"
echo "6. 退出"
echo -n "请选择操作 (1-6): "
read choice

case $choice in
    1)
        sqlite3 stock_simulator.db ".tables"
        ;;
    2)
        sqlite3 stock_simulator.db "SELECT strategy_name, ROUND(annual_return*100,2) as 年化收益率, ROUND(max_drawdown_ratio*100,2) as 最大回撤, ROUND(sharpe_ratio,2) as 夏普比率 FROM backtest_results ORDER BY annual_return DESC;"
        ;;
    3)
        sqlite3 stock_simulator.db "SELECT strategy_name, stock_code, trade_type, trade_price, trade_quantity, profit FROM trades ORDER BY trade_time DESC LIMIT 10;"
        ;;
    4)
        sqlite3 stock_simulator.db "SELECT strategy_name, stock_code, quantity, avg_cost, current_price, market_value FROM holdings WHERE quantity > 0;"
        ;;
    5)
        sqlite3 stock_simulator.db "SELECT strategy_name, strategy_type, description FROM strategies;"
        ;;
    6)
        exit 0
        ;;
    *)
        echo "无效选择"
        ;;
esac
EOF

chmod +x view_db.sh
```

运行后可以使用：
```bash
./view_db.sh
```

这样你就可以方便地查看数据库中的所有数据了！