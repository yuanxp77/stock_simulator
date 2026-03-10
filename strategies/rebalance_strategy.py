#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
等权定投 + 月度再平衡策略

逻辑：
- 初始全仓买入 N 只股票，各占 1/N
- 每月第一个交易日注入固定金额，并将所有持仓再平衡到等权
- 不看技术指标，纯日历驱动
"""

import pandas as pd
import numpy as np
from typing import Dict, List


def _calculate_fees(price: float, quantity: int, trade_type: str):
    """A 股交易费用：(佣金, 印花税)"""
    amount = price * quantity
    commission = max(amount * 0.0003, 5.0)
    stamp_tax = amount * 0.001 if trade_type == '卖出' else 0.0
    return commission, stamp_tax


def run_rebalance_backtest(
    all_data: pd.DataFrame,
    stocks: List[Dict],
    initial_capital: float,
    monthly_invest: float,
    target_weight: float,
) -> Dict:
    """
    等权定投 + 月度再平衡回测。

    Args:
        all_data: 含 date/stock_code/open/high/low/close/volume 的 DataFrame
        stocks: [{'code': '601088', 'name': '中国神华'}, ...]
        initial_capital: 初始资金
        monthly_invest: 每月定投金额
        target_weight: 每只股票目标权重（如 0.25）
    """
    stock_codes = [s['code'] for s in stocks]
    n_stocks = len(stock_codes)

    all_data = all_data.copy()
    all_data['date'] = pd.to_datetime(all_data['date'])
    all_data = all_data[all_data['stock_code'].isin(stock_codes)].sort_values('date')

    trading_days = sorted(all_data['date'].unique())
    if not len(trading_days):
        return _empty_result(initial_capital)

    # 按月分组，找出每月第一个交易日
    day_series = pd.Series(trading_days)
    month_first_days = set(
        day_series.groupby(day_series.apply(lambda d: (d.year, d.month))).first().values
    )

    cash = initial_capital
    total_invested = initial_capital
    holdings = {code: 0 for code in stock_codes}  # code -> qty
    equity_curve = []
    trades = []
    rebalance_log = []
    is_first_day = True

    for day in trading_days:
        day_data = all_data[all_data['date'] == day]
        prices = {}
        for code in stock_codes:
            row = day_data[day_data['stock_code'] == code]
            if not row.empty:
                prices[code] = row.iloc[0]['close']

        if not prices:
            equity_curve.append({
                'date': day, 'equity': cash,
                'cash': cash, 'position_value': 0,
                'total_invested': total_invested,
            })
            continue

        available_codes = [c for c in stock_codes if c in prices]

        do_rebalance = is_first_day or (day in month_first_days and not is_first_day)

        if do_rebalance and not is_first_day:
            cash += monthly_invest
            total_invested += monthly_invest

        if do_rebalance:
            is_first_day = False
            position_value = sum(holdings[c] * prices.get(c, 0) for c in stock_codes)
            total_assets = cash + position_value
            weight = 1.0 / len(available_codes)
            target_value = total_assets * weight

            rebalance_actions = []

            def _buy_underweight():
                """用当前现金按比例买入低配股票，返回是否还有缺口"""
                nonlocal cash
                buy_needs = {}
                for code in available_codes:
                    current_value = holdings[code] * prices[code]
                    diff = target_value - current_value
                    if diff > 0:
                        buy_needs[code] = diff

                total_need = sum(buy_needs.values())
                for code, need in buy_needs.items():
                    alloc = cash * (need / total_need) if total_need > 0 else 0
                    buy_qty = int(alloc / prices[code])
                    if buy_qty > 0:
                        comm, tax = _calculate_fees(prices[code], buy_qty, '买入')
                        cost = buy_qty * prices[code] + comm + tax
                        if cost <= cash:
                            cash -= cost
                            holdings[code] += buy_qty
                            trades.append({
                                'date': day, 'stock_code': code, 'type': '买入',
                                'price': prices[code], 'qty': buy_qty, 'profit': 0,
                            })
                            rebalance_actions.append(f"{code} 买入{buy_qty}股")

                still_gap = any(
                    holdings[c] * prices[c] < target_value * 0.95
                    for c in available_codes
                )
                return still_gap

            # 第一步：用定投资金（和之前剩余现金）先补弱
            still_unbalanced = _buy_underweight()

            # 第二步：如果补完还没平衡，卖出超配的，再用回收的现金继续补
            if still_unbalanced:
                for code in available_codes:
                    current_value = holdings[code] * prices[code]
                    diff = target_value - current_value
                    if diff < 0:
                        sell_qty = int(abs(diff) / prices[code])
                        if sell_qty > 0 and sell_qty <= holdings[code]:
                            comm, tax = _calculate_fees(prices[code], sell_qty, '卖出')
                            revenue = sell_qty * prices[code] - comm - tax
                            cash += revenue
                            holdings[code] -= sell_qty
                            trades.append({
                                'date': day, 'stock_code': code, 'type': '卖出',
                                'price': prices[code], 'qty': sell_qty,
                                'profit': revenue - sell_qty * prices[code],
                            })
                            rebalance_actions.append(f"{code} 卖出{sell_qty}股")

                _buy_underweight()

            if rebalance_actions:
                position_value_after = sum(holdings[c] * prices.get(c, 0) for c in stock_codes)
                rebalance_log.append({
                    'date': day,
                    'total_assets': cash + position_value_after,
                    'total_invested': total_invested,
                    'actions': rebalance_actions,
                })

        position_value = sum(holdings[c] * prices.get(c, 0) for c in stock_codes)
        equity_curve.append({
            'date': day, 'equity': cash + position_value,
            'cash': cash, 'position_value': position_value,
            'total_invested': total_invested,
        })

    # 统计
    if not equity_curve:
        return _empty_result(initial_capital)

    final_equity = equity_curve[-1]['equity']
    total_return = (final_equity - total_invested) / total_invested

    first_date = pd.to_datetime(trading_days[0])
    last_date = pd.to_datetime(trading_days[-1])
    years = (last_date - first_date).days / 365.25
    annual_return = (final_equity / total_invested) ** (1 / years) - 1 if years > 0 else 0

    equity_df = pd.DataFrame(equity_curve)
    cumulative_max = equity_df['equity'].cummax()
    drawdown = cumulative_max - equity_df['equity']
    max_drawdown = drawdown.max()
    max_drawdown_ratio = (drawdown / cumulative_max).max()

    equity_returns = equity_df['equity'].pct_change().dropna()
    volatility = equity_returns.std() * np.sqrt(252) if len(equity_returns) > 0 else 0

    if len(equity_returns) > 0 and equity_returns.std() > 0:
        sharpe = np.sqrt(252) * (equity_returns.mean() - 0.03 / 252) / equity_returns.std()
    else:
        sharpe = 0.0

    stock_names = {s['code']: s.get('name', s['code']) for s in stocks}
    per_stock = {}
    for code in stock_codes:
        last_price = prices.get(code, 0) if prices else 0
        qty = holdings[code]
        market_value = qty * last_price

        stock_trades = [t for t in trades if t['stock_code'] == code]
        total_buy = sum(t['price'] * t['qty'] for t in stock_trades if t['type'] == '买入')
        total_sell = sum(t['price'] * t['qty'] for t in stock_trades if t['type'] == '卖出')
        pnl = market_value + total_sell - total_buy
        net_cost = total_buy - total_sell
        pnl_pct = pnl / total_buy if total_buy > 0 else 0

        per_stock[code] = {
            'name': stock_names.get(code, code),
            'qty': qty,
            'last_price': last_price,
            'market_value': market_value,
            'net_cost': net_cost,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'weight': market_value / final_equity if final_equity > 0 else 0,
        }

    return {
        'initial_capital': initial_capital,
        'total_invested': total_invested,
        'final_equity': final_equity,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'max_drawdown_ratio': max_drawdown_ratio,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'total_trades': len(trades),
        'trades': trades,
        'equity_curve': equity_curve,
        'rebalance_log': rebalance_log,
        'stock_codes': stock_codes,
        'monthly_invest': monthly_invest,
        'per_stock': per_stock,
    }


def _empty_result(initial_capital):
    return {
        'initial_capital': initial_capital,
        'total_invested': initial_capital,
        'final_equity': initial_capital,
        'total_return': 0, 'annual_return': 0,
        'max_drawdown': 0, 'max_drawdown_ratio': 0,
        'volatility': 0, 'sharpe_ratio': 0,
        'total_trades': 0, 'trades': [], 'equity_curve': [],
        'rebalance_log': [], 'stock_codes': [], 'monthly_invest': 0,
    }
