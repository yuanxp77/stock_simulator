#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
再平衡顾问：输入当前持仓股数 + 可用现金，获取实时股价，
按「先补弱、再卖强」策略输出本月操作建议。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import config


def _calculate_fees(price: float, quantity: int, trade_type: str):
    amount = price * quantity
    commission = max(amount * 0.0003, 5.0)
    stamp_tax = amount * 0.001 if trade_type == '卖出' else 0.0
    return commission + stamp_tax


def fetch_latest_price(code: str) -> float:
    """取最近交易日的收盘价（股票 → ETF 自动 fallback）"""
    import akshare as ak
    from datetime import datetime, timedelta

    end = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

    try:
        df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                start_date=start, end_date=end, adjust='qfq')
        if df is not None and not df.empty:
            return float(df.iloc[-1]['收盘'])
    except Exception:
        pass

    try:
        df = ak.fund_etf_hist_em(symbol=code, period='daily',
                                 start_date=start, end_date=end, adjust='qfq')
        if df is not None and not df.empty:
            return float(df.iloc[-1]['收盘'])
    except Exception:
        pass

    return 0.0


def main():
    rb = config.REBALANCE
    stocks = rb['stocks']
    monthly_invest = rb['monthly_invest']

    parser = argparse.ArgumentParser(description='再平衡操作建议')
    parser.add_argument('--cash', type=float, default=0.0,
                        help=f'账户闲置现金（不含本月定投 {monthly_invest:.0f}）')
    for s in stocks:
        parser.add_argument(f'--{s["code"]}', type=int, required=True,
                            metavar='股数', help=f'{s["name"]} 持仓股数')
    args = parser.parse_args()

    holdings = {}
    for s in stocks:
        holdings[s['code']] = getattr(args, s['code'])

    cash = args.cash + monthly_invest

    print("获取最新股价...")
    prices = {}
    for s in stocks:
        p = fetch_latest_price(s['code'])
        prices[s['code']] = p
        print(f"  {s['name']}({s['code']}): {p:.3f}")
        if p == 0:
            print(f"  ⚠ 获取失败，退出")
            return

    # 当前持仓
    total_position = sum(holdings[c] * prices[c] for c in holdings)
    total_assets = cash + total_position
    n = len(stocks)
    target_value = total_assets / n

    print(f"\n{'='*55}")
    print(f"本月再平衡建议")
    print(f"{'='*55}")
    print(f"本月定投: {monthly_invest:,.0f}  账户现金: {args.cash:,.0f}  可用资金: {cash:,.0f}")
    print(f"持仓市值: {total_position:,.0f}  总资产: {total_assets:,.0f}")
    print(f"目标权重: 各 {1/n:.0%}  目标市值: 各 {target_value:,.0f}")

    print(f"\n当前持仓:")
    for s in stocks:
        c = s['code']
        mv = holdings[c] * prices[c]
        w = mv / total_assets if total_assets > 0 else 0
        diff = mv - target_value
        tag = "▲" if diff > 0 else "▼"
        print(f"  {s['name']}({c})  {prices[c]:.2f}元 × {holdings[c]:,}股"
              f"  = {mv:,.0f}  占{w:.1%}  {tag}{abs(diff):,.0f}")

    # 第一步：先补弱
    actions = []

    buy_needs = {}
    for s in stocks:
        c = s['code']
        current = holdings[c] * prices[c]
        gap = target_value - current
        if gap > 0:
            buy_needs[c] = gap

    total_need = sum(buy_needs.values())
    bought_cost = 0
    for code, need in sorted(buy_needs.items(), key=lambda x: -x[1]):
        alloc = cash * (need / total_need) if total_need > 0 else 0
        qty = int(alloc / prices[code])
        if qty > 0:
            fee = _calculate_fees(prices[code], qty, '买入')
            cost = qty * prices[code] + fee
            if cost <= cash:
                cash -= cost
                holdings[code] += qty
                bought_cost += cost
                name = next(s['name'] for s in stocks if s['code'] == code)
                actions.append(('买入', name, code, qty, prices[code], cost))

    # 检查是否还有较大偏差
    still_unbalanced = any(
        holdings[c] * prices[c] < target_value * 0.95
        for c in holdings
    )

    # 第二步：卖强补弱
    if still_unbalanced:
        for s in stocks:
            c = s['code']
            current = holdings[c] * prices[c]
            excess = current - target_value
            if excess > 0:
                sell_qty = int(excess / prices[c])
                if sell_qty > 0 and sell_qty <= holdings[c]:
                    fee = _calculate_fees(prices[c], sell_qty, '卖出')
                    revenue = sell_qty * prices[c] - fee
                    cash += revenue
                    holdings[c] -= sell_qty
                    actions.append(('卖出', s['name'], c, sell_qty, prices[c], revenue))

        # 卖出回收的现金再补弱
        buy_needs2 = {}
        for s in stocks:
            c = s['code']
            current = holdings[c] * prices[c]
            gap = target_value - current
            if gap > 0:
                buy_needs2[c] = gap

        total_need2 = sum(buy_needs2.values())
        for code, need in sorted(buy_needs2.items(), key=lambda x: -x[1]):
            alloc = cash * (need / total_need2) if total_need2 > 0 else 0
            qty = int(alloc / prices[code])
            if qty > 0:
                fee = _calculate_fees(prices[code], qty, '买入')
                cost = qty * prices[code] + fee
                if cost <= cash:
                    cash -= cost
                    holdings[code] += qty
                    name = next(s['name'] for s in stocks if s['code'] == code)
                    actions.append(('买入', name, code, qty, prices[code], cost))

    # 输出操作建议
    print(f"\n操作建议:")
    if not actions:
        print("  无需操作，持仓已均衡")
    else:
        total_fee = 0
        for act_type, name, code, qty, price, amount in actions:
            fee = _calculate_fees(price, qty, act_type)
            total_fee += fee
            print(f"  {act_type} {name}({code})  {qty:,}股 × {price:.2f}元"
                  f"  {'花费' if act_type == '买入' else '回收'} {amount:,.0f}元")
        print(f"\n预估手续费: {total_fee:,.1f}元")

    # 操作后的持仓
    total_after = sum(holdings[c] * prices[c] for c in holdings) + cash
    print(f"\n操作后持仓:")
    for s in stocks:
        c = s['code']
        mv = holdings[c] * prices[c]
        w = mv / total_after if total_after > 0 else 0
        print(f"  {s['name']}({c})  {holdings[c]:,}股  市值 {mv:,.0f}  占{w:.1%}")
    print(f"  剩余现金: {cash:,.0f}")
    print(f"{'='*55}")


if __name__ == '__main__':
    main()
