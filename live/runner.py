#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时策略运行器
用法: python -m live.runner --strategy 双均线策略
"""

import argparse
import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from live.account import VirtualAccount
from live.data_feed import fetch_latest_bars, is_trading_time
from strategies.dual_ma_strategy import DualMAStrategy
from strategies.bollinger_bands_strategy import BollingerBandsStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.ma_reversal_strategy import MAReversalStrategy

STRATEGY_CLASS_MAP = {
    'DualMA': DualMAStrategy,
    'Bollinger': BollingerBandsStrategy,
    'RSI': RSIStrategy,
    'Turtle': TurtleStrategy,
    'MAReversal': MAReversalStrategy,
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def create_strategy(strategy_name: str):
    cfg = config.STRATEGIES.get(strategy_name)
    if cfg is None:
        available = ', '.join(config.STRATEGIES.keys())
        print(f"未知策略: {strategy_name}")
        print(f"可用策略: {available}")
        sys.exit(1)
    cls = STRATEGY_CLASS_MAP.get(cfg['type'])
    if cls is None:
        print(f"未知策略类型: {cfg['type']}")
        sys.exit(1)
    return cls(cfg['params'])


def run_one_tick(strategy, account: VirtualAccount, stocks: list,
                 position_ratio: float):
    """执行一次轮询：获取数据 → 计算信号 → 交易"""
    now_str = datetime.now().strftime('%H:%M')
    current_prices = {}
    signal_lines = []

    for stock_info in stocks:
        code = stock_info['code']
        name = stock_info['name']

        bars = fetch_latest_bars(code, count=120)
        if bars.empty:
            signal_lines.append(f"  {code}({name}): 无数据")
            continue

        last_close = bars.iloc[-1]['close']
        current_prices[code] = last_close

        try:
            with_indicators = strategy.calculate_indicators(bars)
            signals = strategy.generate_signals(with_indicators)
        except Exception as e:
            signal_lines.append(f"  {code}({name}): 计算失败 {e}")
            continue

        if not signals:
            signal_lines.append(f"  {code}({name}): 无信号")
            continue

        last_signal = signals[-1]['signal']

        if last_signal == 'BUY' and code not in account.holdings:
            available = account.cash * position_ratio
            qty = int(available / last_close)
            if qty > 0:
                record = account.buy(code, last_close, qty, name)
                if record:
                    signal_lines.append(
                        f"  {code}({name}): BUY  close={last_close:.2f} "
                        f"-> 买入 {qty} 股")
                else:
                    signal_lines.append(
                        f"  {code}({name}): BUY  close={last_close:.2f} "
                        f"-> 资金不足")
            else:
                signal_lines.append(
                    f"  {code}({name}): BUY  close={last_close:.2f} "
                    f"-> 资金不足")

        elif last_signal == 'SELL' and code in account.holdings:
            record = account.sell(code, last_close)
            if record:
                pnl = record['profit']
                signal_lines.append(
                    f"  {code}({name}): SELL close={last_close:.2f} "
                    f"-> 卖出 {record['qty']} 股, 盈亏 {pnl:+.2f}")
        else:
            signal_lines.append(
                f"  {code}({name}): {last_signal:4s} close={last_close:.2f}")

        time.sleep(1)

    equity = account.get_equity(current_prices)
    holdings_str = account.get_holdings_summary(current_prices)
    print(f"\n[{now_str}] {strategy.strategy_name} | "
          f"资金: {account.cash:,.0f} | "
          f"持仓: {holdings_str} | "
          f"权益: {equity:,.0f}")
    for line in signal_lines:
        print(line)


def wait_for_trading():
    """非交易时间等待，每 30 秒检查一次"""
    while not is_trading_time():
        now = datetime.now()
        print(f"\r[{now.strftime('%H:%M:%S')}] 非交易时间，等待中...", end='', flush=True)
        time.sleep(30)
    print()


def main():
    parser = argparse.ArgumentParser(description='实时策略运行器')
    parser.add_argument('--strategy', type=str, default='双均线策略',
                        help='策略名（对应 config.STRATEGIES 中的 key）')
    parser.add_argument('--interval', type=int, default=60,
                        help='轮询间隔（秒），默认 60')
    parser.add_argument('--no-wait', action='store_true',
                        help='不等待交易时间，立即运行（测试用）')
    args = parser.parse_args()

    strategy = create_strategy(args.strategy)
    account = VirtualAccount(config.INITIAL_CAPITAL)
    stocks = config.STOCKS
    position_ratio = config.POSITION_RATIO

    print("=" * 60)
    print(f"实时策略运行器")
    print(f"策略: {args.strategy}")
    print(f"股票: {', '.join(s['code'] + '(' + s['name'] + ')' for s in stocks)}")
    print(f"资金: {config.INITIAL_CAPITAL:,.0f}")
    print(f"仓位: {position_ratio:.0%}")
    print(f"轮询: 每 {args.interval} 秒")
    print("=" * 60)
    print("Ctrl+C 退出\n")

    try:
        while True:
            if not args.no_wait and not is_trading_time():
                wait_for_trading()

            run_one_tick(strategy, account, stocks, position_ratio)
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("运行结束 — 账户汇总")
        print("=" * 60)
        prices = {}
        for s in stocks:
            bars = fetch_latest_bars(s['code'], count=1)
            if not bars.empty:
                prices[s['code']] = bars.iloc[-1]['close']
        print(account.summary(prices))

        if account.trade_log:
            print(f"\n交易记录 ({len(account.trade_log)} 笔):")
            for t in account.trade_log:
                pnl = f" 盈亏{t['profit']:+.2f}" if t['type'] == '卖出' else ''
                print(f"  {t['time']} {t['type']} {t['stock_code']} "
                      f"价格{t['price']:.2f} 数量{t['qty']}{pnl}")
        print("=" * 60)


if __name__ == '__main__':
    main()
