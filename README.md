# 股票量化交易系统

A 股多策略量化系统，支持离线回测（含参数自动寻优）和实时模拟交易。

## 项目结构

```
stock_simulator/
  config.py               # 统一配置（股票、资金、策略参数、搜索空间）
  makefile                 # 入口命令
  requirements.txt
  strategies/              # 共享策略
    base_strategy.py       # 策略基类（回测引擎 + 费用计算）
    dual_ma_strategy.py    # 双均线策略
    bollinger_bands_strategy.py  # 布林带策略
    rsi_strategy.py        # RSI 超买超卖策略
    turtle_strategy.py     # 海龟交易策略
    ma_reversal_strategy.py     # 均线反转策略
  backtest/                # 离线回测
    main.py                # 回测主程序（参数优化 + 多股票共享资金池回测）
    database.py            # SQLite 结果存储
    data_generator.py      # akshare 数据拉取（东财/新浪/腾讯 fallback）
    stock_simulator.sql    # 建表脚本
  live/                    # 实时模拟交易
    runner.py              # 实时运行主循环（1 分钟 K 线轮询）
    data_feed.py           # akshare 1 分钟 K 线封装
    account.py             # 虚拟模拟账户（内存管理资金 + 持仓）
```

## 快速开始

```bash
# 安装依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 离线回测（参数自动寻优 + 最优参数正式回测）
make backtest

# 实时模拟交易（默认双均线策略，Ctrl+C 退出）
make live
make live STRATEGY=RSI超买超卖策略
```

## 配置

所有配置集中在 `config.py`，修改后直接运行即可：

- `STOCKS` — 股票列表（拉数据 + 回测 + 实时 共用）
- `START_DATE` / `END_DATE` — 回测时间范围
- `INITIAL_CAPITAL` — 初始资金
- `POSITION_RATIO` — 单次买入仓位比例
- `STRATEGIES` — 各策略参数
- `PARAM_SEARCH_SPACE` — 参数网格搜索空间

## 回测流程

1. 通过 akshare 拉取 A 股真实日线数据
2. 对每个策略遍历参数搜索空间，按夏普比率选出最优参数（Top-3 输出）
3. 用最优参数执行多股票共享资金池回测（所有股票共用一个资金池）
4. 输出结果报告（`results/backtest_report.csv`）和可视化图表（`results/visualizations/`）

## 实时模拟交易

- 每 60 秒通过 akshare 获取 1 分钟 K 线
- 复用回测策略类计算信号
- 纯内存虚拟账户管理资金和持仓（进程结束即丢失）
- 非交易时间自动等待

## 策略

| 策略 | 买入条件 | 卖出条件 |
|------|---------|---------|
| 双均线 | 短期均线上穿长期均线 | 短期均线下穿长期均线 |
| 布林带 | 价格从下轨反弹 | 价格突破上轨 |
| RSI | RSI 从超卖区反弹 | RSI 进入超买区 |
| 海龟 | 突破 N 日最高价 | 跌破 M 日最低价 |
| 均线反转 | 跌破均线 + 缩量 | 突破均线 + 放量 |

## 添加新策略

1. 在 `strategies/` 下新建文件，继承 `BaseStrategy`
2. 实现 `calculate_indicators()` 和 `generate_signals()`
3. 在 `config.py` 的 `STRATEGIES` 中注册
4. 在 `backtest/main.py` 和 `live/runner.py` 的 `STRATEGY_CLASS_MAP` 中添加映射

## 费用模型

- 佣金：成交额 × 0.03%，最低 5 元（买卖双向）
- 印花税：成交额 × 0.1%（仅卖出）
