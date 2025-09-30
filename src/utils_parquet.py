# -*- coding: utf-8 -*-
"""Parquet Utilities for Stock Data Management

This module provides utility functions for working with parquet files
in the context of stock data management, specifically for incremental updates.
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Union, Any
import logging

logger = logging.getLogger(__name__)


def get_latest_date_from_parquet(file_path: str) -> Optional[pd.Timestamp]:
    """
    Efficiently get the latest date from a parquet file.

    This function reads only the Date column to minimize memory usage,
    making it very efficient for large files.

    Args:
        file_path: Path to the parquet file

    Returns:
        Latest date in the file, or None if file doesn't exist or is empty

    Example:
        >>> latest_date = get_latest_date_from_parquet('AAPL_OHLCV.parquet')
        >>> print(latest_date)
        2025-06-27 00:00:00
    """
    if not os.path.exists(file_path):
        return None

    try:
        # Read only the Date column for maximum efficiency
        df_dates = pd.read_parquet(file_path, columns=['Date'])

        if df_dates.empty:
            logger.warning(f"Empty parquet file: {file_path}")
            return None

        latest_date = df_dates['Date'].max()
        return pd.to_datetime(latest_date)

    except Exception as e:
        logger.error(f"Error reading parquet file {file_path}: {e}")
        return None


def get_date_range_from_parquet(file_path: str) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Get the date range (min and max dates) from a parquet file.

    Args:
        file_path: Path to the parquet file

    Returns:
        Tuple of (min_date, max_date) or None if file doesn't exist

    Example:
        >>> date_range = get_date_range_from_parquet('AAPL_OHLCV.parquet')
        >>> print(f"Data from {date_range[0]} to {date_range[1]}")
        Data from 2010-01-01 00:00:00 to 2025-06-27 00:00:00
    """
    if not os.path.exists(file_path):
        return None

    try:
        df_dates = pd.read_parquet(file_path, columns=['Date'])

        if df_dates.empty:
            return None

        min_date = df_dates['Date'].min()
        max_date = df_dates['Date'].max()

        return pd.to_datetime(min_date), pd.to_datetime(max_date)

    except Exception as e:
        logger.error(f"Error reading parquet file {file_path}: {e}")
        return None


def validate_parquet_data(file_path: str) -> Dict[str, Any]:
    """
    Validate a parquet file and return diagnostic information.

    Args:
        file_path: Path to the parquet file

    Returns:
        Dictionary with validation results

    Example:
        >>> validation = validate_parquet_data('AAPL_OHLCV.parquet')
        >>> print(validation)
        {
            'is_valid': True,
            'row_count': 3825,
            'column_count': 9,
            'date_range': ('2010-01-01', '2025-06-27'),
            'missing_values': 0,
            'duplicate_dates': 0,
            'data_quality_issues': []
        }
    """
    result = {
        'is_valid': False,
        'row_count': 0,
        'column_count': 0,
        'date_range': None,
        'missing_values': 0,
        'duplicate_dates': 0,
        'data_quality_issues': []
    }

    if not os.path.exists(file_path):
        result['data_quality_issues'].append(f"File does not exist: {file_path}")
        return result

    try:
        df = pd.read_parquet(file_path)

        result['row_count'] = len(df)
        result['column_count'] = len(df.columns)

        if df.empty:
            result['data_quality_issues'].append("File is empty")
            return result

        # Check for required columns
        from .config import REQUIRED_COLUMNS
        required_columns = REQUIRED_COLUMNS
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            result['data_quality_issues'].append(f"Missing required columns: {missing_columns}")

        # Check date range
        if 'Date' in df.columns:
            date_range = get_date_range_from_parquet(file_path)
            if date_range:
                result['date_range'] = (date_range[0].strftime('%Y-%m-%d'),
                                      date_range[1].strftime('%Y-%m-%d'))

            # Check for duplicate dates
            duplicate_dates = df['Date'].duplicated().sum()
            result['duplicate_dates'] = duplicate_dates
            if duplicate_dates > 0:
                result['data_quality_issues'].append(f"Found {duplicate_dates} duplicate dates")

        # Check for missing values
        missing_values = df.isnull().sum().sum()
        result['missing_values'] = missing_values
        if missing_values > 0:
            result['data_quality_issues'].append(f"Found {missing_values} missing values")

        # Check for reasonable price values
        if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            negative_prices = ((df['Open'] <= 0) | (df['High'] <= 0) |
                             (df['Low'] <= 0) | (df['Close'] <= 0)).sum()
            if negative_prices > 0:
                result['data_quality_issues'].append(f"Found {negative_prices} rows with non-positive prices")

            # Check for logical price relationships
            illogical_prices = (df['High'] < df['Low']).sum()
            if illogical_prices > 0:
                result['data_quality_issues'].append(f"Found {illogical_prices} rows where High < Low")

        # If no issues found, mark as valid
        result['is_valid'] = len(result['data_quality_issues']) == 0

    except Exception as e:
        result['data_quality_issues'].append(f"Error reading file: {str(e)}")

    return result


