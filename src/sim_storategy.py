# -*- coding: utf-8 -*-
"""Bargain Strategy - CLI Interface

Command-line interface for the bargain hunting strategy.
Uses the refactored BargainStrategy class from strategies module.
"""

import argparse
import yfinance_cache as yfc
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from strategies.bargain_strategy import BargainStrategy


def main():
    parser = argparse.ArgumentParser(
        description='Bargain Strategy - Python Implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with Toyota stock
  python src/bargain_strategy.py --ticker 7203.T

  # Custom parameters
  python src/bargain_strategy.py --ticker 7203.T --start-year 2023 --drop 5.0 --rise 7.0

  # Specify output directory
  python src/bargain_strategy.py --ticker 7203.T --output results/
        """
    )

    # Required arguments
    parser.add_argument('--ticker', type=str, required=True,
                        help='Stock ticker symbol (e.g., 7203.T for Toyota)')

    # Simulation parameters
    parser.add_argument('--start-year', type=int, default=2024,
                        help='Simulation start year (default: 2024)')
    parser.add_argument('--start-month', type=int, default=1,
                        help='Simulation start month (default: 1)')
    parser.add_argument('--annual-budget', type=float, default=2400000,
                        help='Annual budget in JPY (default: 2,400,000)')
    parser.add_argument('--purchase-limit', type=float, default=100000,
                        help='Maximum purchase per trade in JPY (default: 100,000)')

    # Strategy parameters
    parser.add_argument('--drop', type=float, default=3.0,
                        help='Drop percentage threshold for buy signal (default: 3.0)')
    parser.add_argument('--rise', type=float, default=5.0,
                        help='Rise percentage threshold for sell signal (default: 5.0)')
    parser.add_argument('--ma-period', type=int, default=200,
                        help='Moving average period (default: 200)')

    # Output settings
    parser.add_argument('--output', type=str, default='.',
                        help='Output directory for CSV file (default: current directory)')

    args = parser.parse_args()

    # Prepare date range
    start_date = datetime(args.start_year, args.start_month, 1)
    end_date = datetime(args.start_year + 1, args.start_month, 1) - timedelta(days=1)

    # Need data from before start_date for MA calculation
    data_start = start_date - timedelta(days=args.ma_period * 2)

    print(f"{'='*60}")
    print(f"Bargain Strategy Simulation")
    print(f"{'='*60}")
    print(f"Ticker: {args.ticker}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Annual Budget: JPY {args.annual_budget:,.0f}")
    print(f"Purchase Limit: JPY {args.purchase_limit:,.0f}")
    print(f"Drop Threshold: {args.drop}%")
    print(f"Rise Threshold: {args.rise}%")
    print(f"MA Period: {args.ma_period} days")
    print(f"{'='*60}\n")

    # Download data
    print(f"Downloading data from {data_start.date()}...")
    try:
        ticker = yfc.Ticker(args.ticker)
        df = ticker.history(start=data_start, end=end_date + timedelta(days=1))

        if df.empty:
            print(f"ERROR: No data available for {args.ticker}")
            return

        print(f"Downloaded {len(df)} days of data\n")

    except Exception as e:
        print(f"ERROR downloading data: {e}")
        return

    # Initialize strategy with configuration
    strategy_config = {
        'ma_period': args.ma_period,
        'drop_percentage': args.drop,
        'rise_percentage': args.rise,
        'annual_budget': args.annual_budget,
        'purchase_limit': args.purchase_limit
    }

    strategy = BargainStrategy(strategy_config)

    # Run backtest
    print("Running backtest...")
    result = strategy.backtest(
        ticker=args.ticker,
        price_data=df,
        start_date=start_date,
        end_date=end_date
    )

    if 'error' in result.summary:
        print(f"ERROR: {result.summary['error']}")
        return

    # Convert trades to DataFrame for display
    trades_data = []
    for trade in result.trades:
        trades_data.append({
            'date': trade.date,
            'action': trade.action,
            'price': trade.price,
            'shares': trade.shares,
            'amount': trade.amount,
            'position_shares': trade.position_shares,
            'remaining_budget': trade.remaining_budget,
            'avg_entry_price': trade.avg_entry_price,
            'return_pct': trade.return_pct
        })
    trades_df = pd.DataFrame(trades_data)

    # Print results to stdout
    summary = result.summary
    print(f"\n{'='*60}")
    print("SIMULATION RESULTS")
    print(f"{'='*60}")
    print(f"Initial Capital:        JPY {summary['annual_budget']:,.0f}")
    print(f"Final Capital:          JPY {summary['final_capital']:,.0f}")
    print(f"Strategy Gain:          {summary['capital_gain_rate']:+.2f}%")
    print(f"Buy-and-Hold Gain:      {summary['buy_and_hold_gain_rate']:+.2f}%")
    print(f"Strategy Advantage:     {summary['strategy_advantage']:+.2f}%")
    print(f"\nPrice Movement:")
    print(f"  Start Price: JPY {summary['start_price']:,.2f}")
    print(f"  End Price:   JPY {summary['end_price']:,.2f}")
    print(f"\nTrading Activity:")
    print(f"  Total Trades: {summary['total_trades']}")
    print(f"  Buy Orders:   {summary['buy_trades']}")
    print(f"  Sell Orders:  {summary['sell_trades']}")
    print(f"{'='*60}\n")

    if not trades_df.empty:
        print("Trade History:")
        print(trades_df.to_string(index=False))
        print()

    # Save to CSV and TXT
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"bargain_{timestamp}"
    csv_path = output_dir / f"{base_filename}.csv"
    txt_path = output_dir / f"{base_filename}.txt"

    # Save summary to TXT file
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"Bargain Strategy Simulation Results\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Ticker: {args.ticker}\n")
        f.write(f"Period: {start_date.date()} to {end_date.date()}\n\n")
        f.write(f"Configuration:\n")
        f.write(f"  Annual Budget: JPY {summary['annual_budget']:,.0f}\n")
        f.write(f"  Purchase Limit: JPY {args.purchase_limit:,.0f}\n")
        f.write(f"  Drop Threshold: {args.drop}%\n")
        f.write(f"  Rise Threshold: {args.rise}%\n")
        f.write(f"  MA Period: {args.ma_period} days\n\n")
        f.write(f"Results:\n")
        f.write(f"  Initial Capital: JPY {summary['annual_budget']:,.0f}\n")
        f.write(f"  Final Capital: JPY {summary['final_capital']:,.0f}\n")
        f.write(f"  Strategy Gain: {summary['capital_gain_rate']:+.2f}%\n")
        f.write(f"  Buy-and-Hold Gain: {summary['buy_and_hold_gain_rate']:+.2f}%\n")
        f.write(f"  Strategy Advantage: {summary['strategy_advantage']:+.2f}%\n\n")
        f.write(f"Price Movement:\n")
        f.write(f"  Start Price: JPY {summary['start_price']:,.2f}\n")
        f.write(f"  End Price: JPY {summary['end_price']:,.2f}\n\n")
        f.write(f"Trading Activity:\n")
        f.write(f"  Total Trades: {summary['total_trades']}\n")
        f.write(f"  Buy Orders: {summary['buy_trades']}\n")
        f.write(f"  Sell Orders: {summary['sell_trades']}\n")

    # Save trades to CSV file (data only, no comments)
    trades_df.to_csv(csv_path, index=False, encoding='utf-8')

    print(f"Results saved to:")
    print(f"  Summary: {txt_path}")
    print(f"  Trades:  {csv_path}")


if __name__ == '__main__':
    main()
