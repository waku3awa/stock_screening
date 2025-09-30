# -*- coding: utf-8 -*-
"""Incremental Load yFinance

Enhanced version of load_yfinance.py with incremental update capabilities.
This script efficiently updates existing stock data by downloading only new data
since the last update, reducing network requests and processing time.

Key Features:
- Checks existing parquet files for latest date
- Downloads only missing data from that date to current
- Handles edge cases: corrupted files, delisted tickers, market gaps
- Maintains compatibility with existing batch processing workflow
"""

import yfinance_cache as yfc
import pandas as pd
import os
import time
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm
import logging
from typing import Optional
from utils_parquet import calculate_update_priority
from random import uniform
import warnings
warnings.filterwarnings('ignore')


# カスタムロガーを作成(__name__だとスクリプト名取得できなかった)
logger = logging.getLogger('incremental_load_yfinance')
logger.setLevel(logging.DEBUG) # 必要に応じてレベルを設定

# フォーマッターを作成
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# ファイルハンドラーを作成
# ログファイルが存在しない場合は作成されます
log_file_path = 'custom_incremental_update.log'
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG) # ファイルハンドラーのレベルを設定
file_handler.setFormatter(formatter)

# ストリームハンドラーを作成 (コンソール出力用)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG) # ストリームハンドラーのレベルを設定
stream_handler.setFormatter(formatter)

# ハンドラーをカスタムロガーに追加
# 同じハンドラーが複数回追加されないようにチェックすることもできます
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def test_logger():
    print(logger.level) # 現在のレベルを確認
    logger.info("test print.")


