#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""等权定投 + 月度再平衡回测入口"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from datetime import datetime
import logging
import os
import platform
import argparse

import config
from backtest.data_generator import StockDataGenerator
from strategies.rebalance_strategy import run_rebalance_backtest


def _setup_chinese_font():
    candidates = {
        'Darwin': ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS'],
        'Windows': ['Microsoft YaHei', 'SimHei'],
    }.get(platform.system(), ['WenQuanYi Micro Hei', 'Noto Sans CJK SC'])
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams['font.sans-serif'] = [name, 'DejaVu Sans']
            break
    plt.rcParams['axes.unicode_minus'] = False

_setup_chinese_font()

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('backtest.data_generator').setLevel(logging.WARNING)


def fetch_data(stocks, start_date, end_date):
    os.makedirs("data", exist_ok=True)
    generator = StockDataGenerator(start_date, end_date)
    return generator.generate_multiple_stocks(stocks, "data/rebalance_data.csv")


def plot_equity_curve(result, output_dir="results/visualizations"):
    if not result['equity_curve']:
        logger.warning("无权益曲线数据，跳过绘图")
        return
    os.makedirs(output_dir, exist_ok=True)
    eq = pd.DataFrame(result['equity_curve'])
    eq['date'] = pd.to_datetime(eq['date'])

    fig, ax1 = plt.subplots(figsize=(14, 6))

    ax1.plot(eq['date'], eq['equity'], label='总权益', linewidth=1.5)
    ax1.plot(eq['date'], eq['total_invested'], label='累计投入',
             linewidth=1, linestyle='--', alpha=0.7)
    ax1.fill_between(eq['date'], eq['total_invested'], eq['equity'],
                     where=eq['equity'] >= eq['total_invested'],
                     alpha=0.15, color='green')
    ax1.fill_between(eq['date'], eq['total_invested'], eq['equity'],
                     where=eq['equity'] < eq['total_invested'],
                     alpha=0.15, color='red')

    ax1.set_xlabel('日期')
    ax1.set_ylabel('金额 (元)')
    ax1.set_title('等权定投 + 月度再平衡 — 权益曲线')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    plt.tight_layout()
    path = f"{output_dir}/rebalance_equity.png"
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"权益曲线图已保存到：{path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-fetch', action='store_true', help='跳过数据获取，使用本地缓存')
    args = parser.parse_args()

    rb = config.REBALANCE
    stocks = rb['stocks']
    monthly_invest = rb['monthly_invest']
    target_weight = rb['target_weight']
    interval_months = rb.get('interval_months', 1)
    initial_capital = config.INITIAL_CAPITAL
    start_date = config.START_DATE
    end_date = config.END_DATE or datetime.now().strftime('%Y-%m-%d')

    stock_names = ', '.join(f"{s['code']}({s['name']})" for s in stocks)
    cache_file = "data/rebalance_data.csv"
    interval_label = f"每{interval_months}个月" if interval_months > 1 else "每月"

    print(f"等权定投 + {interval_label}再平衡策略")
    print("=" * 60)
    print(f"股票：{stock_names}")
    print(f"初始资金：{initial_capital:,.0f}  每期定投：{monthly_invest * interval_months:,.0f}（{monthly_invest:,.0f}/月 × {interval_months}月）")
    print(f"目标权重：每只 {target_weight:.0%}  再平衡周期：{interval_label}")
    print(f"时段：{start_date} ~ {end_date}")
    if args.no_fetch:
        print("数据：使用本地缓存")
    print("=" * 60)

    need_codes = {s['code'] for s in stocks}

    if not args.no_fetch:
        logger.info("获取股票数据...")
        all_data = fetch_data(stocks, start_date, end_date)
    elif os.path.exists(cache_file):
        all_data = pd.read_csv(cache_file, dtype={'stock_code': str})
        cached_codes = set(all_data['stock_code'].unique())
        missing = need_codes - cached_codes
        if missing:
            logger.warning(f"缓存缺少 {missing}，重新获取数据...")
            all_data = fetch_data(stocks, start_date, end_date)
        else:
            logger.info("使用本地缓存数据")
    else:
        logger.info("本地缓存不存在，获取数据...")
        all_data = fetch_data(stocks, start_date, end_date)

    if all_data.empty:
        print("未获取到数据")
        return

    logger.info("开始回测...")
    result = run_rebalance_backtest(
        all_data, stocks, initial_capital, monthly_invest, target_weight,
        interval_months=interval_months,
    )

    inv = result['total_invested']
    eq = result['final_equity']
    profit = eq - inv

    print(f"""
累计投入: {inv:,.0f}  |  最终权益: {eq:,.0f}  |  绝对收益: {profit:+,.0f}
总收益率: {result['total_return']:.2%}  |  年化: {result['annual_return']:.2%}  |  最大回撤: {result['max_drawdown_ratio']:.2%}
夏普比率: {result['sharpe_ratio']:.2f}  |  波动率: {result['volatility']:.2%}  |  再平衡: {len(result['rebalance_log'])}次""")

    per = result.get('per_stock', {})
    if per:
        print("\n个股明细:")
        for code, info in per.items():
            label = f"  {info['name']}({code})"
            print(f"{label}  |  {info['qty']:,}股  "
                  f"市值{info['market_value']:,.0f}  "
                  f"盈亏{info['pnl']:+,.0f}({info['pnl_pct']:+.2%})  "
                  f"占比{info['weight']:.1%}")

    plot_equity_curve(result)
    print(f"\n权益曲线 → results/visualizations/rebalance_equity.png")


if __name__ == '__main__':
    main()
