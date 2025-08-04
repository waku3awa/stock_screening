# Incremental yfinance Updates Implementation Guide

This repository provides a comprehensive solution for implementing incremental updates to stock data using yfinance and parquet files. The solution efficiently handles large datasets by downloading only new data since the last update.

## 📋 Overview

The solution addresses the following key requirements:
1. **Check existing parquet files** for their latest date
2. **Download only missing data** from that date to current date
3. **Append new data** to existing files efficiently
4. **Handle edge cases** like corrupted files, market gaps, and delisted tickers

## 🏗️ Architecture

```
├── load_yfinance.py              # 元スクリプト（差分更新機能追加版）
├── incremental_load_yfinance.py  # 高機能差分更新クラス
├── parquet_utils.py              # parquet操作ユーティリティ
├── config.py                     # 設定ファイル
├── quick_start_example.py        # 詳細な実行例
└── README_incremental_updates.md # このドキュメント
```

## 📁 各ファイルの詳細

### メインファイル

#### `load_yfinance.py`
- **用途**: 元のスクリプトに差分更新機能を追加したバージョン
- **対象**: 初心者・シンプルな使用
- **機能**: 
  - 既存データの最新日付から現在までの差分データをダウンロード
  - 新旧データの自動マージ・重複削除
  - バッチ処理・統合処理による最終的な統合ファイル作成
- **使用方法**: 
  ```python
  # 95行目で設定変更
  INCREMENTAL_UPDATE = True   # 差分更新モード
  INCREMENTAL_UPDATE = False  # 全期間ダウンロード
  
  # Google Colabで実行
  %run load_yfinance.py
  ```

#### `incremental_load_yfinance.py`
- **用途**: 高機能な差分更新クラス（IncrementalYFinanceLoader）
- **対象**: 上級者・詳細制御
- **機能**:
  - より詳細な設定とエラーハンドリング
  - 優先度ベースの更新処理
  - 統計情報の詳細レポート
  - 柔軟な設定変更
- **使用方法**:
  ```python
  from incremental_load_yfinance import IncrementalYFinanceLoader
  
  loader = IncrementalYFinanceLoader(
      output_dir="/path/to/stock/data",
      excel_path="/path/to/ticker/list.xls"
  )
  stats = loader.process_incremental_updates()
  ```

### ユーティリティファイル

#### `parquet_utils.py`
- **用途**: parquetファイル操作のユーティリティ関数
- **対象**: 個別のファイル操作や検証を行いたい場合
- **機能**:
  - ファイルの検証・修復
  - 更新優先度の計算
  - データ品質チェック
  - 効率的なデータ追加
- **使用方法**:
  ```python
  from parquet_utils import validate_parquet_data, calculate_update_priority
  
  # ファイル検証
  validation = validate_parquet_data("ticker_file.parquet")
  
  # 更新優先度計算
  priorities = calculate_update_priority("/path/to/raw/data")
  ```

#### `config.py`
- **用途**: 設定ファイル（各種パラメータの定義）
- **対象**: 設定を細かく調整したい場合
- **内容**:
  - ディレクトリパス
  - API設定（レート制限など）
  - 処理パラメータ（バッチサイズなど）
- **使用方法**:
  ```python
  from config import Config
  
  config = Config()
  print(config.output_dir)
  ```

### ドキュメント・使用例

#### `quick_start_example.py`
- **用途**: クイックスタートガイド（詳細な実行例）
- **対象**: 高機能クラスの使用方法を知りたい場合
- **内容**:
  - 段階的な実行手順
  - 高機能クラスの使用例
  - 実際のコード例
  - パフォーマンス最適化
- **使用方法**:
  ```python
  # 詳細な実行例を確認
  %run quick_start_example.py
  ```

## 🎯 どのファイルを使うべきか

### 初心者・シンプルな使用
- **メインファイル**: `load_yfinance.py`
- **特徴**: 既存のスクリプトに最小限の変更で差分更新機能を追加

### 中級者・バランス重視
- **メインファイル**: `incremental_load_yfinance.py`
- **ドキュメント**: `quick_start_example.py`
- **特徴**: より詳細な制御とエラーハンドリングが可能

### 上級者・詳細制御
- **メインファイル**: `incremental_load_yfinance.py`
- **ユーティリティ**: `parquet_utils.py`
- **設定**: `config.py`
- **特徴**: 個別のファイル操作や細かい設定変更が可能

### 開発者・カスタマイズ
- **全ファイル**: 必要に応じて組み合わせて使用
- **特徴**: 独自の要件に合わせてカスタマイズ可能

## 🚀 Key Features

