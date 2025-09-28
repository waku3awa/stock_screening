# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Stock Screening System** focused on Japanese stock market (東証プライム) data analysis and incremental updates. The system implements multiple screening strategies based on technical analysis and fundamental analysis to identify investment opportunities with target monthly returns of 3-5%.

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
├── src/                   # Production code
│   ├── backtest.py        # Backtesting engine for screening strategies
│   ├── config.py          # Configuration management
│   ├── incremental_load_yfinance.py  # Advanced incremental data loader
│   ├── parquet_utils.py   # Parquet file operations and validation
│   ├── stock_screener.py  # Core screening logic implementation
│   └── indicators/        # Technical indicator framework
│       ├── base.py        # Base indicator class
│       ├── bargain_hunter.py  # Bargain hunter strategy
│       └── __init__.py
├── src_poc/               # Proof of concept and simpler implementations
│   ├── config.py          # Legacy configuration (use src/config.py)
│   ├── load_yfinance.py   # Basic data loading with incremental features
│   └── quick_start_example.py  # Usage examples
├── scripts/               # Windows batch scripts for environment management
│   ├── run_backtest_test.bat   # Execute backtest in test environment
│   ├── run_backtest_prod.bat   # Execute backtest in production environment
│   └── set_env_*.bat      # Environment configuration scripts
└── doc/                   # Comprehensive documentation
    └── *.md files
```

## Key Technologies & Dependencies

**Core Dependencies (from pyproject.toml):**
- `pandas>=2.3.1` - Data manipulation and analysis
- `yfinance>=0.2.65` - Yahoo Finance API for stock data
- `numpy>=2.3.2` - Numerical computing for technical indicators
- `pyarrow>=21.0.0` - Parquet file format support
- `tqdm>=4.67.1` - Progress bars for long-running operations
- `python-dotenv>=1.1.1` - Environment variable management
- `pyyaml>=6.0.2` - YAML configuration file support
- `openpyxl>=3.1.5` - Excel file operations

**Development Requirements:**
- Python 3.13+ (specified in pyproject.toml)
- `uv` package manager for dependency management

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
**Files:** `src/config.py`, `config.yaml`

**Purpose:** Centralized configuration management with environment-specific settings and YAML-based configuration.

**Key Configuration Areas:**
- Environment-based configuration (test/development/production)
- Data directory structure and file paths
- Rate limiting settings (`RATE_LIMIT_DELAY = 1.0` seconds)
- Processing parameters (`BATCH_SIZE = 200`, `MAX_LOOKBACK_DAYS = 30`)
- Screening strategy parameters (financial filters, technical analysis)
- Market-specific settings (ticker format, trading hours)

### 4. Technical Indicator Framework
**Files:** `src/indicators/`

**Purpose:** Modular framework for implementing and managing technical analysis indicators.

**Key Features:**
- Base indicator class for consistent implementation patterns
- Parallel processing support for batch calculations
- Configurable parameters via YAML configuration
- Extensible architecture for new indicator strategies

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

**Note:** This project uses Windows batch scripts for common operations and `uv` for Python environment management.

### Quick Reference (Most Common Commands)

```bash
# Test environment backtest (RECOMMENDED for development)
scripts\run_backtest_test.bat

# Production environment backtest (CAUTION!)
scripts\run_backtest_prod.bat

# Incremental data update
set PYTHONIOENCODING=utf-8 && uv run python src/incremental_load_yfinance.py

# Add new dependencies
uv add <package-name>
```

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

### Configuration Structure
Configuration is managed through YAML files and environment variables:
```yaml
# config.yaml - Main configuration file
data_source:
  rate_limit_delay: 1.0
  batch_size: 200

screening:
  financial:
    min_roe: 0.10
    max_per: 15
  technical:
    rsi_period: 14
    moving_averages: [5, 25, 75]

indicators:
  bargain_hunter:
    ma_period: 200
    n_jobs: -1  # Use all CPU cores
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