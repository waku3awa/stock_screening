# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Stock Screening System** focused on Japanese stock market (東証プライム) data analysis and incremental updates. The system implements multiple screening strategies based on technical analysis and fundamental analysis to identify investment opportunities with target monthly returns of 3-5%.

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
├── src/                   # Production code
│   ├── backtest.py        # Backtesting engine for screening strategies
│   ├── incremental_load_yfinance.py  # Advanced incremental data loader
│   └── parquet_utils.py   # Parquet file operations and validation
├── src_poc/               # Proof of concept and simpler implementations
│   ├── config.py          # Configuration management
│   ├── load_yfinance.py   # Basic data loading with incremental features
│   └── quick_start_example.py  # Usage examples
└── doc                    # Comprehensive documentation
    └── *.md files
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

## Development Environment

**Python Environment Management:**
This project uses `uv` for Python environment and dependency management.

```bash
# Install dependencies and create virtual environment
uv add pyyaml python-dotenv

# Run Python scripts with uv
uv run python src/config.py

# Add new dependencies
uv add <package-name>
```

**Japanese Character Encoding:**
To prevent character encoding issues with Japanese text on Windows:

```bash
# Set UTF-8 encoding for Python output
set PYTHONIOENCODING=utf-8 && uv run python <script.py>

# Or use PowerShell
$env:PYTHONIOENCODING="utf-8"; uv run python <script.py>
```

## Common Development Commands

**Note:** This project doesn't have traditional build/test infrastructure. Most operations are run directly through Python scripts using `uv`.

### Data Operations
```bash
# Basic incremental update (simple approach)
uv run python src_poc/load_yfinance.py

# Advanced incremental update with detailed logging
set PYTHONIOENCODING=utf-8 && uv run python src/incremental_load_yfinance.py

# Quick start example with step-by-step guidance
uv run python src_poc/quick_start_example.py

# Test configuration system
set PYTHONIOENCODING=utf-8 && uv run python src/config.py
```

### Validation and Utilities
```python
# Validate parquet files and check data quality (in Python)
from src.parquet_utils import validate_parquet_data, scan_all_parquet_files

# Check update priorities for existing data
from src.parquet_utils import calculate_update_priority

# Access configuration settings
from src.config import TEST_DATA_DIR, RATE_LIMIT_DELAY, RSI_PERIOD
```

### Backtesting
```bash
# Run full backtesting analysis
set PYTHONIOENCODING=utf-8 && uv run python src/backtest.py
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

## Environment Management (Test/Production Switching)

The system supports multiple execution environments with automatic configuration switching based on environment settings.

### Available Environments

- **test**: Uses test data (`../test_stock_data`) with sample companies for safe testing
- **production**: Uses production data (`stock_data/`) with full market data
- **development**: Uses production data structure but with development-friendly settings

### Environment Switching Methods

#### Method 1: Batch Scripts (Recommended)

**Test Environment Execution:**
```bash
# Execute backtest with test data
scripts\run_backtest_test.bat
```

**Production Environment Execution:**
```bash
# Execute backtest with production data (CAUTION!)
scripts\run_backtest_prod.bat
```

#### Method 2: Direct Command Line

**Test Environment:**
```bash
echo APP_ENV=test> .env.current && set PYTHONIOENCODING=utf-8 && uv run python src/backtest.py
```

**Production Environment:**
```bash
echo APP_ENV=production> .env.current && set PYTHONIOENCODING=utf-8 && uv run python src/backtest.py
```

**Development Environment (Default):**
```bash
echo APP_ENV=development> .env.current && set PYTHONIOENCODING=utf-8 && uv run python src/backtest.py
```

### Environment Configuration Files

- **`.env.test`** - Test environment settings (uses test data)
- **`.env.production`** - Production environment settings (uses full market data)  
- **`.env.current`** - Current environment selector (auto-generated)

### Environment-Specific Data Sources

| Environment | Master Data File | 1st Screening Results | Data Directory |
|-------------|------------------|----------------------|----------------|
| **test** | `test_stock_data/ticker_combined_OHLCV.parquet` | `testing/test_data_selected_companies.xlsx` | `../test_stock_data` |
| **production** | `stock_data/ticker_combined_OHLCV.parquet` | `data_j.xls` | `stock_data` |
| **development** | `stock_data/ticker_combined_OHLCV.parquet` | `data_j.xls` | `stock_data` |

### Safety Features

- **Environment Display**: Execution starts by showing current environment and data source
- **Automatic Path Resolution**: Environment-specific file paths are automatically resolved
- **Configuration Validation**: Missing environment files trigger appropriate warnings
- **Gitignore Protection**: All environment configuration files are excluded from version control

### Test Data Configuration

**Test Data Directory**: `../test_stock_data`

The system uses a dedicated test data directory containing 33 sample companies for safe testing and development. This allows validation of screening strategies without risk to production data or analysis.

**Test Data Features:**
- Complete OHLCV data structure matching production format
- Representative sample of Japanese stocks from various sectors
- Safe for experimentation and strategy development
- Isolated from production data pipeline

## Extension Points

The system is designed for extensibility:
- **New Screening Strategies**: Add to the strategy pattern in backtest.py
- **Additional Data Sources**: Extend data loading utilities
- **Database Integration**: System specification includes MySQL schema for production deployment
- **Real-time Monitoring**: Framework ready for market-hours monitoring integration