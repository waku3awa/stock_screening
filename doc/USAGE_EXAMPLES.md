# incremental_load_yfinance.py 使用例

更新された `incremental_load_yfinance.py` は、コマンドライン引数でExcelファイルパスと株価データ保存ディレクトリを指定できるようになりました。

## 基本的な使用方法

### 1. ヘルプの表示
```bash
uv run python src/incremental_load_yfinance.py --help
```

### 2. 基本的な実行
```bash
# 最小構成（必須引数のみ）
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data
```

### 3. ドライラン（実行時間の見積もり）
```bash
# 実際にダウンロードせずに、更新が必要なファイル数と所要時間を確認
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --dry-run
```

## 高度な使用例

### 4. カスタム設定での実行
```bash
# より詳細な設定
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --input-dir ./existing_stock_data \
    --delay 2.0 \
    --lookback 60 \
    --batch-size 100 \
    --log-level DEBUG
```

### 5. バッチファイル再構築なしでの実行
```bash
# 個別ファイルの更新のみ（バッチファイルやマスターファイルは更新しない）
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --no-rebuild
```

### 6. テストデータでの動作確認
```bash
# 34社のテストデータを使用（作成済みの場合）
uv run python src/incremental_load_yfinance.py \
    --excel-path ./test_data_selected_companies.xlsx \
    --output-dir ./test_stock_data \
    --delay 1.5 \
    --log-level INFO
```

## パラメータ説明

### 必須パラメータ
- `-e, --excel-path`: 銘柄リストが含まれるExcelファイルのパス
- `-o, --output-dir`: 株価データファイルの保存先ディレクトリ

### オプションパラメータ
- `-i, --input-dir`: 既存の株価データを読み込むディレクトリ（未指定時は output-dir と同じ）
- `--delay`: yfinanceリクエスト間の待機時間（秒、デフォルト: 1.0）
- `--lookback`: 更新確認の最大日数（デフォルト: 30日）
- `--batch-size`: バッチファイル作成時のファイル数（デフォルト: 200）
- `--dry-run`: 実際のダウンロードなしで実行時間を見積もり
- `--no-rebuild`: バッチファイルとマスターファイルの再構築をスキップ
- `--log-level`: ログレベル（DEBUG, INFO, WARNING, ERROR）

## 実行例とその用途

### シーン1: 初回実行（新規データセット作成）
```bash
# 全銘柄の株価データを新規作成
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --delay 1.0 \
    --log-level INFO
```

### シーン2: 日次更新
```bash
# 既存データの差分更新
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --delay 1.0
```

### シーン3: 障害復旧（長期間の差分）
```bash
# より長い期間の差分を許可
uv run python src/incremental_load_yfinance.py \
    --excel-path ./data/data_j_with_financials.xlsx \
    --output-dir ./stock_data \
    --lookback 90 \
    --delay 2.0 \
    --log-level DEBUG
```

### シーン4: 開発・テスト環境
```bash
# テストデータで少数銘柄のみ処理
uv run python src/incremental_load_yfinance.py \
    --excel-path ./test_data_selected_companies.xlsx \
    --output-dir ./test_stock_data \
    --delay 1.5
```

## 出力ファイル構造

実行後、以下の構造でファイルが作成されます：

```
stock_data/
├── raw/                        # 個別銘柄のparquetファイル
│   ├── 1301.T_OHLCV.parquet   # トヨタ自動車
│   ├── 7203.T_OHLCV.parquet   # 個別銘柄データ
│   └── ...
├── batch_size/                 # バッチ処理されたファイル
│   ├── batch_0.parquet
│   ├── batch_1.parquet
│   └── ...
└── ticker_combined_OHLCV.parquet  # 全銘柄統合マスターファイル
```

## エラーハンドリング

### 一般的なエラーと対処法

1. **Excel file not found**
   - ファイルパスが正しいか確認
   - 相対パスではなく絶対パスを使用

2. **Permission denied**
   - 出力ディレクトリの書き込み権限を確認
   - 既存ファイルが他のプロセスで使用されていないか確認

3. **Rate limiting errors**
   - `--delay` パラメータを大きくする（2.0以上推奨）
   - 一時的にAPIアクセスを制限されている可能性

4. **Memory errors**
   - `--batch-size` を小さくする（100など）
   - システムのメモリ使用量を確認

## パフォーマンス最適化

### 高速化のコツ
- `--delay` を最小限に（1.0秒推奨、エラー時は増加）
- `--no-rebuild` で個別更新のみ実行し、別途バッチ処理
- `--lookback` を適切な値に設定（通常は30日で十分）

### 大量データ処理時
- `--batch-size` を調整してメモリ使用量を制御
- `--log-level WARNING` でログ出力を削減
- 定期的なディスク容量確認

## 自動化スクリプト例

日次実行用のバッチファイル（Windows）：
```batch
@echo off
cd /d "C:\path\to\stock_screening\feature-cleanup"
uv run python src/incremental_load_yfinance.py ^
    --excel-path ./data/data_j_with_financials.xlsx ^
    --output-dir ./stock_data ^
    --delay 1.0 ^
    --log-level INFO
if %ERRORLEVEL% NEQ 0 (
    echo "Error occurred during stock data update"
    exit /b %ERRORLEVEL%
)
echo "Stock data update completed successfully"
```

これで、柔軟性と使いやすさを兼ね備えた株価データ更新システムが完成しました。