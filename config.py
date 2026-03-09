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
    {'code': '600976', 'name': '健民集团'},
    {'code': '601088', 'name': '中国神华'},
    {'code': '600519', 'name': '贵州茅台'},
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

# ── 参数网格搜索空间（用于自动寻优）──
PARAM_SEARCH_SPACE = {
    'DualMA': {
        'grid': {
            'short_ma': [3, 5, 8, 10, 13],
            'long_ma': [15, 20, 30, 40, 60],
        },
        'constraint': lambda p: p['short_ma'] < p['long_ma'],
    },
    'Bollinger': {
        'grid': {
            'bb_period': [10, 15, 20, 25, 30],
            'bb_std': [1.5, 2.0, 2.5, 3.0],
        },
    },
    'RSI': {
        'grid': {
            'rsi_period': [7, 10, 14, 21],
            'oversold': [20, 25, 30, 35],
            'overbought': [65, 70, 75, 80],
        },
        'constraint': lambda p: p['oversold'] < p['overbought'],
    },
    'Turtle': {
        'grid': {
            'breakout_period': [10, 15, 20, 30, 40],
            'exit_period': [5, 8, 10, 15, 20],
            'stop_loss_pct': [0.02, 0.03, 0.05],
        },
        'constraint': lambda p: p['exit_period'] < p['breakout_period'],
    },
    'MAReversal': {
        'grid': {
            'ma_period': [20, 40, 60, 90, 120],
            'volume_change_pct': [0.3, 0.5, 0.7, 1.0],
        },
    },
}
