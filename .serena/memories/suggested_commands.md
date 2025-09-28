# Essential Development Commands

## Environment Management
```bash
# Install dependencies
uv add <package-name>

# Set UTF-8 encoding for Japanese text (Windows)
set PYTHONIOENCODING=utf-8 && uv run python <script.py>
```

## Data Operations
```bash
# Basic incremental data update
uv run python src_poc/load_yfinance.py

# Advanced incremental update with logging
set PYTHONIOENCODING=utf-8 && uv run python src/incremental_load_yfinance.py

# Quick start example
uv run python src_poc/quick_start_example.py

# Test configuration
set PYTHONIOENCODING=utf-8 && uv run python src/config.py
```

## Backtesting & Analysis
```bash
# Test environment backtest (SAFE - uses test data)
scripts\run_backtest_test.bat

# Production environment backtest (CAUTION - uses real data)
scripts\run_backtest_prod.bat

# Direct backtest execution
set PYTHONIOENCODING=utf-8 && uv run python src/backtest.py
```

## Environment Switching
```bash
# Set test environment
echo APP_ENV=test> .env.current

# Set production environment 
echo APP_ENV=production> .env.current

# Set development environment (default)
echo APP_ENV=development> .env.current
```

## System Commands (Windows)
```cmd
# Directory listing
dir

# Change directory
cd <path>

# Find files
where <filename>

# Search in files
findstr "pattern" <file>
```