class IncrementalYFinanceLoader:
    """
    Handles incremental loading of stock data from yFinance.

    This class provides methods to:
    1. Check existing parquet files for their latest date
    2. Download only missing data since the last update
    3. Append new data to existing files efficiently
    4. Handle various edge cases and errors
    """

    def __init__(self, input_dir: str, excel_path: str, output_dir: Optional[str] = None, rate_limit_delay: float = 1.0):
        """
        Initialize the incremental loader.

        Args:
            input_dir: Directory to read existing parquet files from
            excel_path: Path to Excel file containing ticker list
            output_dir: Directory to save new/updated parquet files. If None, defaults to input_dir
            rate_limit_delay: Delay between yFinance requests (seconds)
        """
        self.input_dir = input_dir
        self.output_dir = output_dir if output_dir is not None else input_dir
        self.input_raw_dir = os.path.join(self.input_dir, 'raw')
        self.output_raw_dir = os.path.join(self.output_dir, 'raw')
        self.excel_path = excel_path
        self.rate_limit_delay = rate_limit_delay

        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.output_raw_dir, exist_ok=True)

        # Setup session for yfinance
        try:
            from curl_cffi import requests
            self.session = requests.Session(impersonate="safari15_5")
        except ImportError:
            logger.warning("curl_cffi not available, using default session")
            self.session = None

    def _get_latest_date_from_parquet(self, ticker: str) -> Optional[pd.Timestamp]:
        """
        Get the latest date from an existing parquet file.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Latest date in the file, or None if file doesn't exist or is corrupted
        """
        parquet_path = os.path.join(self.input_raw_dir, f"{ticker}_OHLCV.parquet")

        if not os.path.exists(parquet_path):
            return None

        try:
            # Read only the Date column for efficiency
            df_dates = pd.read_parquet(parquet_path, columns=['Date'])
            if df_dates.empty:
                logger.warning(f"Empty parquet file for {ticker}")
                return None

            latest_date = df_dates['Date'].max()
            logger.debug(f"Latest date for {ticker}: {latest_date}")
            return pd.to_datetime(latest_date)

        except Exception as e:
            logger.error(f"Error reading parquet file for {ticker}: {e}")
            # Move corrupted file to backup and treat as new ticker
            backup_path = parquet_path + ".corrupted"
            try:
                os.rename(parquet_path, backup_path)
                logger.info(f"Moved corrupted file to {backup_path}")
            except Exception as move_error:
                logger.error(f"Failed to move corrupted file: {move_error}")
            return None

    def _download_incremental_data(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Download stock data from yFinance for the specified date range.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data download
            end_date: End date for data download

        Returns:
            DataFrame with stock data, or None if download failed
        """
        try:
            logger.debug(f"Downloading {ticker} from {start_date} to {end_date}")

            df = yfc.download(
                ticker,
                start=start_date,
                end=end_date,
                adjust_splits=False,
                adjust_divs=False,
                session=self.session,
                threads=False
            )
        except Exception as e:
            logger.error(f"Error downloading data for {ticker}: {e}")
            return None

        else:
            if isinstance(df, pd.DataFrame):
                if df.empty:
                    logger.warning(f"No data returned for {ticker} ({start_date} to {end_date})")
                    return None

                # Process the downloaded data
                df.reset_index(inplace=True)

                # Handle multi-level columns that sometimes occur with yfinance
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

                # Ensure proper data types
                df = df.astype({
                    "Open": "float64",
                    "High": "float64",
                    "Low": "float64",
                    "Close": "float64",
                    "Adj Close": "float64",
                    "Volume": "int64"
                })

                df["Date"] = pd.to_datetime(df["Date"])
                df["Ticker"] = ticker

                logger.debug(f"Successfully downloaded {len(df)} records for {ticker}")
                return df
            else:
                print("yfc.downloadの戻り値は DataFrame ではありません:", type(df))


    def _merge_and_save_data(self, ticker: str, new_data: pd.DataFrame, industry_code: int) -> bool:
        """
        Merge new data with existing data and save to parquet file.

        Args:
            ticker: Stock ticker symbol
            new_data: New data to append
            industry_code: Industry code for the ticker

        Returns:
            True if successful, False otherwise
        """
        input_parquet_path = os.path.join(self.input_raw_dir, f"{ticker}_OHLCV.parquet")
        output_parquet_path = os.path.join(self.output_raw_dir, f"{ticker}_OHLCV.parquet")

        try:
            # Add industry code to new data
            new_data["IndustryCode"] = int(industry_code)

            if os.path.exists(input_parquet_path):
                # Read existing data from input directory
                existing_data = pd.read_parquet(input_parquet_path)

                # Combine old and new data
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)

                # Remove duplicates (keep last occurrence) and sort by date
                combined_data.drop_duplicates(subset=['Date'], keep='last', inplace=True)
                combined_data.sort_values(by='Date', inplace=True)

                logger.debug(f"Combined {len(existing_data)} existing + {len(new_data)} new = {len(combined_data)} total records for {ticker}")
            else:
                combined_data = new_data
                logger.debug(f"Creating new file with {len(new_data)} records for {ticker}")

            # Save to output directory
            combined_data.to_parquet(output_parquet_path, index=False)
            return True

        except Exception as e:
            logger.error(f"Error merging and saving data for {ticker}: {e}")
            return False

    def _load_ticker_list(self) -> pd.DataFrame:
        """
        Load the ticker list from Excel file.

        Returns:
            DataFrame with ticker information
        """
        try:
            df_all = pd.read_excel(self.excel_path)
            df_all = df_all[df_all["市場・商品区分"] == "プライム（内国株式）"]
            df_all["Ticker"] = df_all["コード"].astype(str).str.zfill(4) + ".T"
            df_list = df_all[["Ticker", "33業種コード"]].copy()

            logger.info(f"Loaded {len(df_list)} tickers from {self.excel_path}")
            return df_list

        except Exception as e:
            logger.error(f"Error loading ticker list: {e}")
            raise


    def dry_run_incremental_update(self):
        """Dry run of incremental update (shows what would be updated and estimate update time)"""

        logger.info("Dry run of incremental update")

        # This is a simulation - we'll check what would be updated without actually updating
        priorities = calculate_update_priority(self.input_raw_dir, max_age_days=1)

        updates_needed = [p for p in priorities if p['priority'] in ['HIGH', 'MEDIUM']]

        logger.info(f"Dry Run Results:")
        logger.info(f"  Total files that would be updated: {len(updates_needed)}")

        if updates_needed:
            logger.info(f"  Files to update:")
            for item in updates_needed[:10]:  # Show first 10
                logger.info(f"    {item['ticker']}: {item['reason']}")

            if len(updates_needed) > 10:
                logger.info(f"    ... and {len(updates_needed) - 10} more files")

            # Estimate time
            estimated_time = len(updates_needed) * (self.rate_limit_delay + 2)  # 2 seconds for processing
            logger.info(f"  Estimated update time: {estimated_time:.0f} seconds ({estimated_time/60:.1f} minutes)")
        else:
            logger.info("  All files are up to date!")


    def process_incremental_updates(self, max_lookback_days: int = 30) -> dict:
        """
        Process incremental updates for all tickers.

        Args:
            max_lookback_days: Maximum days to look back for updates

        Returns:
            Dictionary with update statistics
        """
        df_list = self._load_ticker_list()

        # Calculate end date (today)
        end_date = datetime.now().strftime('%Y-%m-%d')

        # Statistics tracking
        stats = {
            'total_tickers': len(df_list),
            'updated_tickers': 0,
            'new_tickers': 0,
            'failed_tickers': 0,
            'skipped_tickers': 0,
            'failed_list': []
        }

        logger.info(f"Starting incremental update for {stats['total_tickers']} tickers")

        for _, row in tqdm(df_list.iterrows(), total=len(df_list), desc="Processing tickers"):
            ticker = row["Ticker"]
            industry_code = row["33業種コード"]

            try:
                # Get latest date from existing file
                latest_date = self._get_latest_date_from_parquet(ticker)

                if latest_date is None:
                    # New ticker - download full history
                    start_date = "2010-01-01"
                    stats['new_tickers'] += 1
                    logger.info(f"New ticker {ticker}: downloading full history from {start_date}")
                else:
                    # Existing ticker - calculate start date for incremental update
                    next_date = latest_date + timedelta(days=1)
                    start_date = next_date.strftime('%Y-%m-%d')

                    # Skip if we're already up to date
                    if next_date.date() >= datetime.now().date():
                        logger.debug(f"Ticker {ticker} is already up to date (latest: {latest_date.date()})")
                        stats['skipped_tickers'] += 1
                        continue

                    # Skip if the gap is too large (might indicate delisted ticker)
                    days_behind = (datetime.now() - latest_date).days
                    if days_behind > max_lookback_days:
                        logger.warning(f"Ticker {ticker} is {days_behind} days behind (max: {max_lookback_days}), skipping")
                        stats['skipped_tickers'] += 1
                        continue

                    logger.debug(f"Updating ticker {ticker}: from {start_date} to {end_date}")

                # Download new data
                new_data = self._download_incremental_data(ticker, start_date, end_date)

                if new_data is None or new_data.empty:
                    logger.warning(f"No new data for {ticker}")
                    continue

                # Merge and save
                if self._merge_and_save_data(ticker, new_data, industry_code):
                    stats['updated_tickers'] += 1
                    logger.info(f"Successfully updated {ticker} with {len(new_data)} new records")
                else:
                    stats['failed_tickers'] += 1
                    stats['failed_list'].append(ticker)

                # Rate limiting
                time.sleep(self.rate_limit_delay + uniform(0,0.5))

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                stats['failed_tickers'] += 1
                stats['failed_list'].append(ticker)

        # Log final statistics
        logger.info(f"""
        Incremental Update Complete:
        - Total tickers processed: {stats['total_tickers']}
        - Updated tickers: {stats['updated_tickers']}
        - New tickers: {stats['new_tickers']}
        - Skipped tickers: {stats['skipped_tickers']}
        - Failed tickers: {stats['failed_tickers']}
        """)

        if stats['failed_list']:
            logger.warning(f"Failed tickers: {stats['failed_list']}")

        return stats

    def rebuild_batches_and_master(self, batch_size: int = 200):
        """
        Rebuild batch files and master file after incremental updates.

        Args:
            batch_size: Number of files per batch
        """
        logger.info("Rebuilding batches and master file...")

        # Setup batch directory
        batch_dir = os.path.join(self.output_dir, "batch_size")
        os.makedirs(batch_dir, exist_ok=True)

        # Clean up old batch files
        for f in os.listdir(batch_dir):
            if f.startswith("batch_") and f.endswith(".parquet"):
                os.remove(os.path.join(batch_dir, f))

        # Get all parquet files
        parquet_files = sorted([
            f for f in os.listdir(self.output_raw_dir)
            if f.endswith(".parquet") and not f.startswith("batch_")
        ])

        logger.info(f"Processing {len(parquet_files)} parquet files into batches of {batch_size}")

        # Process batches
        batch_count = 0
        for i in tqdm(range(0, len(parquet_files), batch_size), desc="Creating batches"):
            batch_files = parquet_files[i:i + batch_size]
            dfs = []

            for file in batch_files:
                try:
                    df = pd.read_parquet(os.path.join(self.output_raw_dir, file))
                    if not df.empty:
                        dfs.append(df)
                except Exception as e:
                    logger.error(f"Error reading {file}: {e}")

            if dfs:
                df_batch = pd.concat(dfs, ignore_index=True)
                batch_path = os.path.join(batch_dir, f"batch_{batch_count}.parquet")
                df_batch.to_parquet(batch_path, index=False)
                batch_count += 1
                logger.debug(f"Created batch_{batch_count-1} with {len(df_batch)} records")

        # Combine all batches into master file
        logger.info("Combining batches into master file...")
        batch_files = sorted([f for f in os.listdir(batch_dir) if f.endswith(".parquet")])

        df_list = []
        for file in tqdm(batch_files, desc="Combining batches"):
            path = os.path.join(batch_dir, file)
            df = pd.read_parquet(path)
            df_list.append(df)

        if df_list:
            df_combined = pd.concat(df_list, ignore_index=True)
            output_parquet = os.path.join(self.output_dir, "ticker_combined_OHLCV.parquet")
            df_combined.to_parquet(output_parquet, index=False)
            logger.info(f"Master file created: {output_parquet} with {len(df_combined)} records")
        else:
            logger.warning("No batch files found to combine")


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Incremental Stock Data Loader using yfinance API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with required arguments
  python incremental_load_yfinance.py --excel-path ./data/data_j_with_financials.xlsx --output-dir ./stock_data

  # With custom settings
  python incremental_load_yfinance.py -e ./data/data_j_with_financials.xlsx -o ./stock_data -i ./existing_data --delay 2.0 --lookback 60

  # Dry run to estimate update time
  python incremental_load_yfinance.py -e ./data/data_j_with_financials.xlsx -o ./stock_data --dry-run
        """
    )

    # Required arguments
    parser.add_argument(
        '-e', '--excel-path',
        required=True,
        type=str,
        help='Path to Excel file containing ticker list (required)'
    )

    parser.add_argument(
        '-o', '--output-dir',
        required=True,
        type=str,
        help='Directory to save stock data files (required)'
    )

    # Optional arguments
    parser.add_argument(
        '-i', '--input-dir',
        type=str,
        default=None,
        help='Directory to read existing stock data from (default: same as output-dir)'
    )

    from .config import RATE_LIMIT_DELAY, MAX_LOOKBACK_DAYS, BATCH_SIZE, EXCEL_PATH

    parser.add_argument(
        '--delay',
        type=float,
        default=RATE_LIMIT_DELAY,
        help='Delay between yfinance requests in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--lookback',
        type=int,
        default=MAX_LOOKBACK_DAYS,
        help='Maximum days to look back for updates (default: 30)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help='Number of files per batch when rebuilding (default: 200)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run to estimate update time without actually downloading data'
    )

    parser.add_argument(
        '--no-rebuild',
        action='store_true',
        help='Skip rebuilding batch and master files after updates'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )

    return parser.parse_args()


