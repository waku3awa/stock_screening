# Portfolio Management System

株式ポートフォリオ管理システムのドキュメント

## 概要

このシステムは、保有する株式情報をCSVファイルで管理し、対話形式での銘柄登録と損益表示機能を提供します。
東証プライム市場をデフォルトとし、yfinance APIを使用して銘柄名と現在価格を取得します。

## システム構成

### ファイル構造

```
src/
  portfolio/              # ポートフォリオ管理モジュール
    __init__.py          # モジュール初期化
    models.py            # データモデル (Trade, Position)
    storage.py           # CSV永続化レイヤー
    pricing.py           # 銘柄名取得・価格取得サービス
    cli.py               # 対話形式CLIインターフェース
  portfolio_manager.py   # メインスクリプト

data/
  portfolio/             # ポートフォリオデータディレクトリ
    trades.csv           # 取引履歴 (append-only)

testing/
  test_portfolio.py      # テストスクリプト
```

### データモデル

#### Trade (取引記録)
- `trade_id`: 取引ID (UUID)
- `trade_date`: 取引日 (デフォルト: 当日 JST)
- `ticker_local`: 証券コード (例: 7203)
- `ticker_yf`: yfinanceシンボル (例: 7203.T)
- `stock_name`: 銘柄名
- `side`: BUY/SELL
- `quantity`: 数量
- `price`: 単価
- `commission`: 手数料
- `market`: 市場 (TSE/他)
- `currency`: 通貨 (JPY)
- `notes`: メモ

#### Position (保有ポジション)
- `ticker_local`: 証券コード
- `ticker_yf`: yfinanceシンボル
- `stock_name`: 銘柄名
- `quantity`: 保有数
- `avg_cost`: 平均取得単価
- `current_price`: 現在価格
- `unrealized_pnl`: 評価損益
- `unrealized_pnl_pct`: 評価損益率 (%)

## 主要機能

### 1. 銘柄登録モード (`--mode register`)

対話形式で銘柄情報を入力し、取引履歴に追加します。

**機能詳細:**
- ティッカーコード入力 → 自動で銘柄名を取得
  - 第1優先: data/data_j.xls から取得
  - フォールバック: yfinance API から取得
- 購入数量、価格、手数料の入力
- 購入日のデフォルト設定 (当日 JST)
- 任意のメモ欄
- 連続登録サポート (空欄Enterで終了)
- 登録後、入力内容の確認表示
- CSV追記保存

**使用例:**
```bash
set PYTHONIOENCODING=utf-8 && uv run python src/portfolio_manager.py --mode register
```

**対話フロー:**
```
=== 銘柄登録モード ===
対話形式で銘柄情報を登録します。
終了するには、ティッカー入力時に空欄でEnterを押してください。

ティッカーコード (例: 7203): 7203
銘柄名を取得中... (7203.T)
銘柄名: トヨタ自動車
購入数量: 100
購入価格 (円): 3000
手数料 (円, デフォルト: 0): 100
購入日 (YYYY-MM-DD, デフォルト: 2025-10-26):
メモ (任意): 初回購入

--- 登録完了 ---
取引ID: 12345678-1234-1234-1234-123456789abc
日付: 2025-10-26
銘柄: トヨタ自動車 (7203)
数量: 100
単価: 3000 円
手数料: 100 円
合計: 300100 円
メモ: 初回購入
---------------
```

### 2. 一覧表示モード (`--mode display`)

現在のポートフォリオを表示し、評価損益を計算します。

**機能詳細:**
- 保有銘柄の集計 (BUY/SELL計算)
- yfinance_cacheから現在価格取得
- 評価損益の計算と表示
- pandas DataFrameによる表形式出力
- ポートフォリオ合計の表示

**使用例:**
```bash
set PYTHONIOENCODING=utf-8 && uv run python src/portfolio_manager.py --mode display
```

**出力例:**
```
=== ポートフォリオ表示 ===

保有銘柄数: 2
現在価格を取得中...

ティッカー      銘柄名  保有数  平均取得単価      取得総額    現在価格      評価額        損益     損益率
    7203  トヨタ自動車    100  ¥3,001.00  ¥300,100  ¥3,127.00  ¥312,700  ¥+12,600  +4.20%
    6758  ソニーグループ     50 ¥12,003.00  ¥600,150  ¥4,377.00  ¥218,850 ¥-381,300 -63.53%

--- 合計 ---
取得総額: ¥900,250
評価額: ¥531,550
評価損益: ¥-368,700 (-40.95%)
-----------
```

### 3. 市場選択

デフォルトで東証プライム市場 (TSE) を使用します。

**コマンドライン引数:**
```bash
# TSE (デフォルト)
python src/portfolio_manager.py --mode register --market TSE

# その他の市場
python src/portfolio_manager.py --mode register --market NYSE
```

### 4. データパスのカスタマイズ

**コマンドライン引数:**
```bash
# データディレクトリ指定
python src/portfolio_manager.py --mode display --data-dir /path/to/data

# data_j.xlsパス指定
python src/portfolio_manager.py --mode register --data-j-xls /path/to/data_j.xls
```

## テスト

### テストスクリプトの実行

```bash
set PYTHONIOENCODING=utf-8 && uv run python testing/test_portfolio.py
```

**テスト内容:**
1. Trade作成とCSV保存
2. CSVからの取引読み込み
3. ポジション計算 (平均取得単価)
4. 銘柄名取得 (data_j.xls + yfinanceフォールバック)
5. 現在価格取得と損益計算

