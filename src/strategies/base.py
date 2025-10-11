"""
Strategy Base Class

Base class for all backtesting strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TradeRecord:
    """Individual trade record"""
    date: datetime
    action: str  # 'BUY', 'SELL', 'FINAL_CLOSE'
    price: float
    shares: int
    amount: float
    position_shares: int
    remaining_budget: float
    avg_entry_price: Optional[float] = None
    return_pct: Optional[float] = None


@dataclass
class StrategyResult:
    """Strategy simulation result"""
    trades: List[TradeRecord]
    summary: Dict[str, Any]
    signals_df: pd.DataFrame


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    All strategies should inherit from this class and implement
    the required abstract methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration dictionary
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    @abstractmethod
    def calculate_signals(
        self,
        price_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate trading signals for the given price data.

        Args:
            price_data: DataFrame with OHLCV data

        Returns:
            DataFrame with signals and indicators
        """
        pass

    @abstractmethod
    def simulate(
        self,
        price_data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime
    ) -> StrategyResult:
        """
        Simulate the strategy over a specified period.

        Args:
            price_data: DataFrame with OHLCV data and signals
            start_date: Simulation start date
            end_date: Simulation end date

        Returns:
            StrategyResult: Simulation results
        """
        pass

    def backtest(
        self,
        ticker: str,
        price_data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime
    ) -> StrategyResult:
        """
        Run full backtest: calculate signals and simulate trading.

        Args:
            ticker: Stock ticker symbol
            price_data: DataFrame with OHLCV data
            start_date: Simulation start date
            end_date: Simulation end date

        Returns:
            StrategyResult: Complete backtest results
        """
        # Calculate signals
        signals_df = self.calculate_signals(price_data)

        # Run simulation
        result = self.simulate(signals_df, start_date, end_date)

        # Add ticker to summary
        result.summary['ticker'] = ticker

        return result

    @staticmethod
    def calculate_moving_average(
        prices: pd.Series,
        period: int,
        min_periods: Optional[int] = None
    ) -> pd.Series:
        """
        Calculate moving average.

        Args:
            prices: Price data
            period: Moving average period
            min_periods: Minimum number of observations required

        Returns:
            pd.Series: Moving average values
        """
        if min_periods is None:
            min_periods = period
        return prices.rolling(window=period, min_periods=min_periods).mean()

    @staticmethod
    def is_valid_data(
        price_data: pd.DataFrame,
        required_days: int
    ) -> bool:
        """
        Validate data quality.

        Args:
            price_data: Price data DataFrame
            required_days: Minimum required days

        Returns:
            bool: True if data is valid
        """
        if price_data is None or price_data.empty:
            return False

        if len(price_data) < required_days:
            return False

        # Check required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in price_data.columns for col in required_columns):
            return False

        return True
