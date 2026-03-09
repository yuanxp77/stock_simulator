#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""虚拟模拟账户：纯内存管理资金池、持仓、交易记录"""

from datetime import datetime
from typing import Dict, List, Optional


def _calculate_fees(price: float, quantity: int, trade_type: str):
    """A 股交易费用：(佣金, 印花税)"""
    amount = price * quantity
    commission = max(amount * 0.0003, 5.0)
    stamp_tax = amount * 0.001 if trade_type == '卖出' else 0.0
    return commission, stamp_tax


class VirtualAccount:

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.holdings: Dict[str, Dict] = {}  # code -> {qty, cost, name}
        self.trade_log: List[Dict] = []

    def buy(self, stock_code: str, price: float, qty: int,
            stock_name: str = '') -> Optional[Dict]:
        if qty <= 0:
            return None
        comm, tax = _calculate_fees(price, qty, '买入')
        total_cost = qty * price + comm + tax
        if total_cost > self.cash:
            return None

        self.cash -= total_cost
        if stock_code in self.holdings:
            h = self.holdings[stock_code]
            old_total = h['qty'] * h['cost']
            h['qty'] += qty
            h['cost'] = (old_total + qty * price) / h['qty']
        else:
            self.holdings[stock_code] = {
                'qty': qty, 'cost': price, 'name': stock_name,
            }

        record = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stock_code': stock_code, 'type': '买入',
            'price': price, 'qty': qty,
            'commission': comm, 'stamp_tax': tax,
            'profit': 0.0,
        }
        self.trade_log.append(record)
        return record

    def sell(self, stock_code: str, price: float) -> Optional[Dict]:
        if stock_code not in self.holdings:
            return None
        h = self.holdings[stock_code]
        qty = h['qty']
        comm, tax = _calculate_fees(price, qty, '卖出')
        revenue = qty * price - comm - tax
        profit = revenue - qty * h['cost']
        self.cash += revenue

        record = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stock_code': stock_code, 'type': '卖出',
            'price': price, 'qty': qty,
            'commission': comm, 'stamp_tax': tax,
            'profit': profit,
        }
        self.trade_log.append(record)
        del self.holdings[stock_code]
        return record

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        position_value = sum(
            h['qty'] * current_prices.get(code, h['cost'])
            for code, h in self.holdings.items()
        )
        return self.cash + position_value

    def get_holdings_summary(self, current_prices: Dict[str, float] = None) -> str:
        if not self.holdings:
            return '空仓'
        parts = []
        for code, h in self.holdings.items():
            price = (current_prices or {}).get(code, h['cost'])
            pnl = (price - h['cost']) * h['qty']
            parts.append(f"{code}({h['qty']}股 {'%.2f' % pnl})")
        return ' '.join(parts)

    def summary(self, current_prices: Dict[str, float] = None) -> str:
        prices = current_prices or {}
        equity = self.get_equity(prices)
        total_return = (equity - self.initial_capital) / self.initial_capital
        sells = [t for t in self.trade_log if t['type'] == '卖出']
        wins = sum(1 for t in sells if t['profit'] > 0)
        lines = [
            f"初始资金: {self.initial_capital:,.2f}",
            f"当前权益: {equity:,.2f}",
            f"总收益率: {total_return:.2%}",
            f"现金: {self.cash:,.2f}",
            f"持仓: {self.get_holdings_summary(prices)}",
            f"交易笔数: {len(sells)} 卖出 ({wins} 盈利)",
        ]
        return '\n'.join(lines)