**テスト結果 (サンプル):**
```
============================================================
Portfolio Management System - Basic Functionality Test
============================================================

1. Testing Trade Creation and Storage
----------------------------------------
[OK] Saved: トヨタ自動車 (7203) - 100株 @ 3000円
[OK] Saved: ソニーグループ (6758) - 50株 @ 12000円

2. Testing Trade Loading
----------------------------------------
[OK] Loaded 2 trades from CSV
  - トヨタ自動車: 100株 @ 3000円 (日付: 2025-10-01)
  - ソニーグループ: 50株 @ 12000円 (日付: 2025-10-15)

3. Testing Position Calculation
----------------------------------------
[OK] Calculated 2 positions
  - トヨタ自動車 (7203)
    保有数: 100株
    平均取得単価: 3,001.00円
    取得総額: 300,100円
  - ソニーグループ (6758)
    保有数: 50株
    平均取得単価: 12,003.00円
    取得総額: 600,150円

4. Testing Stock Name Lookup
----------------------------------------
[OK] 7203 (7203.T) -> Toyota Motor Corporation
[OK] 6758 (6758.T) -> Sony Group Corporation
[OK] 9984 (9984.T) -> SoftBank Group Corp.

5. Testing Current Price Fetching
----------------------------------------
Fetching price for トヨタ自動車 (7203.T)...
[OK] Current Price: 3,127.00円
  Unrealized P&L: +12,600円 (+4.20%)
Fetching price for ソニーグループ (6758.T)...
[OK] Current Price: 4,377.00円
  Unrealized P&L: -381,300円 (-63.53%)

============================================================
Test completed successfully!
============================================================
```

## データ管理

### CSV形式

取引履歴は`data/portfolio/trades.csv`にappend-onlyで保存されます。

**CSVフォーマット:**
```csv
trade_id,trade_date,ticker_local,ticker_yf,stock_name,side,quantity,price,commission,market,currency,notes
12345678-1234-1234-1234-123456789abc,2025-10-26,7203,7203.T,トヨタ自動車,BUY,100,3000,100,TSE,JPY,初回購入
```

### ポジション計算ロジック

**平均取得単価の計算 (Simple Average Method):**
1. BUY取引: 取得総額と保有数を累積
2. SELL取引: 平均単価ベースで保有数と取得総額を削減
3. 平均取得単価 = 取得総額 / 保有数

**例:**
```
BUY  100株 @ 3000円 + 手数料100円 = 取得総額 300,100円
BUY  50株  @ 3100円 + 手数料50円  = 取得総額 155,050円
-----------------------------------------------------
保有: 150株, 取得総額: 455,150円
平均取得単価: 455,150 / 150 = 3,034.33円
```

## 依存関係

### 必須パッケージ

- `pandas>=2.3.1` - データ操作
- `yfinance-cache>=0.7.13` - 株価取得
- `python-dotenv>=1.1.1` - 環境変数管理
- `xlrd>=2.0.2` - Excelファイル読み込み

### インストール

```bash
uv add pandas yfinance-cache python-dotenv xlrd
```

## 設計上の考慮事項

### 採用した設計パターン

1. **Append-Only Transaction Log**
   - 取引履歴は追記のみ (編集・削除なし)
   - データ整合性の確保
   - 監査証跡の保持

2. **Derived Positions**
   - ポジションは取引履歴から動的に計算
   - 単一の信頼できる情報源 (Single Source of Truth)

3. **Fallback Strategy**
   - 銘柄名取得: data_j.xls → yfinance
   - 価格取得: fast_info → info → history

4. **Service Layer Pattern**
   - PortfolioStorage: CSV操作
   - StockPricingService: 市場データ取得
   - PortfolioCLI: ユーザーインターフェース

### 将来の拡張可能性

**推奨される追加機能:**
1. **売却機能** - SELL取引の登録
2. **取引編集・削除** - 間違い修正機能
3. **実現損益計算** - FIFO/LIFO/平均法対応
4. **配当管理** - 配当金の記録と表示
5. **ポートフォリオサマリー** - セクター別分析、リスク指標
6. **データベース移行** - SQLite/MySQL対応
7. **複数通貨対応** - 為替レート管理
8. **レポート出力** - PDF/Excel出力

**移行パス:**
- CSV → SQLite: データモデルはそのまま使用可能
- 単一ユーザー → マルチユーザー: アカウント管理の追加

## トラブルシューティング

### 文字エンコーディング問題

**症状:** 日本語が文字化けする

**解決策:**
```bash
# Windows CMD/PowerShell
set PYTHONIOENCODING=utf-8

# または環境変数を恒久的に設定
```

### 銘柄名が取得できない

**症状:** yfinanceから銘柄名を取得できない

**原因:**
- data_j.xlsが見つからない
- yfinance APIの制限

**解決策:**
- data_j.xlsのパスを確認
- ネットワーク接続を確認
- レート制限 (1秒待機) を遵守

### 現在価格が取得できない

**症状:** 現在価格がN/Aと表示される

**原因:**
- 市場休場日
- ティッカーシンボルの誤り
- yfinance APIエラー

**解決策:**
- ティッカーコードを確認 (TSEの場合 ".T" サフィックス)
- 市場営業日を確認
- 時間をおいて再試行

## ライセンスと著作権

このシステムは株価スクリーニングシステムの一部として開発されています。

## 関連ドキュメント

- [メインシステムドキュメント](../CLAUDE.md)
- [バックテストシステム](../src/backtest.py)
- [データ管理](../src/incremental_load_yfinance.py)
