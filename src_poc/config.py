# -*- coding: utf-8 -*-
"""Configuration file for incremental yfinance updates"""

import os
from datetime import datetime

# Base configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data paths
DATA_DIR = os.path.join(BASE_DIR, 'stock_data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
BATCH_DATA_DIR = os.path.join(DATA_DIR, 'batch_size')
EXCEL_PATH = os.path.join(BASE_DIR, 'data_j.xls')  # Update this path

# Output files
MASTER_FILE = os.path.join(DATA_DIR, 'ticker_combined_OHLCV.parquet')
LOG_FILE = os.path.join(BASE_DIR, 'incremental_update.log')

# yfinance settings
RATE_LIMIT_DELAY = 1.0  # seconds between requests
MAX_LOOKBACK_DAYS = 30  # maximum days to look back for updates
BATCH_SIZE = 200  # number of files per batch

# Date settings
DEFAULT_START_DATE = '2010-01-01'
DEFAULT_END_DATE = datetime.now().strftime('%Y-%m-%d')

# Required columns for validation
REQUIRED_COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Ticker']

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': LOG_FILE,
            'mode': 'a',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(BATCH_DATA_DIR, exist_ok=True)