### 1. Efficient Date Checking
- Reads only the Date column from parquet files for maximum efficiency
- Minimal memory usage even with large files
- Handles corrupted files gracefully

### 2. Smart Incremental Downloads
- Downloads only data newer than the latest existing date
- Configurable lookback period to avoid processing stale tickers
- Automatic handling of market holidays and gaps

### 3. Data Quality Management
- Comprehensive validation of parquet files
- Automatic detection and recovery from corrupted data
- Duplicate detection and removal

### 4. Robust Error Handling
- Rate limiting to avoid yfinance restrictions
- Retry mechanisms for failed downloads
- Comprehensive logging for troubleshooting

## 📊 Implementation Strategies

### Strategy 1: Individual File Updates (Recommended)

This approach updates individual ticker files first, then rebuilds batches:

**Advantages:**
- Simple and reliable
- Easy to troubleshoot
- Maintains data integrity
- Self-healing for corrupted files

**Process:**
1. Check each ticker file for latest date
2. Download only missing data
3. Append to existing file
4. Rebuild batch files from updated individual files

```python
from incremental_load_yfinance import IncrementalYFinanceLoader

loader = IncrementalYFinanceLoader(
    output_dir="/path/to/stock/data",
    excel_path="/path/to/ticker/list.xls",
    rate_limit_delay=1.0
)

# Process incremental updates
stats = loader.process_incremental_updates(max_lookback_days=30)

# Rebuild batches and master file
loader.rebuild_batches_and_master()
```

### Strategy 2: Batch-Level Updates

For advanced users who want to optimize I/O operations:

**Advantages:**
- Potentially faster for large datasets
- Reduced file operations

**Disadvantages:**
- More complex implementation
- Harder to troubleshoot
- Risk of data consistency issues

## 🔧 Best Practices

### 1. Reading Latest Date from Parquet Files

```python
from parquet_utils import get_latest_date_from_parquet

# Most efficient approach - reads only Date column
latest_date = get_latest_date_from_parquet('AAPL_OHLCV.parquet')
if latest_date:
    start_date = (latest_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
else:
    start_date = '2010-01-01'  # Default for new files
```

### 2. Handling Date Gaps and Validation

```python
# Check for missing date ranges
from parquet_utils import get_missing_date_ranges

missing_ranges = get_missing_date_ranges(
    'AAPL_OHLCV.parquet', 
    '2010-01-01', 
    '2025-06-27'
)

# Validate data quality
from parquet_utils import validate_parquet_data

validation = validate_parquet_data('AAPL_OHLCV.parquet')
if not validation['is_valid']:
    print(f"Data quality issues: {validation['data_quality_issues']}")
```

### 3. Efficient Parquet Appending

```python
# Recommended approach for appending data
from parquet_utils import append_to_parquet

success = append_to_parquet(
    file_path='AAPL_OHLCV.parquet',
    new_data=new_dataframe,
    remove_duplicates=True
)
```

## 🔍 Edge Case Handling

### 1. Corrupted Files
```python
# Automatic detection and recovery
def handle_corrupted_file(file_path):
    try:
        data = pd.read_parquet(file_path)
        return data
    except Exception as e:
        # Move to backup and treat as new ticker
        backup_path = file_path + ".corrupted"
        os.rename(file_path, backup_path)
        return None
```

### 2. Market Holidays and Gaps
```python
# yfinance automatically handles non-trading days
# No special handling required - just use consecutive dates
df = yf.download(ticker, start=start_date, end=end_date)
```

### 3. Delisted Tickers
```python
# Check for empty downloads
if df.empty:
    logger.warning(f"No data for {ticker} - possibly delisted")
    # Archive the file or mark as inactive
```

### 4. Rate Limiting
```python
# Built-in rate limiting
import time
time.sleep(1.0)  # Wait 1 second between requests

# Monitor for rate limit errors
try:
    df = yf.download(ticker, start=start_date, end=end_date)
except Exception as e:
    if "429" in str(e):  # Rate limit error
        time.sleep(60)  # Wait longer and retry
```

## 🛠️ Usage Examples

### Quick Start
```bash
# 1. Update configuration
vim config.py  # Set your paths

# 2. Run examples to see current status
python quick_start_example.py

# 3. Run incremental update
python incremental_load_yfinance.py
```

### Advanced Usage
```python
# Custom incremental update with specific settings
loader = IncrementalYFinanceLoader(
    output_dir="/custom/path",
    excel_path="/custom/ticker/list.xls",
    rate_limit_delay=2.0  # Slower for stability
)

# Update only high-priority tickers
from parquet_utils import calculate_update_priority

priorities = calculate_update_priority("/custom/path/raw", max_age_days=7)
high_priority = [p for p in priorities if p['priority'] == 'HIGH']

print(f"Need to update {len(high_priority)} high-priority tickers")
```

