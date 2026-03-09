#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化策略基类
定义所有量化策略的通用接口和基础功能
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging


class BaseStrategy(ABC):
    """量化策略基类"""
    
    def __init__(self, strategy_name: str, parameters: Dict):
        """
        初始化策略
        
        Args:
            strategy_name: 策略名称
            parameters: 策略参数
        """
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.logger = logging.getLogger(f"Strategy_{strategy_name}")
        
        # 策略状态
        self.is_position = False  # 是否有持仓
        self.position_stock = None  # 持仓股票
        self.position_quantity = 0  # 持仓数量
        self.position_cost = 0.0  # 持仓成本
        self.position_time = None  # 持仓开始时间
        
        # 交易记录
        self.trade_signals = []  # 交易信号
        self.trade_history = []  # 交易历史
        
        # 策略指标
        self.total_return = 0.0  # 总收益率
        self.total_trades = 0  # 总交易次数
        self.winning_trades = 0  # 盈利交易次数
        self.losing_trades = 0  # 亏损交易次数
        
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 历史数据
            
        Returns:
            包含技术指标的数据
        """
        pass
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 包含技术指标的数据
            
        Returns:
            交易信号列表
        """
        pass
        
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算常用技术指标（子类可以重写）
        
        Args:
            data: 历史数据
            
        Returns:
            包含技术指标的数据
        """
        df = data.copy()
        
        # 计算移动平均线
        if 'ma5' in self.parameters:
            df['ma5'] = df['close'].rolling(window=self.parameters['ma5']).mean()
        if 'ma20' in self.parameters:
            df['ma20'] = df['close'].rolling(window=self.parameters['ma20']).mean()
        if 'ma60' in self.parameters:
            df['ma60'] = df['close'].rolling(window=self.parameters['ma60']).mean()
            
        # 计算布林带
        if 'bb_period' in self.parameters:
            period = self.parameters['bb_period']
            std = df['close'].rolling(window=period).std()
            df['bb_middle'] = df['close'].rolling(window=period).mean()
            df['bb_upper'] = df['bb_middle'] + (std * self.parameters.get('bb_std', 2))
            df['bb_lower'] = df['bb_middle'] - (std * self.parameters.get('bb_std', 2))
            
        # 计算RSI
        if 'rsi_period' in self.parameters:
            df['rsi'] = self._calculate_rsi(df['close'], self.parameters['rsi_period'])
            
        # 计算成交量
        if 'volume_ma' in self.parameters:
            df['volume_ma'] = df['volume'].rolling(window=self.parameters['volume_ma']).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
        return df
        
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            RSI序列
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算ATR指标（平均真实波幅）
        
        Args:
            data: OHLC数据
            period: 计算周期
            
        Returns:
            ATR序列
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
        
    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> Tuple[float, float]:
        """
        计算最大回撤
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            (最大回撤金额, 最大回撤比例)
        """
        cumulative_max = equity_curve.cummax()
        drawdown = cumulative_max - equity_curve
        max_drawdown = drawdown.max()
        max_drawdown_ratio = (max_drawdown / cumulative_max).max()
        
        return max_drawdown, max_drawdown_ratio
        
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率
            
        Returns:
            夏普比率
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
            
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        
        return sharpe_ratio
        
    def _calculate_win_rate(self, profits: List[float]) -> float:
        """
        计算胜率
        
        Args:
            profits: 盈亏列表
            
        Returns:
            胜率
        """
        if not profits:
            return 0.0
            
        winning_trades = sum(1 for p in profits if p > 0)
        total_trades = len(profits)
        
        return winning_trades / total_trades if total_trades > 0 else 0.0
        
    def _calculate_profit_loss_ratio(self, profits: List[float]) -> float:
        """
        计算盈亏比
        
        Args:
            profits: 盈亏列表
            
        Returns:
            盈亏比
        """
        if not profits:
            return 0.0
            
        profits = np.array(profits)
        profits = profits[profits != 0]  # 排除零盈亏
        
        if len(profits) == 0:
            return 0.0
            
        profits = profits[profits != 0]
        if len(profits) == 0:
            return 0.0
            
        winning_profits = profits[profits > 0]
        losing_profits = profits[profits < 0]
        
        if len(winning_profits) == 0 or len(losing_profits) == 0:
            return 0.0
            
        avg_win = winning_profits.mean()
        avg_loss = abs(losing_profits.mean())
        
        return avg_win / avg_loss if avg_loss > 0 else 0.0
        
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 position_ratio: float = 0.8, stop_loss: float = None) -> Dict:
        """
        回测策略
        
        Args:
            data: 历史数据
            initial_capital: 初始资金
            position_ratio: 仓位比例
            stop_loss: 止损比例
            
        Returns:
            回测结果
        """
        # 重置策略状态
        self.reset_strategy()
        
        # 计算技术指标
        data_with_indicators = self.calculate_indicators(data)
        
        # 生成交易信号
        signals = self.generate_signals(data_with_indicators)
        
        # 初始化账户
        current_capital = initial_capital
        current_position = 0
        position_cost = 0.0
        position_stock = None
        
        # 记录权益曲线
        equity_curve = []
        
        # 记录交易记录
        trades = []
        
        # 执行回测
        for i, signal in enumerate(signals):
            date = signal['date']
            price = signal['close']
            
            # 更新权益
            if current_position > 0 and position_stock:
                position_value = current_position * price
                total_equity = current_capital + position_value
            else:
                total_equity = current_capital
                
            equity_curve.append({
                'date': date,
                'equity': total_equity,
                'cash': current_capital,
                'position': current_position,
                'position_value': current_position * price if current_position > 0 else 0
            })
            
            # 检查止损
            if stop_loss and current_position > 0 and position_stock:
                current_pnl = (price - position_cost) * current_position
                pnl_ratio = current_pnl / (position_cost * current_position)
                
                if pnl_ratio <= -stop_loss:
                    # 触发止损
                    trade_amount = current_position * price
                    commission, stamp_tax = self._calculate_fees(price, current_position, '卖出')
                    total_cost = trade_amount + commission + stamp_tax
                    
                    current_capital += trade_amount - commission - stamp_tax
                    profit = trade_amount - position_cost * current_position - commission - stamp_tax
                    
                    # 记录交易
                    trades.append({
                        'date': date,
                        'type': '卖出',
                        'direction': '平仓',
                        'stock': position_stock,
                        'price': price,
                        'quantity': current_position,
                        'amount': trade_amount,
                        'commission': commission,
                        'stamp_tax': stamp_tax,
                        'total_cost': total_cost,
                        'profit': profit,
                        'profit_ratio': profit / (position_cost * current_position)
                    })
                    
                    # 重置持仓
                    current_position = 0
                    position_cost = 0.0
                    position_stock = None
                    
                    continue
            
            # 执行交易信号
            if signal['signal'] == 'BUY' and current_position == 0:
                # 买入信号
                available_amount = current_capital * position_ratio
                quantity = int(available_amount / price)
                
                if quantity > 0:
                    trade_amount = quantity * price
                    commission, stamp_tax = self._calculate_fees(price, quantity, '买入')
                    total_cost = trade_amount + commission + stamp_tax
                    
                    if total_cost <= current_capital:
                        current_capital -= total_cost
                        current_position = quantity
                        position_cost = price
                        position_stock = signal['stock_code']
                        
                        # 记录交易
                        trades.append({
                            'date': date,
                            'type': '买入',
                            'direction': '开仓',
                            'stock': position_stock,
                            'price': price,
                            'quantity': quantity,
                            'amount': trade_amount,
                            'commission': commission,
                            'stamp_tax': stamp_tax,
                            'total_cost': total_cost,
                            'profit': 0,
                            'profit_ratio': 0
                        })
                        
            elif signal['signal'] == 'SELL' and current_position > 0:
                # 卖出信号
                trade_amount = current_position * price
                commission, stamp_tax = self._calculate_fees(price, current_position, '卖出')
                total_cost = trade_amount + commission + stamp_tax
                
                current_capital += trade_amount - commission - stamp_tax
                profit = trade_amount - position_cost * current_position - commission - stamp_tax
                
                # 记录交易
                trades.append({
                    'date': date,
                    'type': '卖出',
                    'direction': '平仓',
                    'stock': position_stock,
                    'price': price,
                    'quantity': current_position,
                    'amount': trade_amount,
                    'commission': commission,
                    'stamp_tax': stamp_tax,
                    'total_cost': total_cost,
                    'profit': profit,
                    'profit_ratio': profit / (position_cost * current_position)
                })
                
                # 重置持仓
                current_position = 0
                position_cost = 0.0
                position_stock = None
        
        # 计算最终权益
        if current_position > 0 and position_stock:
            final_position_value = current_position * data.iloc[-1]['close']
            final_equity = current_capital + final_position_value
        else:
            final_equity = current_capital
            
        # 计算收益率
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算年化收益率
        last_date = pd.to_datetime(data.iloc[-1]['date'])
        first_date = pd.to_datetime(data.iloc[0]['date'])
        years = (last_date - first_date).days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 计算交易统计
        profits = [trade['profit'] for trade in trades if trade['type'] == '卖出']
        win_rate = self._calculate_win_rate(profits)
        profit_loss_ratio = self._calculate_profit_loss_ratio(profits)
        
        # 计算最大回撤
        equity_df = pd.DataFrame(equity_curve)
        max_drawdown, max_drawdown_ratio = self._calculate_max_drawdown(equity_df['equity'])
        
        # 计算波动率和夏普比率
        equity_returns = equity_df['equity'].pct_change().dropna()
        volatility = equity_returns.std() * np.sqrt(252)  # 年化波动率
        sharpe_ratio = self._calculate_sharpe_ratio(equity_returns)
        
        # 更新策略统计
        self.total_return = total_return
        self.total_trades = len([t for t in trades if t['type'] == '卖出'])
        self.winning_trades = len([p for p in profits if p > 0])
        self.losing_trades = len([p for p in profits if p < 0])
        
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
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'trades': trades,
            'equity_curve': equity_curve
        }
        
    def _calculate_fees(self, price: float, quantity: int, trade_type: str) -> Tuple[float, float]:
        """
        计算交易费用
        
        Args:
            price: 交易价格
            quantity: 交易数量
            trade_type: 交易类型
            
        Returns:
            (手续费, 印花税)
        """
        trade_amount = price * quantity
        
        # 手续费：双向收取，按0.0003计算，最低5元
        commission = max(trade_amount * 0.0003, 5.0)
        
        # 印花税：仅卖出收取，按0.001计算
        stamp_tax = trade_amount * 0.001 if trade_type == '卖出' else 0.0
        
        return commission, stamp_tax
        
    def reset_strategy(self):
        """重置策略状态"""
        self.is_position = False
        self.position_stock = None
        self.position_quantity = 0
        self.position_cost = 0.0
        self.position_time = None
        self.trade_signals = []
        self.trade_history = []
        self.total_return = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
    def get_strategy_info(self) -> Dict:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_return': self.total_return
        }