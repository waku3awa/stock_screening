# -*- coding: utf-8 -*-
"""Bargain Strategy - Python Implementation

Converted from PineScript (src_poc/bargain_storategy.pine).
Implements a long/short strategy based on price movements relative to 200-day moving average.

Strategy Logic:
- Buy Signal: Price drops X% over 2 bars while below 200-day MA
- Sell Signal: Price rises Y% over 2 bars while above 200-day MA
- Position Sizing: Annual budget with per-trade purchase limits
- Period: Simulates one year from specified start date
"""

import argparse
import yfinance_cache as yfc
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def calculate_bargain_signals(df: pd.DataFrame,
                               drop_percentage: float = 3.0,
                               rise_percentage: float = 5.0,
                               ma_period: int = 200) -> pd.DataFrame:
    """
    Calculate bargain hunting strategy signals.

    Args:
        df: DataFrame with OHLCV data
        drop_percentage: % drop threshold for buy signal
        rise_percentage: % rise threshold for sell signal
        ma_period: Moving average period

    Returns:
        DataFrame with signals and indicators
    """
    df_result = df.copy()

    # Calculate 200-day moving average
    df_result['MA200'] = df_result['Close'].rolling(window=ma_period, min_periods=ma_period).mean()

    # Valuation flags
    df_result['overvalued'] = df_result['Close'] > df_result['MA200']
    df_result['undervalued'] = df_result['Close'] < df_result['MA200']

    # Past price data (shifted)
    close_t0 = df_result['Close']
    close_t1 = df_result['Close'].shift(1)
    close_t2 = df_result['Close'].shift(2)

    # MA must be valid (not NaN) for signals
    ma_valid = df_result['MA200'].notna()

    # Buy condition:
    # - MA200 is valid
    # - Not overvalued (close <= MA200) - explicitly check to avoid NaN issues
    # - Downward trend started 2 bars ago (close[2] > close[1])
    # - Drop rate >= threshold over 2 bars
    # - Protect against zero division
    down_trend_start = close_t2 > close_t1

    # Calculate drop rate with zero-division protection
    drop_rate = pd.Series(0.0, index=df_result.index)
    valid_c2 = (close_t2.notna()) & (close_t2 != 0)
    drop_rate[valid_c2] = ((close_t2[valid_c2] - close_t0[valid_c2]) / close_t2[valid_c2]) * 100

    buy_condition = (
        ma_valid &
        (close_t0 <= df_result['MA200']) &
        down_trend_start &
        (drop_rate >= drop_percentage)
    )

    # Sell condition:
    # - MA200 is valid
    # - Not undervalued (close >= MA200) - explicitly check to avoid NaN issues
    # - Upward trend started 2 bars ago (close[2] < close[1])
    # - Rise rate >= threshold over 2 bars
    # - Protect against zero division
    up_trend_start = close_t2 < close_t1

    # Calculate rise rate with zero-division protection
    rise_rate = pd.Series(0.0, index=df_result.index)
    rise_rate[valid_c2] = ((close_t0[valid_c2] - close_t2[valid_c2]) / close_t2[valid_c2]) * 100

    sell_condition = (
        ma_valid &
        (close_t0 >= df_result['MA200']) &
        up_trend_start &
        (rise_rate >= rise_percentage)
    )

    # Add signal column: 1=buy, -1=sell, 0=hold
    df_result['signal'] = 0
    df_result.loc[buy_condition, 'signal'] = 1
    df_result.loc[sell_condition, 'signal'] = -1

    # Store rates for analysis
    df_result['drop_rate'] = drop_rate
    df_result['rise_rate'] = rise_rate

    return df_result


