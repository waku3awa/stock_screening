# -*- coding: utf-8 -*-
"""
株価スクリーニングシステム統一設定モジュール
YAML設定ファイルと環境変数を読み込み、プロジェクト全体に設定を提供
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from dotenv import load_dotenv

# プロジェクトルートディレクトリの特定
# このconfig.pyを基準に絶対パスを生成 (src -> feature-visualize)
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
ENV_FILE = PROJECT_ROOT / ".env"

# .envファイルから環境変数を読み込み
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class ConfigError(Exception):
    """設定ファイル関連のエラー"""
    pass


def load_yaml_config() -> Dict:
    """config.yamlを読み込んでディクショナリとして返す"""
    try:
        if not CONFIG_FILE.exists():
            raise ConfigError(f"設定ファイルが見つかりません: {CONFIG_FILE}")
        
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        if not config_data:
            raise ConfigError("設定ファイルが空または無効です")
            
        return config_data
    
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML設定ファイルの読み込みエラー: {e}")
    except Exception as e:
        raise ConfigError(f"設定ファイル読み込み中の予期しないエラー: {e}")


# YAML設定の読み込み
try:
    _config = load_yaml_config()
except ConfigError as e:
    print(f"警告: {e}")
    _config = {}

# === パス設定 (pathlibを使用した堅牢なパス管理) ===

# プロジェクトの基本ディレクトリ
DATA_DIR = PROJECT_ROOT / "stock_data"
RAW_DATA_DIR = DATA_DIR / "raw"
BATCH_DATA_DIR = DATA_DIR / "batch_size"

# テストデータディレクトリ (環境変数または相対パスから)
TEST_DATA_DIR = Path(os.getenv("TEST_DATA_DIR", "../test_stock_data"))
if not TEST_DATA_DIR.is_absolute():
    TEST_DATA_DIR = PROJECT_ROOT / TEST_DATA_DIR

# ファイルパス
EXCEL_PATH = PROJECT_ROOT / _config.get("data_source", {}).get("excel_file", "data_j.xls")
MASTER_FILE = DATA_DIR / "ticker_combined_OHLCV.parquet"
LOG_FILE = PROJECT_ROOT / "incremental_update.log"

# ディレクトリの自動作成
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
BATCH_DATA_DIR.mkdir(parents=True, exist_ok=True)
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# === データソース設定 ===

# yfinance API設定
YFINANCE_API_KEY = os.getenv("YFINANCE_API_KEY")
RATE_LIMIT_DELAY = _config.get("data_source", {}).get("rate_limit_delay", 1.0)
MAX_LOOKBACK_DAYS = _config.get("data_source", {}).get("max_lookback_days", 30)
BATCH_SIZE = _config.get("data_source", {}).get("batch_size", 200)

# === 日付設定 ===

DEFAULT_START_DATE = _config.get("backtest", {}).get("default_start_date", "2010-01-01")
DEFAULT_END_DATE = datetime.now().strftime('%Y-%m-%d')

# === スクリーニング戦略設定 ===

# 財務指標設定
FINANCIAL_FILTERS = _config.get("screening", {}).get("financial", {})
MIN_ROE = FINANCIAL_FILTERS.get("min_roe", 0.10)
MAX_PER = FINANCIAL_FILTERS.get("max_per", 15)
MIN_OPERATING_MARGIN = FINANCIAL_FILTERS.get("min_operating_margin", 0.10)

# テクニカル分析設定
TECHNICAL_PARAMS = _config.get("screening", {}).get("technical", {})
RSI_PERIOD = TECHNICAL_PARAMS.get("rsi_period", 14)
RSI_MIN = TECHNICAL_PARAMS.get("rsi_range", {}).get("min", 25)
RSI_MAX = TECHNICAL_PARAMS.get("rsi_range", {}).get("max", 75)
MOVING_AVERAGES = TECHNICAL_PARAMS.get("moving_averages", [5, 25, 75])
MA_CONVERGENCE_THRESHOLD = TECHNICAL_PARAMS.get("ma_convergence_threshold", 0.08)

# === バックテスト設定 ===

INITIAL_CAPITAL = _config.get("backtest", {}).get("initial_capital", 1000000)

# === ファイル・データ設定 ===

REQUIRED_COLUMNS = _config.get("files", {}).get("required_columns", [
    "Date", "Open", "High", "Low", "Close", "Volume", "Ticker"
])

# === ログ設定 ===

LOG_LEVEL = os.getenv("LOG_LEVEL", _config.get("files", {}).get("log_level", "INFO"))
LOG_FORMAT = _config.get("files", {}).get("log_format", 
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# === 市場固有設定 ===

MARKET_CONFIG = _config.get("market", {})
TICKER_SUFFIX = MARKET_CONFIG.get("ticker_suffix", ".T")
CURRENCY = MARKET_CONFIG.get("currency", "JPY")

# === データベース設定 (将来の拡張用) ===

DATABASE_URL = os.getenv("DATABASE_URL")

# === 開発・デバッグ設定 ===

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"

# === ログ設定辞書 (既存コードとの互換性維持) ===

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': LOG_FORMAT
        },
    },
    'handlers': {
        'default': {
            'level': LOG_LEVEL,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': str(LOG_FILE),
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


def get_config_summary() -> str:
    """設定の概要を文字列で返す（デバッグ用）"""
    summary = f"""
=== 株価スクリーニングシステム設定概要 ===
プロジェクトルート: {PROJECT_ROOT}
データディレクトリ: {DATA_DIR}
テストデータディレクトリ: {TEST_DATA_DIR}
レート制限: {RATE_LIMIT_DELAY}秒
バッチサイズ: {BATCH_SIZE}
初期投資額: {INITIAL_CAPITAL:,}円
開発モード: {DEVELOPMENT_MODE}
    """.strip()
    return summary


if __name__ == "__main__":
    # 設定のテスト実行
    import sys
    import io
    
    # 標準出力をUTF-8で設定
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print(get_config_summary())
    
    # パスの存在確認
    print(f"\n=== パス存在確認 ===")
    print(f"設定ファイル: {CONFIG_FILE.exists()}")
    print(f"環境変数ファイル: {ENV_FILE.exists()}")
    print(f"データディレクトリ: {DATA_DIR.exists()}")
    print(f"テストデータディレクトリ: {TEST_DATA_DIR.exists()}")