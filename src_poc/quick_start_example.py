#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick Start Example for Incremental yfinance Updates

This script demonstrates how to use the incremental update functionality
with practical examples and common use cases.
"""

import logging
import os
from datetime import datetime, timedelta
from incremental_load_yfinance import IncrementalYFinanceLoader
from parquet_utils import (
    get_latest_date_from_parquet, 
    validate_parquet_data,
    scan_all_parquet_files,
    calculate_update_priority
)
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def example_1_check_existing_files():
    """Example 1: Check existing parquet files for their latest dates"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Check existing parquet files")
    print("="*60)
    
    # Scan all files in the raw data directory
    summary = scan_all_parquet_files(config.RAW_DATA_DIR)
    
    if not summary:
        print("No parquet files found in the raw data directory.")
        return
    
    print(f"Found {len(summary)} parquet files:")
    
    # Show first 10 files as example
    count = 0
    for ticker, info in summary.items():
        if count >= 10:
            break
        
        if info['is_valid'] and info['date_range']:
            latest_date = info['date_range'][1]
            days_behind = (datetime.now().date() - 
                          datetime.strptime(latest_date, '%Y-%m-%d').date()).days
            
            print(f"  {ticker}: {info['date_range'][0]} to {latest_date} "
                  f"({info['row_count']} rows, {days_behind} days behind)")
        else:
            print(f"  {ticker}: INVALID or MISSING DATA")
        
        count += 1
    
    if len(summary) > 10:
        print(f"  ... and {len(summary) - 10} more files")


def example_2_update_priorities():
    """Example 2: Calculate which files need updates most urgently"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Calculate update priorities")
    print("="*60)
    
    priorities = calculate_update_priority(config.RAW_DATA_DIR, max_age_days=7)
    
    if not priorities:
        print("No files found to analyze.")
        return
    
    # Group by priority
    high_priority = [p for p in priorities if p['priority'] == 'HIGH']
    medium_priority = [p for p in priorities if p['priority'] == 'MEDIUM']
    low_priority = [p for p in priorities if p['priority'] == 'LOW']
    
    print(f"Update Priority Summary:")
    print(f"  HIGH priority (needs immediate update): {len(high_priority)} files")
    print(f"  MEDIUM priority (should update soon): {len(medium_priority)} files")
    print(f"  LOW priority (up to date): {len(low_priority)} files")
    
    # Show top 5 high priority files
    if high_priority:
        print(f"\nTop 5 HIGH priority files:")
        for item in high_priority[:5]:
            print(f"  {item['ticker']}: {item['reason']}")


def example_3_validate_specific_file():
    """Example 3: Validate a specific parquet file"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Validate specific file")
    print("="*60)
    
    # Find any parquet file to validate
    parquet_files = [f for f in os.listdir(config.RAW_DATA_DIR) if f.endswith('.parquet')]
    
    if not parquet_files:
        print("No parquet files found to validate.")
        return
    
    # Use the first file as example
    example_file = os.path.join(config.RAW_DATA_DIR, parquet_files[0])
    ticker = parquet_files[0].replace('_OHLCV.parquet', '')
    
    print(f"Validating file: {ticker}")
    
    validation = validate_parquet_data(example_file)
    
    print(f"Validation Results for {ticker}:")
    print(f"  Is Valid: {validation['is_valid']}")
    print(f"  Row Count: {validation['row_count']:,}")
    print(f"  Column Count: {validation['column_count']}")
    print(f"  Date Range: {validation['date_range']}")
    print(f"  Missing Values: {validation['missing_values']}")
    print(f"  Duplicate Dates: {validation['duplicate_dates']}")
    
    if validation['data_quality_issues']:
        print(f"  Data Quality Issues:")
        for issue in validation['data_quality_issues']:
            print(f"    - {issue}")
    else:
        print(f"  No data quality issues found!")


