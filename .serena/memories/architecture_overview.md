# Architecture Overview

## Directory Structure
```
├── src/                   # Production code
│   ├── backtest.py        # Main backtesting engine
│   ├── config.py          # Configuration management
│   ├── incremental_load_yfinance.py  # Advanced data loader
│   ├── parquet_utils.py   # Data validation utilities
│   ├── stock_screener.py  # Screening logic
│   └── indicators/        # Technical indicators
│       ├── base.py        # Base indicator class
│       ├── bargain_hunter.py  # Bargain hunter strategy
│       └── __init__.py
├── src_poc/               # Proof of concept implementations
├── scripts/               # Batch scripts for environment switching
├── data/                  # Data storage directory
├── testing/               # Test data and utilities
└── doc/                   # Documentation
```

## Core Components

### 1. Configuration System (`config.py`)
- Environment-based configuration (test/dev/prod)
- YAML-based configuration file (`config.yaml`)
- Automatic environment switching via `.env.current`

### 2. Data Management Layer
- **Incremental Loading**: Only downloads new data since last update
- **Parquet Storage**: Efficient columnar storage format
- **Data Validation**: Integrity checking and corruption recovery
- **File Patterns**: Individual ticker files, batch files, master file

### 3. Screening Engine (`backtest.py`, `stock_screener.py`)
- Financial screening (ROE, PER, Operating Margin)
- Technical analysis (RSI, Moving Averages, Trend analysis)
- Market sentiment scoring system

### 4. Indicator Framework (`indicators/`)
- Base class for technical indicators
- Modular indicator implementations
- Parallel processing support for batch calculations