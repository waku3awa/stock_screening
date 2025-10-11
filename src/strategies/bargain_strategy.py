# -*- coding: utf-8 -*-
"""
Bargain Strategy

Implements a long/short strategy based on price movements relative to 200-day moving average.
Converted from PineScript (src_poc/bargain_storategy.pine).
"""

from typing import Dict, Any
import pandas as pd
import pytz
from datetime import datetime
from .base import BaseStrategy, StrategyResult, TradeRecord


class BargainStrategy(BaseStrategy):
    """
    Bargain hunting trading strategy.

    Strategy Logic:
    - Buy Signal: Price drops X% over 2 bars while below 200-day MA
    - Sell Signal: Price rises Y% over 2 bars while above 200-day MA
    - Position Sizing: Annual budget with per-trade purchase limits
    - Pyramiding: Allows multiple buy entries (position accumulation)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration
                - ma_period: Moving average period (default: 200)
                - drop_percentage: Drop % threshold for buy (default: 3.0)
                - rise_percentage: Rise % threshold for sell (default: 5.0)
                - annual_budget: Total annual budget (default: 2400000)
                - purchase_limit: Max purchase per trade (default: 100000)
        """
        self.ma_period = config.get('ma_period', 200)
        self.drop_percentage = config.get('drop_percentage', 3.0)
        self.rise_percentage = config.get('rise_percentage', 5.0)
        self.annual_budget = config.get('annual_budget', 2400000)
        self.purchase_limit = config.get('purchase_limit', 100000)
        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate configuration."""
        if self.ma_period <= 0:
            raise ValueError(f"MA period must be positive: {self.ma_period}")

        if self.drop_percentage <= 0:
            raise ValueError(f"Drop percentage must be positive: {self.drop_percentage}")

        if self.rise_percentage <= 0:
            raise ValueError(f"Rise percentage must be positive: {self.rise_percentage}")

        if self.annual_budget <= 0:
            raise ValueError(f"Annual budget must be positive: {self.annual_budget}")

        if self.purchase_limit <= 0:
            raise ValueError(f"Purchase limit must be positive: {self.purchase_limit}")

    def calculate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate trading signals.

        Args:
            price_data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals and indicators
        """
        df_result = price_data.copy()

        # Calculate moving average
        df_result['MA200'] = self.calculate_moving_average(
            df_result['Close'],
            self.ma_period,
            min_periods=self.ma_period
        )

        # Valuation flags
        df_result['overvalued'] = df_result['Close'] > df_result['MA200']
        df_result['undervalued'] = df_result['Close'] < df_result['MA200']

        # Shifted price data
        close_t0 = df_result['Close']
        close_t1 = df_result['Close'].shift(1)
        close_t2 = df_result['Close'].shift(2)

        # MA must be valid (not NaN)
        ma_valid = df_result['MA200'].notna()

        # Trend detection
        down_trend_start = close_t2 > close_t1
        up_trend_start = close_t2 < close_t1

        # Calculate price change rates with zero-division protection
        drop_rate = pd.Series(0.0, index=df_result.index)
        rise_rate = pd.Series(0.0, index=df_result.index)

        valid_c2 = (close_t2.notna()) & (close_t2 != 0)
        drop_rate[valid_c2] = ((close_t2[valid_c2] - close_t0[valid_c2]) / close_t2[valid_c2]) * 100
        rise_rate[valid_c2] = ((close_t0[valid_c2] - close_t2[valid_c2]) / close_t2[valid_c2]) * 100

        # Buy condition
        buy_condition = (
            ma_valid &
            (close_t0 <= df_result['MA200']) &
            down_trend_start &
            (drop_rate >= self.drop_percentage)
        )

        # Sell condition
        sell_condition = (
            ma_valid &
            (close_t0 >= df_result['MA200']) &
            up_trend_start &
            (rise_rate >= self.rise_percentage)
        )

        # Set signals: 1=buy, -1=sell, 0=hold
        df_result['signal'] = 0
        df_result.loc[buy_condition, 'signal'] = 1
        df_result.loc[sell_condition, 'signal'] = -1

        # Store rates for analysis
        df_result['drop_rate'] = drop_rate
        df_result['rise_rate'] = rise_rate

        return df_result

    def simulate(
        self,
        price_data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime
    ) -> StrategyResult:
        """
        Simulate the strategy with budget management.

        Args:
            price_data: DataFrame with signals
            start_date: Simulation start date
            end_date: Simulation end date

        Returns:
            StrategyResult: Simulation results
        """
        # Convert dates to timezone-aware if needed
        if price_data.index.tzinfo is not None:
            start_date = pytz.UTC.localize(start_date) if start_date.tzinfo is None else start_date
            end_date = pytz.UTC.localize(end_date) if end_date.tzinfo is None else end_date

        # Filter to simulation period
        df_sim = price_data.loc[start_date:end_date].copy()

        if df_sim.empty:
            return StrategyResult(
                trades=[],
                summary={
                    'error': 'No data in specified period',
                    'start_date': start_date,
                    'end_date': end_date
                },
                signals_df=pd.DataFrame()
            )

        # Initialize tracking variables
        remaining_budget = self.annual_budget
        position_shares = 0
        total_cost = 0.0
        trades = []

        # Get start price for buy-and-hold comparison
        start_price = df_sim.iloc[0]['Close']

        # Simulate trading
        for idx, row in df_sim.iterrows():
            date = idx
            close_price = row['Close']
            signal = row['signal']

            # Buy signal - Allow pyramiding
            if signal == 1 and remaining_budget > 0:
                max_dollars = min(self.purchase_limit, remaining_budget)
                shares = int(max_dollars // close_price)

                if shares > 0:
                    cost = shares * close_price
                    position_shares += shares
                    total_cost += cost
                    remaining_budget -= cost

                    trades.append(TradeRecord(
                        date=date,
                        action='BUY',
                        price=close_price,
                        shares=shares,
                        amount=cost,
                        position_shares=position_shares,
                        remaining_budget=remaining_budget
                    ))

            # Sell signal - Close all positions
            elif signal == -1 and position_shares > 0:
                proceeds = position_shares * close_price
                remaining_budget += proceeds

                avg_entry_price = total_cost / position_shares if position_shares > 0 else 0
                trade_return = ((close_price - avg_entry_price) / avg_entry_price) * 100 if avg_entry_price > 0 else 0

                trades.append(TradeRecord(
                    date=date,
                    action='SELL',
                    price=close_price,
                    shares=position_shares,
                    amount=proceeds,
                    position_shares=0,
                    remaining_budget=remaining_budget,
                    avg_entry_price=avg_entry_price,
                    return_pct=trade_return
                ))

                position_shares = 0
                total_cost = 0.0

        # Final position close
        if position_shares > 0:
            end_price = df_sim.iloc[-1]['Close']
            proceeds = position_shares * end_price
            remaining_budget += proceeds

            avg_entry_price = total_cost / position_shares if position_shares > 0 else 0
            trade_return = ((end_price - avg_entry_price) / avg_entry_price) * 100 if avg_entry_price > 0 else 0

            trades.append(TradeRecord(
                date=df_sim.index[-1],
                action='FINAL_CLOSE',
                price=end_price,
                shares=position_shares,
                amount=proceeds,
                position_shares=0,
                remaining_budget=remaining_budget,
                avg_entry_price=avg_entry_price,
                return_pct=trade_return
            ))

        # Calculate summary statistics
        final_capital = remaining_budget
        capital_gain_rate = ((final_capital - self.annual_budget) / self.annual_budget) * 100

        end_price = df_sim.iloc[-1]['Close']
        buy_and_hold_gain_rate = ((end_price - start_price) / start_price) * 100

        trades_list = [t for t in trades if t.action in ['BUY', 'SELL']]
        buy_trades = [t for t in trades_list if t.action == 'BUY']
        sell_trades = [t for t in trades_list if t.action == 'SELL']

        summary = {
            'start_date': start_date,
            'end_date': end_date,
            'annual_budget': self.annual_budget,
            'final_capital': final_capital,
            'capital_gain_rate': capital_gain_rate,
            'buy_and_hold_gain_rate': buy_and_hold_gain_rate,
            'strategy_advantage': capital_gain_rate - buy_and_hold_gain_rate,
            'start_price': start_price,
            'end_price': end_price,
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades)
        }

        return StrategyResult(
            trades=trades,
            summary=summary,
            signals_df=df_sim
        )
