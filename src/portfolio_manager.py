#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Portfolio Management System

A simple portfolio management system for tracking stock holdings.
Supports Japanese stock market (Tokyo Stock Exchange) by default.

Usage:
    # Register trades interactively
    python src/portfolio_manager.py --mode register

    # Display current portfolio
    python src/portfolio_manager.py --mode display

    # Specify different market
    python src/portfolio_manager.py --mode register --market NYSE
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.portfolio import PortfolioStorage, StockPricingService
from src.portfolio.cli import PortfolioCLI
from src.config import PROJECT_ROOT as CONFIG_PROJECT_ROOT


def main():
    """Main entry point for portfolio manager"""

    parser = argparse.ArgumentParser(
        description="Portfolio Management System for Stock Holdings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register new trades
  %(prog)s --mode register

  # Display current portfolio
  %(prog)s --mode display

  # Use different market
  %(prog)s --mode register --market NYSE
        """
    )

    parser.add_argument(
        '--mode',
        choices=['register', 'display'],
        required=True,
        help='Operating mode: register (add trades) or display (show portfolio)'
    )

    parser.add_argument(
        '--market',
        default='TSE',
        help='Market identifier (default: TSE for Tokyo Stock Exchange)'
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=None,
        help='Portfolio data directory (default: PROJECT_ROOT/data/portfolio)'
    )

    parser.add_argument(
        '--data-j-xls',
        type=Path,
        default=None,
        help='Path to data_j.xls file (default: PROJECT_ROOT/data/data_j.xls)'
    )

    args = parser.parse_args()

    # Set default paths
    data_dir = args.data_dir or (CONFIG_PROJECT_ROOT / "data" / "portfolio")
    data_j_xls = args.data_j_xls or (CONFIG_PROJECT_ROOT / "data" / "data_j.xls")

    # Determine market suffix
    market_suffix = ".T" if args.market == "TSE" else ""

    # Initialize services
    print(f"\n{'='*60}")
    print(f"Portfolio Management System")
    print(f"{'='*60}")
    print(f"Mode: {args.mode}")
    print(f"Market: {args.market}")
    print(f"Data Directory: {data_dir}")
    print(f"Stock Database: {data_j_xls}")
    print(f"{'='*60}\n")

    try:
        # Initialize storage
        storage = PortfolioStorage(data_dir)

        # Initialize pricing service
        pricing = StockPricingService(data_j_xls, market_suffix)

        # Initialize CLI
        cli = PortfolioCLI(storage, pricing, args.market)

        # Execute mode
        if args.mode == 'register':
            cli.register_mode()
        elif args.mode == 'display':
            cli.display_mode()

    except KeyboardInterrupt:
        print("\n\nプログラムを終了します。")
        sys.exit(0)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
