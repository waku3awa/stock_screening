# Development Workflow & Conventions

## Task Completion Checklist
1. **Run Tests**: No formal test framework - validate with sample data in test environment
2. **Environment Testing**: Always test in test environment first using `scripts\run_backtest_test.bat`
3. **Data Validation**: Check parquet file integrity after data operations
4. **Encoding**: Ensure UTF-8 encoding for Japanese text output

## Code Style & Conventions
- **Python 3.13+**: Modern Python features expected
- **Type Hints**: Not extensively used but recommended for new code
- **Japanese Comments**: Mixed Japanese/English comments are normal
- **Configuration**: Use YAML configuration file, not hardcoded values
- **Error Handling**: Robust error handling for network failures and data corruption

## Environment Safety
- **Always use test environment first** for new features
- **Production environment** should only be used after thorough testing
- **Environment files** (`.env.*`) are gitignored for safety

## Data Processing Patterns
- **Incremental Updates**: Prefer incremental over full downloads
- **Batch Processing**: Process data in configurable batches (default: 200 files)
- **Rate Limiting**: Respect yfinance API limits (1 second delay between requests)
- **Validation**: Always validate parquet files after operations

## File Naming Conventions
- **Ticker Files**: `{TICKER}_OHLCV.parquet` (e.g., `7203.T_OHLCV.parquet`)
- **Batch Files**: `batch_{number}_combined.parquet`
- **Master File**: `ticker_combined_OHLCV.parquet`
- **Environment Files**: `.env.{environment}`, `.env.current`