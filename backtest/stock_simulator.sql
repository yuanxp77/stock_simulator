-- 股票模拟交易数据库表结构
-- 使用SQLite，无需复杂部署

-- 删除已存在的表（如果存在）
DROP TABLE IF EXISTS backtest_results;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS account;
DROP TABLE IF EXISTS strategies;

-- 1. 本金账户表（account）
-- 记录初始本金、当前可用资金、总权益、资金变动时间等
CREATE TABLE account (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    initial_capital REAL NOT NULL DEFAULT 100000.0,  -- 初始本金，默认10万元
    available_cash REAL NOT NULL DEFAULT 100000.0,   -- 当前可用资金
    total_equity REAL NOT NULL DEFAULT 100000.0,     -- 总权益（可用资金+持仓市值）
    last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 最后更新时间
    strategy_name TEXT NOT NULL                     -- 策略名称
);

-- 2. 持仓表（holdings）
-- 记录持有的股票代码、持仓数量、持仓成本、持仓时间、所属策略等
CREATE TABLE holdings (
    holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,                     -- 策略名称
    stock_code TEXT NOT NULL,                        -- 股票代码（如：600519）
    stock_name TEXT,                                 -- 股票名称
    quantity INTEGER NOT NULL DEFAULT 0,             -- 持仓数量
    avg_cost REAL NOT NULL DEFAULT 0.0,             -- 平均持仓成本
    current_price REAL NOT NULL DEFAULT 0.0,         -- 当前股价
    market_value REAL NOT NULL DEFAULT 0.0,          -- 持仓市值
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,        -- 未实现盈亏
    unrealized_pnl_ratio REAL NOT NULL DEFAULT 0.0,  -- 未实现盈亏比例
    holding_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 持仓开始时间
    last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 最后更新时间
    UNIQUE(strategy_name, stock_code)               -- 同一策略同一股票只能有一条持仓记录
);

-- 3. 交易记录表（trades）
-- 记录每笔交易的策略名称、股票代码、买卖方向、交易价格、交易数量、交易时间、手续费等
CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,                     -- 策略名称
    stock_code TEXT NOT NULL,                        -- 股票代码
    stock_name TEXT,                                 -- 股票名称
    trade_type TEXT NOT NULL CHECK (trade_type IN ('买入', '卖出')),  -- 交易类型
    direction TEXT NOT NULL CHECK (direction IN ('开仓', '平仓')),   -- 买卖方向
    trade_price REAL NOT NULL,                       -- 交易价格
    trade_quantity INTEGER NOT NULL,                 -- 交易数量
    trade_amount REAL NOT NULL,                      -- 交易金额
    commission REAL NOT NULL DEFAULT 0.0,             -- 手续费
    stamp_tax REAL NOT NULL DEFAULT 0.0,             -- 印花税
    total_cost REAL NOT NULL,                        -- 总成本（含费用）
    trade_time DATETIME DEFAULT CURRENT_TIMESTAMP,   -- 交易时间
    trade_date DATE,                                 -- 交易日期（便于分析）
    profit REAL DEFAULT 0.0,                         -- 本次交易盈亏
    profit_ratio REAL DEFAULT 0.0                   -- 本次交易盈亏比例
);

-- 4. 策略参数表（strategies）
-- 记录策略名称、核心参数、创建时间等
CREATE TABLE strategies (
    strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL UNIQUE,              -- 策略名称
    strategy_type TEXT NOT NULL,                     -- 策略类型
    parameters TEXT NOT NULL,                        -- 策略参数（JSON格式）
    description TEXT,                                -- 策略描述
    is_active BOOLEAN DEFAULT 1,                     -- 是否启用
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    last_updated_time DATETIME DEFAULT CURRENT_TIMESTAMP -- 最后更新时间
);

-- 5. 回测结果表（backtest_results）
-- 记录策略名称、回测时间段、总收益率、年化收益率、最大回撤、胜率、交易次数等
CREATE TABLE backtest_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,                     -- 策略名称
    start_date DATE NOT NULL,                        -- 回测开始日期
    end_date DATE NOT NULL,                          -- 回测结束日期
    total_return REAL NOT NULL DEFAULT 0.0,          -- 总收益率
    annual_return REAL NOT NULL DEFAULT 0.0,         -- 年化收益率
    max_drawdown REAL NOT NULL DEFAULT 0.0,          -- 最大回撤
    max_drawdown_ratio REAL NOT NULL DEFAULT 0.0,    -- 最大回撤比例
    win_rate REAL NOT NULL DEFAULT 0.0,              -- 胜率
    profit_loss_ratio REAL NOT NULL DEFAULT 0.0,     -- 盈亏比
    total_trades INTEGER NOT NULL DEFAULT 0,         -- 总交易次数
    winning_trades INTEGER NOT NULL DEFAULT 0,       -- 盈利交易次数
    losing_trades INTEGER NOT NULL DEFAULT 0,        -- 亏损交易次数
    sharpe_ratio REAL NOT NULL DEFAULT 0.0,          -- 夏普比率
    volatility REAL NOT NULL DEFAULT 0.0,            -- 波动率
    final_equity REAL NOT NULL DEFAULT 0.0,          -- 最终权益
    max_equity REAL NOT NULL DEFAULT 0.0,            -- 最高权益
    min_equity REAL NOT NULL DEFAULT 0.0,            -- 最低权益
    backtest_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 回测完成时间
    data_source TEXT,                                -- 数据来源
    stock_codes TEXT                                 -- 参与回测的股票代码（逗号分隔）
);

-- 创建索引以提高查询性能
CREATE INDEX idx_trades_strategy_time ON trades(strategy_name, trade_time);
CREATE INDEX idx_trades_stock ON trades(stock_code);
CREATE INDEX idx_holdings_strategy ON holdings(strategy_name);
CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_name);
CREATE INDEX idx_trades_date ON trades(trade_date);

-- 插入默认策略参数
INSERT INTO strategies (strategy_name, strategy_type, parameters, description) VALUES 
('双均线策略', 'trend', '{"short_ma": 5, "long_ma": 20}', '短期均线上穿长期均线买入，下穿卖出'),
('布林带策略', 'momentum', '{"bb_period": 20, "bb_std": 2}', '股价跌破布林带下轨买入，突破上轨卖出'),
('RSI超买超卖策略', 'oscillator', '{"rsi_period": 14, "oversold": 30, "overbought": 70}', 'RSI<30买入，RSI>70卖出'),
('海龟交易策略', 'breakout', '{"breakout_period": 20, "exit_period": 10, "stop_loss_pct": 0.02}', '突破20日最高价买入，跌破10日最低价卖出，设置2%止损'),
('简单均线反转策略', 'reversal', '{"ma_period": 60, "volume_change_pct": 0.5}', 'MA60为趋势线，股价跌破MA60且成交量缩量50%买入，突破MA60且成交量放量50%卖出');

-- 插入初始账户记录
INSERT INTO account (initial_capital, available_cash, total_equity, strategy_name) 
VALUES (100000.0, 100000.0, 100000.0, '初始账户');