def append_to_parquet(file_path: str, new_data: pd.DataFrame,
                     remove_duplicates: bool = True) -> bool:
    """
    Efficiently append new data to an existing parquet file.

    Args:
        file_path: Path to the parquet file
        new_data: DataFrame with new data to append
        remove_duplicates: Whether to remove duplicate dates

    Returns:
        True if successful, False otherwise

    Example:
        >>> new_data = pd.DataFrame({
        ...     'Date': ['2025-06-28', '2025-06-29'],
        ...     'Open': [150.0, 151.0],
        ...     'High': [152.0, 153.0],
        ...     'Low': [149.0, 150.0],
        ...     'Close': [151.0, 152.0],
        ...     'Volume': [1000000, 1100000],
        ...     'Ticker': ['AAPL', 'AAPL']
        ... })
        >>> success = append_to_parquet('AAPL_OHLCV.parquet', new_data)
        >>> print(f"Append successful: {success}")
        Append successful: True
    """
    try:
        if os.path.exists(file_path):
            # Read existing data
            existing_data = pd.read_parquet(file_path)

            # Combine old and new data
            combined_data = pd.concat([existing_data, new_data], ignore_index=True)

            if remove_duplicates and 'Date' in combined_data.columns:
                # Remove duplicates, keeping the last occurrence
                combined_data.drop_duplicates(subset=['Date'], keep='last', inplace=True)
                combined_data.sort_values(by='Date', inplace=True)

            logger.info(f"Appended {len(new_data)} rows to {file_path} "
                       f"(total: {len(combined_data)} rows)")
        else:
            combined_data = new_data
            logger.info(f"Created new file {file_path} with {len(new_data)} rows")

        # Save the combined data
        combined_data.to_parquet(file_path, index=False)
        return True

    except Exception as e:
        logger.error(f"Error appending to parquet file {file_path}: {e}")
        return False


def get_missing_date_ranges(file_path: str, expected_start: str,
                           expected_end: str) -> List[Tuple[str, str]]:
    """
    Identify missing date ranges in a parquet file.

    Args:
        file_path: Path to the parquet file
        expected_start: Expected start date (YYYY-MM-DD format)
        expected_end: Expected end date (YYYY-MM-DD format)

    Returns:
        List of tuples representing missing date ranges

    Example:
        >>> missing_ranges = get_missing_date_ranges('AAPL_OHLCV.parquet',
        ...                                        '2010-01-01', '2025-06-27')
        >>> print(missing_ranges)
        [('2025-06-25', '2025-06-27')]
    """
    if not os.path.exists(file_path):
        return [(expected_start, expected_end)]

    try:
        df_dates = pd.read_parquet(file_path, columns=['Date'])

        if df_dates.empty:
            return [(expected_start, expected_end)]

        # Convert to datetime
        df_dates['Date'] = pd.to_datetime(df_dates['Date'])
        existing_dates = set(df_dates['Date'].dt.date)

        # Generate expected date range (business days only)
        expected_dates = pd.bdate_range(start=expected_start, end=expected_end)
        expected_dates_set = set(expected_dates.date)

        # Find missing dates
        missing_dates = sorted(expected_dates_set - existing_dates)

        if not missing_dates:
            return []

        # Group consecutive missing dates into ranges
        ranges = []
        start_date = missing_dates[0]
        prev_date = missing_dates[0]

        for date in missing_dates[1:]:
            if (date - prev_date).days > 1:
                # Gap found, close current range
                ranges.append((start_date.strftime('%Y-%m-%d'),
                              prev_date.strftime('%Y-%m-%d')))
                start_date = date
            prev_date = date

        # Add the last range
        ranges.append((start_date.strftime('%Y-%m-%d'),
                      prev_date.strftime('%Y-%m-%d')))

        return ranges

    except Exception as e:
        logger.error(f"Error analyzing missing dates in {file_path}: {e}")
        return [(expected_start, expected_end)]


