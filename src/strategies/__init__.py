"""
Strategies package

Trading strategy implementations for backtesting.
"""

from .base import BaseStrategy, StrategyResult, TradeRecord
from .bargain_strategy import BargainStrategy

__all__ = [
    'BaseStrategy',
    'StrategyResult',
    'TradeRecord',
    'BargainStrategy',
]
