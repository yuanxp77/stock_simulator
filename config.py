#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测系统统一配置 —— 所有可调参数都在这里修改
"""

# ── 时间范围 ──
START_DATE = "2020-01-01"
END_DATE = None  # None = 取到今天

# ── 资金 ──
INITIAL_CAPITAL = 100000.0  # 初始资金（所有股票共享同一资金池）
POSITION_RATIO = 0.3        # 单次买入仓位比例（占当前可用现金）

# ── 股票列表（拉数据 + 回测都用这个列表）──
STOCKS = [
    {'code': '600519', 'name': '贵州茅台'},
    {'code': '000858', 'name': '五粮液'},
    {'code': '601318', 'name': '中国平安'},
    {'code': '600036', 'name': '招商银行'},
    {'code': '000333', 'name': '美的集团'},
    {'code': '600276', 'name': '恒瑞医药'},
    {'code': '601888', 'name': '中国中免'},
    {'code': '600887', 'name': '伊利股份'},
    {'code': '000651', 'name': '格力电器'},
    {'code': '600028', 'name': '中国石化'},
]

# ── 策略配置 ──
STRATEGIES = {
    '双均线策略': {
        'type': 'DualMA',
        'params': {'short_ma': 5, 'long_ma': 20},
    },
    '布林带策略': {
        'type': 'Bollinger',
        'params': {'bb_period': 20, 'bb_std': 2},
    },
    'RSI超买超卖策略': {
        'type': 'RSI',
        'params': {'rsi_period': 14, 'oversold': 30, 'overbought': 70},
    },
    '海龟交易策略': {
        'type': 'Turtle',
        'params': {'breakout_period': 20, 'exit_period': 10, 'stop_loss_pct': 0.02},
    },
    '简单均线反转策略': {
        'type': 'MAReversal',
        'params': {'ma_period': 60, 'volume_change_pct': 0.5},
    },
}
