# -*- coding: utf-8 -*-
"""Stock pricing and metadata services"""

import pandas as pd
import yfinance_cache as yfc
from pathlib import Path
from typing import Optional, Dict
from decimal import Decimal
import warnings

warnings.filterwarnings('ignore')


class StockPricingService:
    """Provides stock name lookup and price fetching services"""

    def __init__(self, data_j_path: Path, market_suffix: str = ".T"):
        """Initialize pricing service

        Args:
            data_j_path: Path to data_j.xls file
            market_suffix: Suffix to append to ticker (e.g., ".T" for TSE)
        """
        self.data_j_path = Path(data_j_path)
        self.market_suffix = market_suffix
        self._stock_names_cache: Optional[Dict[str, str]] = None

    def _load_stock_names(self) -> Dict[str, str]:
        """Load stock names from data_j.xls

        Returns:
            Dictionary mapping ticker code to stock name
        """
        if self._stock_names_cache is not None:
            return self._stock_names_cache

        stock_names = {}

        try:
            # Read data_j.xls - assume second column is ticker, third is name
            df = pd.read_excel(self.data_j_path, engine='xlrd')

            # Get column names (handling encoding issues)
            columns = df.columns.tolist()

            if len(columns) >= 3:
                # Typically: 日付, コード, 銘柄名, ...
                ticker_col = columns[1]  # Second column is ticker
                name_col = columns[2]    # Third column is name

                for _, row in df.iterrows():
                    ticker = str(row[ticker_col]).strip()
                    name = str(row[name_col]).strip()

                    # Skip invalid entries
                    if ticker and name and ticker != 'nan' and name != 'nan':
                        stock_names[ticker] = name

                print(f"[INFO] Loaded {len(stock_names)} stock names from data_j.xls")

        except Exception as e:
            print(f"[WARNING] Failed to load data_j.xls: {e}")

        self._stock_names_cache = stock_names
        return stock_names

    def get_stock_name(self, ticker_local: str, ticker_yf: str) -> str:
        """Get stock name from data_j.xls or yfinance

        Args:
            ticker_local: Local ticker code (e.g., "7203")
            ticker_yf: yfinance symbol (e.g., "7203.T")

        Returns:
            Stock name
        """
        # Try data_j.xls first
        stock_names = self._load_stock_names()
        if ticker_local in stock_names:
            return stock_names[ticker_local]

        # Fallback to yfinance
        try:
            ticker = yfc.Ticker(ticker_yf)
            info = ticker.info

            # Try to get name from various fields
            name = (
                info.get('longName') or
                info.get('shortName') or
                info.get('name') or
                ticker_yf
            )
            return name

        except Exception as e:
            print(f"[WARNING] Failed to fetch name for {ticker_yf}: {e}")
            return ticker_yf

    def get_current_price(self, ticker_yf: str) -> Optional[Decimal]:
        """Get current price from yfinance

        Args:
            ticker_yf: yfinance symbol (e.g., "7203.T")

        Returns:
            Current price as Decimal, or None if unavailable
        """
        try:
            ticker = yfc.Ticker(ticker_yf)

            # Try fast_info first (faster)
            try:
                price = ticker.fast_info.get('lastPrice')
                if price and price > 0:
                    return Decimal(str(price))
            except:
                pass

            # Fallback to info
            info = ticker.info
            price = (
                info.get('regularMarketPrice') or
                info.get('currentPrice') or
                info.get('previousClose')
            )

            if price and price > 0:
                return Decimal(str(price))

            # Last resort: get latest close from history
            history = ticker.history(period="1d")
            if not history.empty and 'Close' in history.columns:
                close_price = history['Close'].iloc[-1]
                return Decimal(str(close_price))

        except Exception as e:
            print(f"[WARNING] Failed to fetch price for {ticker_yf}: {e}")

        return None

    def format_ticker(self, ticker_local: str, market: str = "TSE") -> str:
        """Format local ticker to yfinance symbol

        Args:
            ticker_local: Local ticker code (e.g., "7203")
            market: Market identifier (e.g., "TSE")

        Returns:
            yfinance symbol (e.g., "7203.T")
        """
        if market == "TSE":
            return f"{ticker_local}{self.market_suffix}"
        else:
            # For other markets, may need different logic
            return ticker_local
