# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Stock Screening System** focused on Japanese stock market (東証プライム) data analysis and incremental updates. The system implements multiple screening strategies based on technical analysis and fundamental analysis to identify investment opportunities with target monthly returns of 3-5%.

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
├── src/                    # Production code
│   ├── backtest.py        # Backtesting engine for screening strategies
│   ├── incremental_load_yfinance.py  # Advanced incremental data loader
│   └── parquet_utils.py   # Parquet file operations and validation
├── src_poc/               # Proof of concept and simpler implementations
│   ├── config.py          # Configuration management
│   ├── load_yfinance.py   # Basic data loading with incremental features
│   └── quick_start_example.py  # Usage examples
└── *.md files             # Comprehensive documentation
```

## Key Technologies & Dependencies

**Core Dependencies:**
- `pandas` - Data manipulation and analysis
- `yfinance` - Yahoo Finance API for stock data
- `numpy` - Numerical computing for technical indicators
- `tqdm` - Progress bars for long-running operations
- `pyarrow` - Parquet file format support

**Optional Dependencies:**
- `curl_cffi` - Enhanced HTTP requests (for rate limiting bypass)
- `matplotlib` - Data visualization for backtesting

**Google Colab Specific:**
- Some scripts include `google.colab` imports for cloud execution
- `tqdm.notebook` for Jupyter notebook progress bars

## Core System Components

### 1. Data Management Layer
**Files:** `parquet_utils.py`, `incremental_load_yfinance.py`, `config.py`

**Purpose:** Efficient storage and retrieval of large-scale stock price data using Parquet format with incremental update capabilities.

**Key Features:**
- **Incremental Updates**: Only downloads data newer than the latest cached date
- **Data Validation**: Comprehensive parquet file integrity checking
- **Memory Optimization**: Reads only necessary columns (e.g., Date column for date checking)
- **Error Recovery**: Automatic handling of corrupted files and network failures

### 2. Screening Engine
**Files:** `backtest.py` (primary), system specification document

**Purpose:** Implementation of multiple stock screening strategies based on technical and fundamental analysis.

**Screening Strategies:**
- **Primary Financial Screening**: ROE > 10%, PER < 15, Operating Margin > 10%
- **Technical Analysis**: RSI (25-75 range), Moving Average convergence (±8%), Trend analysis
- **Market Score**: 3-dimensional market sentiment analysis (Momentum, Position, Psychology)

### 3. Configuration System
**Files:** `config.py`

**Purpose:** Centralized configuration management for data paths, API settings, and processing parameters.

**Key Configuration Areas:**
- Data directory structure (`RAW_DATA_DIR`, `BATCH_DATA_DIR`)
- Rate limiting settings (`RATE_LIMIT_DELAY = 1.0` seconds)
- Processing parameters (`BATCH_SIZE = 200`, `MAX_LOOKBACK_DAYS = 30`)

## Common Development Commands

**Note:** This project doesn't have traditional build/test infrastructure. Most operations are run directly through Python scripts.

### Data Operations
```python
# Basic incremental update (simple approach)
python src_poc/load_yfinance.py

# Advanced incremental update with detailed logging
python src/incremental_load_yfinance.py

# Quick start example with step-by-step guidance
python src_poc/quick_start_example.py
```

### Validation and Utilities
```python
# Validate parquet files and check data quality
from src.parquet_utils import validate_parquet_data, scan_all_parquet_files

# Check update priorities for existing data
from src.parquet_utils import calculate_update_priority
```

### Backtesting
```python
# Run full backtesting analysis
python src/backtest.py
```

## Important File Patterns

### Parquet File Structure
- Individual ticker files: `{TICKER}_OHLCV.parquet` (e.g., `7203.T_OHLCV.parquet`)
- Batch files: `batch_{number}_combined.parquet`
- Master file: `ticker_combined_OHLCV.parquet`

### Data Columns
All parquet files follow standardized column structure:
- `Date` - Trading date (index)
- `Open`, `High`, `Low`, `Close` - OHLC price data
- `Volume` - Trading volume
- `Ticker` - Stock symbol (e.g., "7203.T" for Tokyo Stock Exchange)

### Configuration Switching
The incremental update mode can be toggled in `load_yfinance.py`:
```python
INCREMENTAL_UPDATE = True   # Incremental mode (recommended for daily updates)
INCREMENTAL_UPDATE = False  # Full download mode (initial setup)
```

## Development Workflow

1. **Initial Setup**: Configure paths in `config.py` and ensure required dependencies are installed
2. **Data Initialization**: Run full download with `INCREMENTAL_UPDATE = False`
3. **Daily Operations**: Use incremental updates with `INCREMENTAL_UPDATE = True`
4. **Strategy Development**: Use backtesting framework to validate new screening strategies
5. **Data Validation**: Regularly run parquet validation utilities to ensure data integrity

## Performance Considerations

- **Rate Limiting**: yfinance API requires 1-second delays between requests
- **Memory Management**: Large datasets should be processed in batches (default: 200 files)
- **Caching Strategy**: Parquet files serve as local cache to minimize API calls
- **Parallel Processing**: Can be implemented for independent ticker processing

## Error Handling Patterns

The system implements robust error handling for common issues:
- **Network Failures**: Automatic retry with exponential backoff
- **Corrupted Files**: Automatic backup and recovery
- **Missing Data**: Graceful handling of delisted or suspended stocks
- **API Limits**: Built-in rate limiting and respect for yfinance quotas

## Market-Specific Considerations

**Tokyo Stock Exchange Focus:**
- Ticker format: `{CODE}.T` (e.g., "7203.T" for Toyota)
- Trading hours: JST timezone considerations
- Market holidays: Japanese calendar support
- Currency: JPY pricing

**Screening Strategy Context:**
- Targets: Monthly returns of 3-5%
- Market conditions: Most effective in neutral to slightly bearish markets (score -1 to 0)
- Time horizon: Medium-term technical analysis (5/25/75-day moving averages)

## Extension Points

The system is designed for extensibility:
- **New Screening Strategies**: Add to the strategy pattern in backtest.py
- **Additional Data Sources**: Extend data loading utilities
- **Database Integration**: System specification includes MySQL schema for production deployment
- **Real-time Monitoring**: Framework ready for market-hours monitoring integration