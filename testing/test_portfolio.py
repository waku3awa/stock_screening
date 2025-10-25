#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script for portfolio management system"""

import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.portfolio import Trade, Position, PortfolioStorage, StockPricingService


def test_basic_functionality():
    """Test basic portfolio management functionality"""
    print("\n" + "="*60)
    print("Portfolio Management System - Basic Functionality Test")
    print("="*60 + "\n")

    # Setup paths
    test_data_dir = PROJECT_ROOT / "data" / "portfolio_test"
    data_j_xls = PROJECT_ROOT / "data" / "data_j.xls"

    # Clean test directory
    if test_data_dir.exists():
        trades_file = test_data_dir / "trades.csv"
        if trades_file.exists():
            trades_file.unlink()

    # Initialize services
    storage = PortfolioStorage(test_data_dir)
    pricing = StockPricingService(data_j_xls, ".T")

    print("1. Testing Trade Creation and Storage")
    print("-" * 40)

    # Create sample trades
    trades = [
        Trade(
            trade_date=date(2025, 10, 1),
            ticker_local="7203",
            ticker_yf="7203.T",
            stock_name="トヨタ自動車",
            side="BUY",
            quantity=100,
            price=Decimal("3000"),
            commission=Decimal("100"),
            market="TSE",
            currency="JPY",
            notes="初回購入"
        ),
        Trade(
            trade_date=date(2025, 10, 15),
            ticker_local="6758",
            ticker_yf="6758.T",
            stock_name="ソニーグループ",
            side="BUY",
            quantity=50,
            price=Decimal("12000"),
            commission=Decimal("150"),
            market="TSE",
            currency="JPY",
            notes="追加購入"
        ),
    ]

    # Save trades
    for trade in trades:
        storage.append_trade(trade)
        print(f"[OK] Saved: {trade.stock_name} ({trade.ticker_local}) - {trade.quantity}株 @ {trade.price}円")

    print("\n2. Testing Trade Loading")
    print("-" * 40)

    loaded_trades = storage.load_all_trades()
    print(f"[OK] Loaded {len(loaded_trades)} trades from CSV")

    for trade in loaded_trades:
        print(f"  - {trade.stock_name}: {trade.quantity}株 @ {trade.price}円 (日付: {trade.trade_date})")

    print("\n3. Testing Position Calculation")
    print("-" * 40)

    positions = storage.calculate_positions(loaded_trades)
    print(f"[OK] Calculated {len(positions)} positions")

    for pos in positions:
        print(f"  - {pos.stock_name} ({pos.ticker_local})")
        print(f"    保有数: {pos.quantity}株")
        print(f"    平均取得単価: {pos.avg_cost:,.2f}円")
        print(f"    取得総額: {pos.total_cost:,.0f}円")

    print("\n4. Testing Stock Name Lookup")
    print("-" * 40)

    test_tickers = ["7203", "6758", "9984"]
    for ticker in test_tickers:
        ticker_yf = pricing.format_ticker(ticker, "TSE")
        stock_name = pricing.get_stock_name(ticker, ticker_yf)
        print(f"[OK] {ticker} ({ticker_yf}) -> {stock_name}")

    print("\n5. Testing Current Price Fetching")
    print("-" * 40)

    for pos in positions:
        print(f"Fetching price for {pos.stock_name} ({pos.ticker_yf})...")
        current_price = pricing.get_current_price(pos.ticker_yf)

        if current_price:
            pos.current_price = current_price
            print(f"[OK] Current Price: {current_price:,.2f}円")
            print(f"  Unrealized P&L: {pos.unrealized_pnl:+,.0f}円 ({pos.unrealized_pnl_pct:+.2f}%)")
        else:
            print(f"[FAIL] Failed to fetch price")

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60 + "\n")

    print("Next steps:")
    print("  1. Register mode: python src/portfolio_manager.py --mode register")
    print("  2. Display mode: python src/portfolio_manager.py --mode display")


if __name__ == "__main__":
    test_basic_functionality()