def scan_all_parquet_files(directory: str) -> Dict[str, Dict]:
    """
    Scan all parquet files in a directory and return summary information.

    Args:
        directory: Directory containing parquet files

    Returns:
        Dictionary with file information

    Example:
        >>> summary = scan_all_parquet_files('/path/to/stock/data')
        >>> print(f"Found {len(summary)} files")
        >>> for ticker, info in summary.items():
        ...     print(f"{ticker}: {info['date_range']} ({info['row_count']} rows)")
    """
    summary = {}

    if not os.path.exists(directory):
        logger.error(f"Directory does not exist: {directory}")
        return summary

    parquet_files = [f for f in os.listdir(directory) if f.endswith('.parquet')]

    for file in parquet_files:
        file_path = os.path.join(directory, file)
        ticker = file.replace('_OHLCV.parquet', '')

        validation = validate_parquet_data(file_path)

        summary[ticker] = {
            'file_path': file_path,
            'is_valid': validation['is_valid'],
            'row_count': validation['row_count'],
            'date_range': validation['date_range'],
            'issues': validation['data_quality_issues']
        }

    return summary


def get_last_business_day(date: Optional[str] = None) -> str:
    """
    Get the last business day (Monday-Friday) on or before the specified date.
    
    This function is crucial for stock market data processing as markets are closed
    on weekends and some holidays. It ensures we always request data for a day
    when markets were potentially open.
    
    Args:
        date: Date string in 'YYYY-MM-DD' format. If None, uses today's date.
        
    Returns:
        String representing the last business day in 'YYYY-MM-DD' format
        
    Example:
        >>> # If today is Sunday 2024-01-07
        >>> get_last_business_day()
        '2024-01-05'  # Returns Friday
        
        >>> # If today is Wednesday 2024-01-03  
        >>> get_last_business_day()
        '2024-01-03'  # Returns same day (Wednesday)
    """
    if date is None:
        target_date = datetime.now()
    else:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    
    # Find the last business day (Monday=0, Sunday=6)
    while target_date.weekday() > 4:  # Saturday=5, Sunday=6
        target_date -= timedelta(days=1)
    
    return target_date.strftime('%Y-%m-%d')


def adjust_date_range_for_market(start_date: str, end_date: str) -> Tuple[str, str]:
    """
    Adjust date range to ensure both dates fall on potential trading days.
    
    This function adjusts both start and end dates to business days to avoid
    requesting data for weekends when markets are closed.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        Tuple of (adjusted_start_date, adjusted_end_date) in 'YYYY-MM-DD' format
        
    Example:
        >>> adjust_date_range_for_market('2024-01-06', '2024-01-07')  # Sat-Sun
        ('2024-01-05', '2024-01-05')  # Both adjusted to Friday
    """
    # Adjust end date to last business day
    adjusted_end = get_last_business_day(end_date)
    
    # For start date, if it's a weekend, move to next business day
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    while start_dt.weekday() > 4:  # Saturday=5, Sunday=6
        start_dt += timedelta(days=1)
    adjusted_start = start_dt.strftime('%Y-%m-%d')
    
    return adjusted_start, adjusted_end

