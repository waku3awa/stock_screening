# -*- coding: utf-8 -*-
"""Storage layer for portfolio data using CSV files"""

import csv
import os
from pathlib import Path
from typing import List, Dict
from decimal import Decimal
from collections import defaultdict

from .models import Trade, Position


class PortfolioStorage:
    """Handles CSV file operations for portfolio data"""

    FIELDNAMES = [
        'trade_id', 'trade_date', 'コード', 'ticker_yf', '銘柄名',
        'シグナル', 'quantity', 'price', 'commission', 'market', 'currency', 'notes'
    ]

    def __init__(self, data_dir: Path):
        """Initialize storage with data directory

        Args:
            data_dir: Directory to store portfolio data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trades.csv"

        # Create trades file with headers if it doesn't exist
        if not self.trades_file.exists():
            self._create_trades_file()

    def _create_trades_file(self):
        """Create trades.csv with headers"""
        with open(self.trades_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()

    def append_trade(self, trade: Trade):
        """Append a trade to trades.csv

        Args:
            trade: Trade object to append
        """
        with open(self.trades_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(trade.to_dict())

    def load_all_trades(self) -> List[Trade]:
        """Load all trades from CSV

        Returns:
            List of Trade objects
        """
        trades = []

        if not self.trades_file.exists():
            return trades

        with open(self.trades_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trades.append(Trade.from_dict(row))
                except Exception as e:
                    print(f"警告: 取引データの読み込みエラー - {e}")
                    continue

        return trades

    def calculate_positions(self, trades: List[Trade]) -> List[Position]:
        """Calculate current positions from trade history

        Uses simple average cost method for calculating cost basis.

        Args:
            trades: List of Trade objects

        Returns:
            List of Position objects
        """
        # Group trades by ticker
        ticker_trades = defaultdict(list)
        for trade in trades:
            ticker_trades[trade.ticker_yf].append(trade)

        positions = []

        for ticker_yf, ticker_trade_list in ticker_trades.items():
            # Sort by date
            ticker_trade_list.sort(key=lambda t: t.trade_date)

            total_quantity = 0
            total_cost = Decimal("0")
            stock_name = ""
            ticker_local = ""
            market = "TSE"
            currency = "JPY"

            for trade in ticker_trade_list:
                # Store metadata from latest trade
                stock_name = trade.stock_name
                ticker_local = trade.ticker_local
                market = trade.market
                currency = trade.currency

                if trade.side == "BUY":
                    total_quantity += trade.quantity
                    total_cost += trade.price * trade.quantity + trade.commission
                elif trade.side == "SELL":
                    # Simple average method: reduce quantity and proportional cost
                    if total_quantity > 0:
                        cost_per_share = total_cost / total_quantity
                        total_quantity -= trade.quantity
                        total_cost = cost_per_share * total_quantity

            # Only create position if there's remaining quantity
            if total_quantity > 0:
                avg_cost = total_cost / total_quantity
                position = Position(
                    ticker_local=ticker_local,
                    ticker_yf=ticker_yf,
                    stock_name=stock_name,
                    quantity=total_quantity,
                    avg_cost=avg_cost,
                    market=market,
                    currency=currency
                )
                positions.append(position)

        return positions

    def get_current_positions(self) -> List[Position]:
        """Get current positions from all trades

        Returns:
            List of Position objects
        """
        trades = self.load_all_trades()
        return self.calculate_positions(trades)
