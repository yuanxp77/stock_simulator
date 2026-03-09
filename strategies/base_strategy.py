#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量化策略基类"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import logging


class BaseStrategy(ABC):
    """量化策略基类，定义回测框架和公共指标计算"""

    def __init__(self, strategy_name: str, parameters: Dict):
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.logger = logging.getLogger(f"Strategy_{strategy_name}")

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标，子类实现"""
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """生成交易信号，子类实现"""
        pass

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> Tuple[float, float]:
        cumulative_max = equity_curve.cummax()
        drawdown = cumulative_max - equity_curve
        max_drawdown = drawdown.max()
        max_drawdown_ratio = (drawdown / cumulative_max).max()
        return max_drawdown, max_drawdown_ratio

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        excess_returns = returns - risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    @staticmethod
    def _calculate_fees(price: float, quantity: int, trade_type: str) -> Tuple[float, float]:
        """计算A股交易费用：(手续费, 印花税)"""
        trade_amount = price * quantity
        commission = max(trade_amount * 0.0003, 5.0)
        stamp_tax = trade_amount * 0.001 if trade_type == '卖出' else 0.0
        return commission, stamp_tax

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 position_ratio: float = 0.8, stop_loss: float = None) -> Dict:
        """
        回测引擎：计算指标 → 生成信号 → 模拟交易 → 统计结果

        Args:
            data: 含 date/open/high/low/close/volume 的 DataFrame
            initial_capital: 初始资金
            position_ratio: 单次买入仓位比例
            stop_loss: 止损比例（如 0.02 表示亏 2% 平仓）
        """
        data_with_indicators = self.calculate_indicators(data)
        signals = self.generate_signals(data_with_indicators)

        cash = initial_capital
        position = 0
        cost = 0.0
        equity_curve = []
        trades = []

        for signal in signals:
            price = signal['close']
            position_value = position * price if position > 0 else 0
            total_equity = cash + position_value
            equity_curve.append({'date': signal['date'], 'equity': total_equity,
                                 'cash': cash, 'position': position,
                                 'position_value': position_value})

            # 止损检查
            if stop_loss and position > 0:
                pnl_ratio = (price - cost) / cost
                if pnl_ratio <= -stop_loss:
                    comm, tax = self._calculate_fees(price, position, '卖出')
                    profit = position * price - position * cost - comm - tax
                    cash += position * price - comm - tax
                    trades.append({'date': signal['date'], 'type': '卖出',
                                   'price': price, 'quantity': position, 'profit': profit})
                    position, cost = 0, 0.0
                    continue

            if signal['signal'] == 'BUY' and position == 0:
                qty = int(cash * position_ratio / price)
                if qty > 0:
                    comm, tax = self._calculate_fees(price, qty, '买入')
                    total_cost = qty * price + comm + tax
                    if total_cost <= cash:
                        cash -= total_cost
                        position, cost = qty, price
                        trades.append({'date': signal['date'], 'type': '买入',
                                       'price': price, 'quantity': qty, 'profit': 0})

            elif signal['signal'] == 'SELL' and position > 0:
                comm, tax = self._calculate_fees(price, position, '卖出')
                profit = position * price - position * cost - comm - tax
                cash += position * price - comm - tax
                trades.append({'date': signal['date'], 'type': '卖出',
                               'price': price, 'quantity': position, 'profit': profit})
                position, cost = 0, 0.0

        # 计算最终权益（未平仓按最后价格计）
        if position > 0:
            final_equity = cash + position * data.iloc[-1]['close']
        else:
            final_equity = cash

        total_return = (final_equity - initial_capital) / initial_capital

        last_date = pd.to_datetime(data.iloc[-1]['date'])
        first_date = pd.to_datetime(data.iloc[0]['date'])
        years = (last_date - first_date).days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        sell_profits = [t['profit'] for t in trades if t['type'] == '卖出']
        winning = [p for p in sell_profits if p > 0]
        losing = [p for p in sell_profits if p < 0]
        win_rate = len(winning) / len(sell_profits) if sell_profits else 0.0

        avg_win = np.mean(winning) if winning else 0
        avg_loss = abs(np.mean(losing)) if losing else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

        equity_df = pd.DataFrame(equity_curve)
        max_drawdown, max_drawdown_ratio = self._calculate_max_drawdown(equity_df['equity'])
        equity_returns = equity_df['equity'].pct_change().dropna()
        volatility = equity_returns.std() * np.sqrt(252)
        sharpe_ratio = self._calculate_sharpe_ratio(equity_returns)

        return {
            'strategy_name': self.strategy_name,
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'max_drawdown_ratio': max_drawdown_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': len(sell_profits),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'trades': trades,
            'equity_curve': equity_curve
        }
