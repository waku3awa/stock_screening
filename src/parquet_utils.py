# -*- coding: utf-8 -*-
"""Parquet Utilities for Stock Data Management

This module provides utility functions for working with parquet files
in the context of stock data management, specifically for incremental updates.
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
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


def validate_parquet_data(file_path: str) -> Dict[str, any]:
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