def main():
    """
    Main function to run incremental updates.
    """
    # Parse command line arguments
    args = parse_arguments()

    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))

    # Validate paths
    if not os.path.exists(args.excel_path):
        logger.error(f"Excel file not found: {args.excel_path}")
        return 1

    # Set input directory (default to output directory if not specified)
    input_dir = args.input_dir if args.input_dir else args.output_dir

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    logger.info(f"Configuration:")
    logger.info(f"  Excel file: {args.excel_path}")
    logger.info(f"  Input directory: {input_dir}")
    logger.info(f"  Output directory: {args.output_dir}")
    logger.info(f"  Rate limit delay: {args.delay}s")
    logger.info(f"  Max lookback days: {args.lookback}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Dry run: {args.dry_run}")

    try:
        # Create loader instance
        loader = IncrementalYFinanceLoader(
            input_dir=input_dir,
            excel_path=args.excel_path,
            output_dir=args.output_dir,
            rate_limit_delay=args.delay
        )

        if args.dry_run:
            # Perform dry run only
            logger.info("Performing dry run...")
            loader.dry_run_incremental_update()
            logger.info("Dry run complete!")
            return 0

        # Process incremental updates
        logger.info("Starting incremental updates...")
        stats = loader.process_incremental_updates(max_lookback_days=args.lookback)

        # Rebuild batches and master file if any updates were made and not disabled
        if not args.no_rebuild and (stats['updated_tickers'] > 0 or stats['new_tickers'] > 0):
            logger.info("Rebuilding batch and master files...")
            loader.rebuild_batches_and_master(batch_size=args.batch_size)
        elif args.no_rebuild:
            logger.info("Batch rebuild skipped (--no-rebuild flag)")
        else:
            logger.info("No updates were made, skipping batch rebuild")

        logger.info("Incremental update process complete!")

        # Print final summary
        logger.info(f"""
Final Summary:
- Total tickers: {stats['total_tickers']}
- Updated: {stats['updated_tickers']}
- New: {stats['new_tickers']}
- Skipped: {stats['skipped_tickers']}
- Failed: {stats['failed_tickers']}
        """)

        return 0

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        return 1


def incremental_yf_update(
    input_dir="/content/drive/MyDrive/stock_prediction/external_sources/yf_data",
    excel_path="/content/drive/MyDrive/stock_prediction/ver.1/results/1st/data_j_with_financials.xlsx",
    max_lookback_days=30,
    output_dir=None):
    """Update all ticker"""
    print("\n" + "="*60)
    print("Update all ticker")
    print("="*60)

    # Example code (commented out to avoid actual execution)
    loader = IncrementalYFinanceLoader(
        input_dir=input_dir,
        excel_path=excel_path,
        output_dir=output_dir,
        rate_limit_delay=1.5
    )

    print(f"Estimate time")
    loader.dry_run_incremental_update()

    # This would update all tickers that need updates
    stats = loader.process_incremental_updates(max_lookback_days=max_lookback_days)

    print(f"Incremental download complete: {stats}")

    # Rebuild batches and master file if any updates were made
    if stats['updated_tickers'] > 0 or stats['new_tickers'] > 0:
        loader.rebuild_batches_and_master()
    else:
        print("No updates were made, skipping batch rebuild")

    print("Rebuild_batches_and_master Process complete!")


if __name__ == "__main__":
    import sys
    sys.exit(main())