def simulate_strategy(df: pd.DataFrame,
                      annual_budget: float,
                      purchase_limit: float,
                      start_date: datetime,
                      end_date: datetime) -> tuple[pd.DataFrame, dict]:
    """
    Simulate the bargain strategy with budget management.

    Args:
        df: DataFrame with signals
        annual_budget: Total budget for the year
        purchase_limit: Maximum purchase per trade
        start_date: Simulation start date
        end_date: Simulation end date

    Returns:
        (trades_df, summary_dict)
    """
    # Convert dates to timezone-aware if df index is timezone-aware
    if df.index.tzinfo is not None:
        # Make start_date and end_date timezone-aware (UTC)
        start_date = pytz.UTC.localize(start_date) if start_date.tzinfo is None else start_date
        end_date = pytz.UTC.localize(end_date) if end_date.tzinfo is None else end_date

    # Filter data to simulation period
    df_sim = df.loc[start_date:end_date].copy()

    if df_sim.empty:
        return pd.DataFrame(), {
            'error': 'No data in specified period',
            'start_date': start_date,
            'end_date': end_date
        }

    # Initialize tracking variables
    remaining_budget = annual_budget
    position_shares = 0
    total_cost = 0.0  # Track total cost for average entry price calculation
    trades = []

    # Get start price for buy-and-hold comparison
    start_price = df_sim.iloc[0]['Close']

    for idx, row in df_sim.iterrows():
        date = idx
        close_price = row['Close']
        signal = row['signal']

        # Buy signal - Allow pyramiding (multiple entries)
        # NOTE: Original PineScript allows pyramiding=1000, so we allow multiple buys
        if signal == 1 and remaining_budget > 0:
            max_dollars = min(purchase_limit, remaining_budget)
            shares = int(max_dollars // close_price)

            if shares > 0:
                cost = shares * close_price
                position_shares += shares  # Add to existing position
                total_cost += cost
                remaining_budget -= cost

                trades.append({
                    'date': date,
                    'action': 'BUY',
                    'price': close_price,
                    'shares': shares,
                    'amount': cost,
                    'position_shares': position_shares,
                    'remaining_budget': remaining_budget
                })

        # Sell signal - Close ALL positions (matching PineScript strategy.close behavior)
        elif signal == -1 and position_shares > 0:
            proceeds = position_shares * close_price
            remaining_budget += proceeds

            # Calculate return based on average entry price
            avg_entry_price = total_cost / position_shares if position_shares > 0 else 0
            trade_return = ((close_price - avg_entry_price) / avg_entry_price) * 100 if avg_entry_price > 0 else 0

            trades.append({
                'date': date,
                'action': 'SELL',
                'price': close_price,
                'shares': position_shares,
                'amount': proceeds,
                'position_shares': 0,
                'remaining_budget': remaining_budget,
                'avg_entry_price': avg_entry_price,
                'return_pct': trade_return
            })

            position_shares = 0
            total_cost = 0.0

    # Final position close at end date
    if position_shares > 0:
        end_price = df_sim.iloc[-1]['Close']
        proceeds = position_shares * end_price
        remaining_budget += proceeds

        avg_entry_price = total_cost / position_shares if position_shares > 0 else 0
        trade_return = ((end_price - avg_entry_price) / avg_entry_price) * 100 if avg_entry_price > 0 else 0

        trades.append({
            'date': df_sim.index[-1],
            'action': 'FINAL_CLOSE',
            'price': end_price,
            'shares': position_shares,
            'amount': proceeds,
            'position_shares': 0,
            'remaining_budget': remaining_budget,
            'avg_entry_price': avg_entry_price,
            'return_pct': trade_return
        })

    trades_df = pd.DataFrame(trades)

    # Calculate summary statistics
    final_capital = remaining_budget
    capital_gain_rate = ((final_capital - annual_budget) / annual_budget) * 100

    # Buy-and-hold comparison
    end_price = df_sim.iloc[-1]['Close']
    single_buy_gain_rate = ((end_price - start_price) / start_price) * 100

    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'annual_budget': annual_budget,
        'final_capital': final_capital,
        'capital_gain_rate': capital_gain_rate,
        'buy_and_hold_gain_rate': single_buy_gain_rate,
        'strategy_advantage': capital_gain_rate - single_buy_gain_rate,
        'start_price': start_price,
        'end_price': end_price,
        'total_trades': len(trades_df),
        'buy_trades': len(trades_df[trades_df['action'] == 'BUY']),
        'sell_trades': len(trades_df[trades_df['action'] == 'SELL'])
    }

    return trades_df, summary


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

    # Calculate signals
    print("Calculating signals...")
    df_signals = calculate_bargain_signals(
        df,
        drop_percentage=args.drop,
        rise_percentage=args.rise,
        ma_period=args.ma_period
    )

    # Run simulation
    print("Running simulation...")
    trades_df, summary = simulate_strategy(
        df_signals,
        annual_budget=args.annual_budget,
        purchase_limit=args.purchase_limit,
        start_date=start_date,
        end_date=end_date
    )

    if 'error' in summary:
        print(f"ERROR: {summary['error']}")
        return

    # Print results to stdout
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