def get_ticker_data(
    tickers: Union[str, List[str]],
    directory: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    auto_download: bool = False,
    excel_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Get stock data for specified tickers from parquet files.

    This function retrieves stock data for one or more tickers from parquet files
    in the specified directory. It can optionally download missing data if files
    don't exist or data is missing for the specified period.

    Args:
        tickers: Single ticker string or list of ticker symbols (e.g., '7203.T' or ['7203.T', '6758.T'])
        directory: Directory containing parquet files (typically 'raw' subdirectory)
        start_date: Start date in 'YYYY-MM-DD' format. If None, gets all available data
        end_date: End date in 'YYYY-MM-DD' format. If None, uses today's date
        auto_download: If True, automatically downloads missing data. If False, raises error for missing data
        excel_path: Path to Excel file with ticker list (required if auto_download=True)

    Returns:
        DataFrame containing combined stock data for all requested tickers

    Raises:
        FileNotFoundError: If ticker file doesn't exist and auto_download=False
        ValueError: If requested date range has no data and auto_download=False

    Example:
        >>> # Get single ticker data
        >>> df = get_ticker_data('7203.T', './stock_data/raw', '2024-01-01', '2024-12-31')

        >>> # Get multiple tickers with auto-download
        >>> df = get_ticker_data(['7203.T', '6758.T'], './stock_data/raw',
        ...                     start_date='2024-01-01', auto_download=True,
        ...                     excel_path='./data/data_j.xlsx')
    """
    # Convert single ticker to list for uniform processing
    if isinstance(tickers, str):
        tickers = [tickers]

    # Set default dates if not provided
    if end_date is None:
        end_date = get_last_business_day()  # Use last business day instead of today
    if start_date is None:
        start_date = '2010-01-01'  # Default historical start
    
    # Adjust date range for market hours to avoid weekend/holiday issues
    start_date, end_date = adjust_date_range_for_market(start_date, end_date)
    logger.info(f"Adjusted date range for market hours: {start_date} to {end_date}")

    # Convert dates to datetime objects for comparison
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    all_data = []
    missing_tickers = []
    incomplete_tickers = []

    for ticker in tickers:
        file_path = os.path.join(directory, f"{ticker}_OHLCV.parquet")

        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File not found for ticker {ticker}: {file_path}")
            missing_tickers.append(ticker)
            continue

        try:
            # Read the parquet file
            df = pd.read_parquet(file_path)

            if df.empty:
                logger.warning(f"Empty file for ticker {ticker}")
                missing_tickers.append(ticker)
                continue

            # Ensure Date column is datetime
            df['Date'] = pd.to_datetime(df['Date'])

            # Check data availability for requested period
            data_start = df['Date'].min()
            data_end = df['Date'].max()

            # Check if we have data for the requested period
            if data_end < start_dt or data_start > end_dt:
                logger.warning(f"No data for {ticker} in requested period {start_date} to {end_date}")
                logger.warning(f"Available data: {data_start.strftime('%Y-%m-%d')} to {data_end.strftime('%Y-%m-%d')}")
                incomplete_tickers.append({
                    'ticker': ticker,
                    'reason': 'no_overlap',
                    'available_range': (data_start, data_end)
                })
                continue

            # Check for missing data at the beginning or end
            needs_update = False
            update_start = None
            update_end = None

            if data_start > start_dt:
                logger.info(f"Data for {ticker} starts at {data_start.strftime('%Y-%m-%d')}, requested from {start_date}")
                needs_update = True
                update_start = start_date
                update_end = (data_start - timedelta(days=1)).strftime('%Y-%m-%d')

            if data_end < end_dt:
                logger.info(f"Data for {ticker} ends at {data_end.strftime('%Y-%m-%d')}, requested until {end_date}")
                needs_update = True
                if not update_start:
                    update_start = (data_end + timedelta(days=1)).strftime('%Y-%m-%d')
                    update_end = end_date

            if needs_update:
                incomplete_tickers.append({
                    'ticker': ticker,
                    'reason': 'partial_data',
                    'update_range': (update_start, update_end) if update_start else None
                })

            # Filter data for requested date range
            mask = (df['Date'] >= start_dt) & (df['Date'] <= end_dt)
            filtered_df = df[mask].copy()

            if not filtered_df.empty:
                all_data.append(filtered_df)
                logger.info(f"Retrieved {len(filtered_df)} records for {ticker}")
            else:
                logger.warning(f"No data for {ticker} after filtering for date range")

        except Exception as e:
            logger.error(f"Error reading data for {ticker}: {e}")
            missing_tickers.append(ticker)

    # Handle missing or incomplete data
    if missing_tickers or incomplete_tickers:
        if auto_download:
            logger.info("Auto-download enabled. Attempting to download missing data...")

            if not excel_path:
                raise ValueError("excel_path is required when auto_download=True")

            # Import incremental loader
            try:
                from .incremental_load_yfinance import IncrementalYFinanceLoader

                # Load ticker list from Excel
                df_excel = pd.read_excel(excel_path)
                df_excel = df_excel[df_excel["市場・商品区分"] == "プライム（内国株式）"]
                df_excel["Ticker"] = df_excel["コード"].astype(str).str.zfill(4) + ".T"
                ticker_list = df_excel[["Ticker", "33業種コード"]].copy()

                # Create loader instance
                loader = IncrementalYFinanceLoader(
                    input_dir=os.path.dirname(directory),
                    ticker_list=ticker_list,
                    output_dir=os.path.dirname(directory),
                    rate_limit_delay=1.0
                )

                # Download missing tickers
                for ticker in missing_tickers:
                    logger.info(f"Downloading full history for {ticker}")
                    try:
                        # Download data
                        new_data = loader._download_incremental_data(ticker, start_date, end_date)
                        if new_data is not None and not new_data.empty:
                            # Save to file
                            file_path = os.path.join(directory, f"{ticker}_OHLCV.parquet")
                            new_data.to_parquet(file_path, index=False)
                            all_data.append(new_data)
                            logger.info(f"Successfully downloaded and saved {len(new_data)} records for {ticker}")
                    except Exception as e:
                        logger.error(f"Failed to download data for {ticker}: {e}")

                # Update incomplete tickers
                for item in incomplete_tickers:
                    if item['reason'] == 'partial_data' and item.get('update_range'):
                        ticker = item['ticker']
                        update_start, update_end = item['update_range']
                        logger.info(f"Downloading missing data for {ticker} from {update_start} to {update_end}")

                        try:
                            new_data = loader._download_incremental_data(ticker, update_start, update_end)
                            if new_data is not None and not new_data.empty:
                                # Append to existing file
                                file_path = os.path.join(directory, f"{ticker}_OHLCV.parquet")
                                if append_to_parquet(file_path, new_data):
                                    # Re-read the updated file
                                    df = pd.read_parquet(file_path)
                                    df['Date'] = pd.to_datetime(df['Date'])
                                    mask = (df['Date'] >= start_dt) & (df['Date'] <= end_dt)
                                    filtered_df = df[mask].copy()

                                    # Replace old data with updated data
                                    all_data = [d for d in all_data if d['Ticker'].iloc[0] != ticker]
                                    all_data.append(filtered_df)
                                    logger.info(f"Successfully updated {ticker} with {len(new_data)} new records")
                        except Exception as e:
                            logger.error(f"Failed to update data for {ticker}: {e}")

            except ImportError as e:
                logger.error(f"Cannot import IncrementalYFinanceLoader: {e}")
                raise ValueError("Auto-download requested but incremental loader not available")

        else:
            # Raise error if auto_download is False
            error_msg = []
            if missing_tickers:
                error_msg.append(f"Missing files for tickers: {missing_tickers}")
            if incomplete_tickers:
                incomplete_info = [f"{item['ticker']} ({item['reason']})" for item in incomplete_tickers]
                error_msg.append(f"Incomplete data for tickers: {incomplete_info}")

            raise ValueError(f"Data issues found (set auto_download=True to fix): {'; '.join(error_msg)}")

    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df.sort_values(by=['Ticker', 'Date'], inplace=True)
        logger.info(f"Retrieved total of {len(combined_df)} records for {len(all_data)} tickers")
        return combined_df
    else:
        logger.warning("No data retrieved for any ticker")
        return pd.DataFrame()


def get_recent_ticker_data(
    tickers: Union[str, List[str]],
    directory: str,
    days: int = 365,
    auto_download: bool = False,
    excel_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Get recent stock data for specified tickers (convenience function).

    This is a convenience wrapper around get_ticker_data that automatically
    calculates the date range based on the number of days from today.

    Args:
        tickers: Single ticker string or list of ticker symbols
        directory: Directory containing parquet files
        days: Number of days of historical data to retrieve (default: 365)
        auto_download: If True, automatically downloads missing data
        excel_path: Path to Excel file with ticker list (required if auto_download=True)

    Returns:
        DataFrame containing recent stock data

    Example:
        >>> # Get last year of data for Toyota
        >>> df = get_recent_ticker_data('7203.T', './stock_data/raw', days=365)

        >>> # Get last 30 days for multiple tickers
        >>> df = get_recent_ticker_data(['7203.T', '6758.T'], './stock_data/raw', days=30)
    """
    end_date = get_last_business_day()  # Use last business day instead of today
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    return get_ticker_data(
        tickers=tickers,
        directory=directory,
        start_date=start_date,
        end_date=end_date,
        auto_download=auto_download,
        excel_path=excel_path
    )


def calculate_update_priority(directory: str, max_age_days: int = 7) -> List[Dict]:
    """
    Calculate which files need updates most urgently.

    Args:
        directory: Directory containing parquet files
        max_age_days: Maximum age in days before considering file stale

    Returns:
        List of dictionaries with update priority information

    Example:
        >>> priorities = calculate_update_priority('/path/to/stock/data')
        >>> for item in priorities[:5]:  # Show top 5 priorities
        ...     print(f"{item['ticker']}: {item['days_behind']} days behind")
    """
    priorities = []
    summary = scan_all_parquet_files(directory)
    current_date = datetime.now().date()

    for ticker, info in summary.items():
        if not info['is_valid'] or not info['date_range']:
            priorities.append({
                'ticker': ticker,
                'priority': 'HIGH',
                'reason': 'Invalid or missing data',
                'days_behind': 9999,
                'last_date': None
            })
            continue

        last_date = datetime.strptime(info['date_range'][1], '%Y-%m-%d').date()
        days_behind = (current_date - last_date).days

        if days_behind <= 1:
            priority = 'LOW'
        elif days_behind <= max_age_days:
            priority = 'MEDIUM'
        else:
            priority = 'HIGH'

        priorities.append({
            'ticker': ticker,
            'priority': priority,
            'reason': f'{days_behind} days behind',
            'days_behind': days_behind,
            'last_date': last_date.strftime('%Y-%m-%d')
        })

    # Sort by priority and days behind
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    priorities.sort(key=lambda x: (priority_order[x['priority']], x['days_behind']))

    return priorities


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test with a hypothetical file
    test_file = "/path/to/test_file.parquet"

    print("Parquet Utilities Example Usage:")
    print("=" * 50)

    # Example 1: Get latest date
    latest_date = get_latest_date_from_parquet(test_file)
    print(f"Latest date: {latest_date}")

    # Example 2: Validate data
    validation = validate_parquet_data(test_file)
    print(f"Validation result: {validation}")

    # Example 3: Scan directory
    summary = scan_all_parquet_files("/path/to/stock/data")
    print(f"Found {len(summary)} files")

    # Example 4: Get ticker data with various options
    print("\n" + "=" * 50)
    print("New Data Extraction Functions:")
    print("=" * 50)

    # Example 4a: Get single ticker data for specific period
    print("\n# Get Toyota (7203.T) data for 2024")
    print("df = get_ticker_data('7203.T', './stock_data/raw', '2024-01-01', '2024-12-31')")

    # Example 4b: Get multiple tickers with auto-download
    print("\n# Get multiple tickers with auto-download if missing")
    print("df = get_ticker_data(['7203.T', '6758.T'], './stock_data/raw',")
    print("                    start_date='2024-01-01', auto_download=True,")
    print("                    excel_path='./data/data_j.xlsx')")

    # Example 4c: Get recent data (last year)
    print("\n# Get last year of data for Toyota")
    print("df = get_recent_ticker_data('7203.T', './stock_data/raw', days=365)")

    # Example 4d: Get recent data for multiple tickers
    print("\n# Get last 30 days for multiple tickers")
    print("df = get_recent_ticker_data(['7203.T', '6758.T'], './stock_data/raw', days=30)")
