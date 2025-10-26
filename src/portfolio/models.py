# -*- coding: utf-8 -*-
"""Data models for portfolio management"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass
class Trade:
    """Represents a single trade transaction (buy or sell)"""

    trade_id: str = field(default_factory=lambda: str(uuid4()))
    trade_date: date = field(default_factory=date.today)
    ticker_local: str = ""  # Local code without suffix (e.g., "7203")
    ticker_yf: str = ""  # yfinance symbol with suffix (e.g., "7203.T")
    stock_name: str = ""
    side: str = "BUY"  # BUY or SELL
    quantity: int = 0
    price: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    market: str = "TSE"  # Tokyo Stock Exchange
    currency: str = "JPY"
    notes: str = ""

    def __post_init__(self):
        """Validate and convert types after initialization"""
        # Convert date string to date object if needed
        if isinstance(self.trade_date, str):
            self.trade_date = datetime.strptime(self.trade_date, "%Y-%m-%d").date()

        # Ensure Decimal types
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))

        # Ensure uppercase for side
        self.side = self.side.upper()

        # Validate side
        if self.side not in ("BUY", "SELL"):
            raise ValueError(f"Invalid side: {self.side}. Must be BUY or SELL")

    @property
    def total_cost(self) -> Decimal:
        """Total cost including commission"""
        return self.price * self.quantity + self.commission

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
        return {
            'trade_id': self.trade_id,
            'trade_date': self.trade_date.strftime("%Y-%m-%d"),
            'コード': self.ticker_local,
            'ticker_yf': self.ticker_yf,
            '銘柄名': self.stock_name,
            'シグナル': self.side,
            'quantity': self.quantity,
            'price': str(self.price),
            'commission': str(self.commission),
            'market': self.market,
            'currency': self.currency,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        """Create Trade from dictionary (supports both old and new column names)"""
        return cls(
            trade_id=data['trade_id'],
            trade_date=datetime.strptime(data['trade_date'], "%Y-%m-%d").date(),
            ticker_local=data.get('コード', data.get('ticker_local', '')),
            ticker_yf=data['ticker_yf'],
            stock_name=data.get('銘柄名', data.get('stock_name', '')),
            side=data.get('シグナル', data.get('side', 'BUY')),
            quantity=int(data['quantity']),
            price=Decimal(data['price']),
            commission=Decimal(data['commission']),
            market=data['market'],
            currency=data['currency'],
            notes=data.get('notes', '')
        )


@dataclass
class Position:
    """Represents current holding position for a stock"""

    ticker_local: str
    ticker_yf: str
    stock_name: str
    quantity: int
    avg_cost: Decimal  # Average cost per share
    market: str
    currency: str
    current_price: Optional[Decimal] = None

    @property
    def total_cost(self) -> Decimal:
        """Total cost basis"""
        return self.avg_cost * self.quantity

    @property
    def market_value(self) -> Optional[Decimal]:
        """Current market value"""
        if self.current_price is None:
            return None
        return self.current_price * self.quantity

    @property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """Unrealized profit/loss"""
        if self.current_price is None:
            return None
        return self.market_value - self.total_cost

    @property
    def unrealized_pnl_pct(self) -> Optional[Decimal]:
        """Unrealized profit/loss percentage"""
        if self.current_price is None or self.total_cost == 0:
            return None
        return (self.unrealized_pnl / self.total_cost) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for display"""
        return {
            'ticker': self.ticker_local,
            'name': self.stock_name,
            'quantity': self.quantity,
            'avg_cost': float(self.avg_cost),
            'total_cost': float(self.total_cost),
            'current_price': float(self.current_price) if self.current_price else None,
            'market_value': float(self.market_value) if self.market_value else None,
            'pnl': float(self.unrealized_pnl) if self.unrealized_pnl else None,
            'pnl_pct': f"{float(self.unrealized_pnl_pct):.2f}%" if self.unrealized_pnl_pct else None
        }
