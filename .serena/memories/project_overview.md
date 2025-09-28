# Project Overview

## Purpose
Stock Screening System focused on Japanese stock market (東証プライム) data analysis. The system implements multiple screening strategies based on technical and fundamental analysis to identify investment opportunities with target monthly returns of 3-5%.

## Core Technologies
- **Python 3.13+** (using uv for dependency management)
- **pandas** - Data manipulation and analysis
- **yfinance** - Yahoo Finance API for stock data
- **numpy** - Numerical computing for technical indicators
- **pyarrow** - Parquet file format for efficient data storage
- **tqdm** - Progress bars for long-running operations

## Key Features
- Incremental data loading to avoid redundant API calls
- Multiple screening strategies (financial + technical analysis)
- Environment-based configuration (test/development/production)
- Parquet-based data caching and validation
- Japanese stock market focus with proper ticker formatting (.T suffix)