def example_4_dry_run_incremental_update():
    """Example 4: Dry run of incremental update (shows what would be updated)"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Dry run of incremental update")
    print("="*60)
    
    # This is a simulation - we'll check what would be updated without actually updating
    priorities = calculate_update_priority(config.RAW_DATA_DIR, max_age_days=1)
    
    updates_needed = [p for p in priorities if p['priority'] in ['HIGH', 'MEDIUM']]
    
    print(f"Dry Run Results:")
    print(f"  Total files that would be updated: {len(updates_needed)}")
    
    if updates_needed:
        print(f"  Files to update:")
        for item in updates_needed[:10]:  # Show first 10
            print(f"    {item['ticker']}: {item['reason']}")
        
        if len(updates_needed) > 10:
            print(f"    ... and {len(updates_needed) - 10} more files")
        
        # Estimate time
        estimated_time = len(updates_needed) * (config.RATE_LIMIT_DELAY + 2)  # 2 seconds for processing
        print(f"  Estimated update time: {estimated_time:.0f} seconds ({estimated_time/60:.1f} minutes)")
    else:
        print("  All files are up to date!")


def example_5_single_ticker_update():
    """Example 5: Update a single ticker (for testing)"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Single ticker update example")
    print("="*60)

    # This is a demonstration of how you would update a single ticker
    print("This example shows how to update a single ticker.")
    print("To actually run this, you would need to:")
    print("1. Ensure you have the Excel file with ticker data")
    print("2. Update the config.py file with correct paths")
    print("3. Run the incremental loader")

    # Example code (commented out to avoid actual execution)
    loader = IncrementalYFinanceLoader(
        input_dir=config.DATA_DIR,
        excel_path=config.EXCEL_PATH,
        # output_dir=config.OUTPUT_DIR,  # ouput_dirがない場合はinput_dirと同じになる
        rate_limit_delay=config.RATE_LIMIT_DELAY
    )

    # This would update all tickers that need updates
    stats = loader.process_incremental_updates(max_lookback_days=config.MAX_LOOKBACK_DAYS)

    print(f"Incremental download complete: {stats}")

    # Rebuild batches and master file if any updates were made
    if stats['updated_tickers'] > 0 or stats['new_tickers'] > 0:
        loader.rebuild_batches_and_master()
    else:
        print("No updates were made, skipping batch rebuild")

    print("Rebuild_batches_and_master Process complete!")


def example_6_rebuild_batches_and_master():
    """Example 6: Rebuild_batches_and_master"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Rebuild_batches_and_master")
    print("="*60)

    # Example code (commented out to avoid actual execution)
    loader = IncrementalYFinanceLoader(
        input_dir=config.DATA_DIR,
        excel_path=config.EXCEL_PATH,
        # output_dir=config.OUTPUT_DIR,  # ouput_dirがない場合はinput_dirと同じになる
        rate_limit_delay=config.RATE_LIMIT_DELAY
    )

    # This would update all tickers that need updates
    loader.rebuild_batches_and_master()

    print("Process complete!")


def main():
    """Run all examples"""
    print("Incremental yfinance Update - Quick Start Examples")
    print("=" * 60)
    
    # Check if directories exist
    if not os.path.exists(config.RAW_DATA_DIR):
        print(f"Raw data directory not found: {config.RAW_DATA_DIR}")
        print("Please create the directory and add some sample parquet files to run the examples.")
        return
    
    # Run examples
    example_1_check_existing_files()
    example_2_update_priorities()
    example_3_validate_specific_file()
    example_4_dry_run_incremental_update()
    example_5_single_ticker_update()
    
    print("\n" + "="*60)
    print("IMPLEMENTATION GUIDE")
    print("="*60)
    print("""
To implement incremental updates in your project:

1. SETUP:
   - Update config.py with your actual file paths
   - Ensure you have the Excel file with ticker data
   - Install required dependencies: pip install yfinance pandas pyarrow tqdm

2. BASIC USAGE:
   - Use parquet_utils.py functions to check existing files
   - Use IncrementalYFinanceLoader for updates
   - Run quick_start_example.py to see current status

3. RECOMMENDED WORKFLOW:
   - Run daily/weekly incremental updates
   - Use calculate_update_priority() to identify files needing updates
   - Use validate_parquet_data() to check data quality
   - Monitor logs for any issues

4. ADVANCED FEATURES:
   - Batch processing for memory efficiency
   - Automatic corruption detection and recovery
   - Rate limiting to avoid yfinance restrictions
   - Comprehensive logging and error handling

5. CUSTOMIZATION:
   - Modify rate_limit_delay in config.py
   - Adjust max_lookback_days for your needs
   - Update batch_size based on your system memory
   - Add custom validation rules in parquet_utils.py
""")


if __name__ == "__main__":
    main()