### Data Quality Monitoring
```python
# Scan all files for issues
from parquet_utils import scan_all_parquet_files

summary = scan_all_parquet_files("/path/to/raw/data")
issues = {k: v for k, v in summary.items() if not v['is_valid']}

print(f"Found {len(issues)} files with data quality issues")
```

## 📈 Performance Considerations

### Memory Optimization
- Read only necessary columns when checking dates
- Process files in batches to avoid memory overflow
- Use efficient data types (int64 for Volume, float64 for prices)

### Network Optimization
- Implement rate limiting (1-2 seconds between requests)
- Use session objects for connection reuse
- Handle network errors gracefully with retries

### Storage Optimization
- Use parquet compression
- Partition large datasets by date or ticker
- Regular cleanup of temporary files

## 🔒 Error Handling and Recovery

### Automatic Recovery
- Corrupted files are automatically moved to backup
- Failed downloads are logged and can be retried
- Data validation ensures integrity

### Manual Recovery
```python
# Manually rebuild from individual files
loader = IncrementalYFinanceLoader(output_dir, excel_path)
loader.rebuild_batches_and_master(batch_size=200)

# Validate all files
summary = scan_all_parquet_files(raw_data_dir)
invalid_files = [k for k, v in summary.items() if not v['is_valid']]
```

## 🧪 Testing and Validation

### Unit Testing
```python
# Test utility functions
from parquet_utils import get_latest_date_from_parquet, validate_parquet_data

# Test with sample data
test_file = "test_data.parquet"
assert get_latest_date_from_parquet(test_file) is not None
assert validate_parquet_data(test_file)['is_valid']
```

### Integration Testing
```python
# Test full workflow with small dataset
loader = IncrementalYFinanceLoader(test_dir, test_excel)
stats = loader.process_incremental_updates(max_lookback_days=7)
assert stats['updated_tickers'] >= 0
```

## 📝 Configuration Options

### Key Settings (config.py)
```python
# Rate limiting
RATE_LIMIT_DELAY = 1.0  # seconds between requests

# Data validation
MAX_LOOKBACK_DAYS = 30  # maximum days to look back

# Batch processing
BATCH_SIZE = 200  # files per batch

# File paths
DATA_DIR = '/path/to/stock/data'
EXCEL_PATH = '/path/to/ticker/list.xls'
```

## 🚨 Common Issues and Solutions

### Issue 1: "No module named 'curl_cffi'"
**Solution:** Install optional dependency
```bash
pip install curl_cffi
```

### Issue 2: Rate limiting errors
**Solution:** Increase delay in config.py
```python
RATE_LIMIT_DELAY = 2.0  # Increase from 1.0
```

### Issue 3: Memory errors during batch processing
**Solution:** Reduce batch size
```python
BATCH_SIZE = 100  # Reduce from 200
```

### Issue 4: Corrupted parquet files
**Solution:** Files are automatically handled and moved to backup

## 🔄 Maintenance and Monitoring

### Daily Monitoring
```python
# Check update status
priorities = calculate_update_priority(raw_data_dir)
high_priority = [p for p in priorities if p['priority'] == 'HIGH']

if high_priority:
    print(f"Warning: {len(high_priority)} files need immediate updates")
```

### Weekly Maintenance
```python
# Full validation scan
summary = scan_all_parquet_files(raw_data_dir)
issues = {k: v for k, v in summary.items() if not v['is_valid']}

# Log cleanup
if os.path.getsize('incremental_update.log') > 10*1024*1024:  # 10MB
    # Archive old log file
    pass
```

## 📚 API Reference

### IncrementalYFinanceLoader
- `process_incremental_updates(max_lookback_days)`: Main update method
- `rebuild_batches_and_master(batch_size)`: Rebuild processed files
- `get_latest_date_from_parquet(ticker)`: Get latest date for ticker

### Utility Functions
- `validate_parquet_data(file_path)`: Comprehensive file validation
- `append_to_parquet(file_path, new_data)`: Efficient data appending
- `scan_all_parquet_files(directory)`: Directory-wide file analysis
- `calculate_update_priority(directory)`: Prioritize updates by urgency

## 🎯 Next Steps

1. **Setup**: Configure paths in config.py
2. **Test**: Run quick_start_example.py
3. **Deploy**: Implement daily/weekly update schedule
4. **Monitor**: Set up alerting for failed updates
5. **Optimize**: Fine-tune parameters based on your usage patterns

This implementation provides a robust, efficient, and maintainable solution for incremental yfinance updates that scales with your data needs.