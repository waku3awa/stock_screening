# 株式投資スクリーニングシステム設計仕様書

## 1. システム概要

### 1.1 目的
7つの連載記事で紹介された株式投資スクリーニング手法を統合し、月利3〜5%を目指す自動化された投資支援システムを構築する。

### 1.2 システム進化の段階
```
【初期段階】→【改善段階】→【成熟段階】
都度処理     ローカル最適化  データベース基盤
CSV出力     Parquet活用    MySQL中心設計
```

## 2. 全体アーキテクチャ

### 2.1 システム構成
```
┌─────────────────────────────────┐
│        Presentation Layer       │
│  - Web UI / CLI                 │
│  - レポート出力                  │
│  - アラート通知                  │
├─────────────────────────────────┤
│        Business Logic Layer     │
│  - スクリーニングエンジン         │
│  - テクニカル分析                │
│  - 相場スコア計算                │
│  - バックテスト機能              │
├─────────────────────────────────┤
│        Data Access Layer        │
│  - MySQL データベース            │
│  - yfinance API                 │
│  - Parquet ローカルキャッシュ     │
├─────────────────────────────────┤
│        Infrastructure Layer     │
│  - タスクスケジューラ             │
│  - ログ管理                      │  
│  - 監視・アラート                │
└─────────────────────────────────┘
```

### 2.2 データフロー
```
外部データ取得 → ローカルキャッシュ → 指標計算 → スクリーニング → 結果蓄積 → 分析・可視化
     ↓              ↓              ↓           ↓           ↓           ↓
  yfinance API   Parquet Files   Technical   Screening   MySQL DB   Web Reports
                                 Indicators   Results
```

## 3. スクリーニング手法体系

### 3.1 1次スクリーニング（財務指標フィルタリング）
**目的**: 約2,000銘柄から財務的に健全な企業を選別

**処理内容**:
1次スクリーニングは膨大な銘柄数から投資対象を効率的に絞り込む最初のフィルターです。財務指標による定量的な判定により、以下の特徴を持つ企業を自動選別します：
- **収益性**: ROEにより株主資本に対する利益効率を評価
- **割安性**: PERにより株価の割安度を判定
- **事業効率**: 営業利益率により本業の収益力を測定

この段階では「利益を出せていて、割安で、体質が強い企業」という基本条件をクリアした銘柄のみを通過させ、後続のテクニカル分析の対象を大幅に絞り込みます。

**条件**:
- ROE > 10%
- PER < 15
- 営業利益率 > 10%

**実装**:
```python
def primary_screening(df):
    return df[
        (df['ROE'] > 0.10) &
        (df['PER'] < 15) &
        (df['OperatingMargin'] > 0.10)
    ]
```

### 3.2 テクニカル分析スクリーニング
**目的**: チャートパターンによる投資タイミングの特定

**処理内容**:
テクニカル分析スクリーニングは、1次スクリーニングを通過した財務的に健全な銘柄に対して、株価チャートのテクニカル指標を用いて投資タイミングを判定します。複数の指標を組み合わせることで以下を実現します：

- **RSI判定**: 買われすぎ・売られすぎの状況を回避し、適切な価格レンジの銘柄を選別
- **トレンド分析**: 複数期間の移動平均線により、短期・中期・長期のトレンド方向を総合判定
- **収束パターン検出**: 移動平均線の収束により、トレンド転換の可能性が高い銘柄を特定
- **モメンタム評価**: 短期トレンドの傾きにより、上昇初期段階の銘柄を捕捉

この手法により月利3-5%を狙える銘柄を系統的に発見し、手作業では困難な大量銘柄の同時分析を自動化します。

**指標**:
- RSI（14日、25-75範囲）
- 移動平均線（MA5/25/75）
- 移動平均収束判定（±2%以内、バックテストの結果、戦略の柔軟性を考慮し8%を採用（より多くの銘柄を捕捉可能））
- 短期トレンド傾き

**実装**:
```python
def technical_screening(df):
    # RSI計算（14日、25-75範囲）
    df['RSI'] = calculate_rsi(df['Close'], 14)
    
    # 移動平均線（MA5/25/75）
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA25'] = df['Close'].rolling(25).mean()
    df['MA75'] = df['Close'].rolling(75).mean()
    
    # 短期トレンド傾き（MA5がMA25を上回る = 上昇トレンド）
    upward_trend = df['MA5'] > df['MA25']
    
    # 移動平均収束判定（±2%～8%の範囲で調整可能、ここでは8%を使用）
    ma_convergence = abs(df['Close'] - df['MA25']) / df['MA25'] <= 0.08
    
    # スクリーニング条件（全指標の組み合わせ）
    return df[
        (df['RSI'] >= 25) & (df['RSI'] <= 75) &  # RSI範囲判定
        ma_convergence &                          # 移動平均収束判定
        upward_trend                             # 短期トレンド傾き
    ]
```

### 3.3 相場スコア判定
**目的**: 市場の「勢い・位置・心理」を定量化

**処理内容**:
相場スコア判定は、個別銘柄のスクリーニングを実行する前に市場全体の状況を客観的に評価するシステムです。TOPIX（東証株価指数）を基準として、市場の3つの側面を総合的に分析します：

- **勢い（Momentum）**: 短期的な価格変動により市場参加者の積極性を測定
- **位置（Position）**: 中期トレンドからの乖離により市場の過熱・冷却度を判定  
- **心理（Psychology）**: RSI指標により市場全体の投資家心理を数値化

-3から+3の7段階スコアにより、スクリーニング戦略の有効性を事前判定し、市場環境に応じた柔軟な投資判断を可能にします。特に相場スコアが-1から0の弱気～中立局面で最も効果的な成果を示すことが実証されています。

**構成要素**:
1. **勢い（R₅）**: 5日リターン
   - +1点: R₅ > 1%
   - -1点: R₅ < -1%

2. **位置（D₂₅）**: 25日移動平均乖離
   - +1点: D₂₅ > 0
   - -1点: D₂₅ < 0

3. **心理（RSI₁₄）**: 14日RSI
   - +1点: RSI > 55
   - -1点: RSI < 45

**スコア範囲**: -3 ～ +3

**実装**:
```python
def calculate_market_score(df):
    # TOPIX (1306.T) データを使用
    r5 = (df['Close'] / df['Close'].shift(5) - 1) * 100
    d25 = (df['Close'] / df['Close'].rolling(25).mean() - 1) * 100
    rsi14 = calculate_rsi(df['Close'], 14)
    
    score = 0
    score += 1 if r5.iloc[-1] > 1 else (-1 if r5.iloc[-1] < -1 else 0)
    score += 1 if d25.iloc[-1] > 0 else (-1 if d25.iloc[-1] < 0 else 0)
    score += 1 if rsi14.iloc[-1] > 55 else (-1 if rsi14.iloc[-1] < 45 else 0)
    
    return score
```

## 4. データモデル設計

### 4.1 データモデル全体設計

#### 設計思想と基本原則
株式スクリーニングシステムのデータモデルは、金融時系列データの特性を考慮した正規化設計を採用しています。リレーショナルデータベース（MySQL）による厳密なデータ整合性と、大容量時系列データの効率的な管理を両立する設計となっています。

#### データ構造の階層関係
```
┌─────────────────┐
│   securities    │ ← 銘柄マスタ（基準テーブル）
│   (銘柄情報)    │
└─────┬───────────┘
      │ 1:N
      ▼
┌─────────────────┐    ┌──────────────────┐
│  daily_prices   │    │ technical_indicators │
│  (日次株価)     │    │ (テクニカル指標)      │
└─────┬───────────┘    └──────────┬───────────┘
      │ 1:N                      │ 1:N
      │                          │
      ▼                          ▼
┌─────────────────┐    ┌──────────────────┐
│screening_results│    │   market_scores    │
│(スクリーニング) │    │   (相場スコア)     │
└─────────────────┘    └──────────────────┘
```

#### 正規化レベルと設計判断
**第3正規形を基本とした設計**:
- **銘柄マスタの分離**: 静的な銘柄情報を独立管理
- **時系列データの最適化**: 日次データは日付を複合キーとして高速アクセス
- **計算結果の事前保存**: テクニカル指標は計算コスト削減のため非正規化

#### データ統合の考え方
**マスタデータ中心設計**:
```sql
-- 全テーブルがsecuritiesを基点とする外部キー制約
securities (ticker) ←┐
                     ├─ daily_prices (ticker)
                     ├─ technical_indicators (ticker)
                     └─ screening_results (ticker)
```

**時系列データの管理方針**:
- **日付の統一**: 全時系列データで共通の日付形式（DATE型）
- **欠損データ対応**: NULL許可により不完全データでも柔軟に対応
- **履歴保持**: 過去データを完全保存し、長期的なトレンド分析を可能に

#### パフォーマンス設計の重点項目

**1. インデックス戦略**
```sql
-- 時系列アクセスパターンに最適化
INDEX (ticker, date)  -- 銘柄別時系列検索
INDEX (date, ticker)  -- 日付別一括検索
INDEX (date)          -- 期間指定検索
```

**2. パーティショニング戦略**
```sql
-- 年別パーティション分割
PARTITION BY RANGE (YEAR(date))
-- 古いデータへのアクセス負荷軽減
-- バックアップとメンテナンスの効率化
```

**3. データ型の最適化**
```sql
-- 数値精度と格納効率のバランス
DECIMAL(10,2)  -- 株価（小数点2桁精度）
DECIMAL(5,2)   -- RSI等の指標（範囲が限定的）
DECIMAL(6,2)   -- リターン率（±999.99%対応）
```

#### データ品質管理

**制約による品質保証**:
- **主キー制約**: データの一意性確保
- **外部キー制約**: 参照整合性維持
- **NOT NULL制約**: 必須データの保証
- **CHECK制約**: 値の妥当性検証

**データ更新の追跡**:
```sql
-- 全テーブルに標準装備
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

#### 拡張性への配慮

**新指標の追加容易性**:
- テクニカル指標テーブルへのカラム追加による対応
- ALTER TABLE操作で既存データに影響なし

**新戦略の対応**:
- screening_resultsのpatternカラムによる戦略識別
- 新戦略追加時もテーブル構造変更不要

**外部データ連携**:
- ティッカーシンボルによる標準化された銘柄識別
- 証券会社APIや他システムとの連携基盤

#### データモデルの利点

**1. 保守性**
- 正規化による冗長性排除
- 一元的なマスタデータ管理
- 明確な責任分界

**2. 拡張性**
- 新テーブル追加の容易性
- 既存構造への影響最小化
- バージョンアップ対応

**3. パフォーマンス**
- 適切なインデックス配置
- 時系列データ最適化
- 大容量データ対応

**4. 分析適合性**
- スクリーニング処理に最適化
- バックテスト分析支援
- 長期データ蓄積対応

### 4.2 核心テーブル設計

#### securities（銘柄マスタ）
**テーブルの役割**:
銘柄マスタテーブルは、システムで扱う全ての株式銘柄の基本情報を一元管理する重要な基盤テーブルです。ティッカーシンボルを主キーとして各銘柄を一意に識別し、企業名、上場市場区分、業種・業界分類などの静的な属性情報を保持します。他の全てのテーブルから参照される中核的なマスタデータとして、データの整合性と正規化を実現します。

**設計のポイント**:
- **主キー**: ticker（ティッカーシンボル）による一意性確保
- **市場区分**: ENUMによる値の制約と整合性維持
- **タイムスタンプ**: created_at/updated_atによる変更履歴管理
- **参照整合性**: 外部キー制約により他テーブルとの整合性を保証

```sql
CREATE TABLE securities (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    market_segment ENUM('Prime', 'Standard', 'Growth') NOT NULL,
    sector VARCHAR(50),
    industry VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### daily_prices（日次株価データ）
**テーブルの役割**:
日次株価テーブルは、各銘柄の日々の取引データ（OHLCV）を時系列で蓄積する大容量データテーブルです。株価の始値・高値・安値・終値と出来高を日付別に記録し、テクニカル分析の基礎データとして機能します。調整後終値（adj_close）により株式分割や配当の影響を除去した正確な価格推移を提供し、長期的なトレンド分析を可能にします。

**設計のポイント**:
- **複合主キー**: ticker + price_dateによる一意性確保
- **外部キー制約**: securitiesテーブルとの参照整合性維持
- **複合インデックス**: ticker + price_dateによる高速検索
- **パーティショニング**: 年別分割による大容量データ対応
- **数値精度**: DECIMAL型による正確な価格表現

```sql
CREATE TABLE daily_prices (
    ticker VARCHAR(10),
    price_date DATE,
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    adj_close DECIMAL(10,2),
    PRIMARY KEY (ticker, price_date),
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    INDEX idx_ticker_date (ticker, price_date),
    INDEX idx_date (price_date)
);
```

#### technical_indicators（テクニカル指標）
**テーブルの役割**:
テクニカル指標テーブルは、日次株価データから計算される各種テクニカル分析指標を銘柄・日付別に保存する計算結果保管テーブルです。移動平均線、RSI、ボリンジャーバンド、MACDなどの指標値を事前計算して蓄積することで、スクリーニング処理時の高速アクセスを実現します。指標の再計算コストを削減し、複数の分析処理で共通利用できる効率的な設計です。

**設計のポイント**:
- **複合主キー**: ticker + indicator_dateによる一意性確保
- **指標別カラム**: 各テクニカル指標を専用カラムで管理
- **高精度数値**: RSIは小数点2桁、MACDは4桁で精密な計算結果を保持
- **NULL値許可**: 計算に必要な期間のデータが不足する場合の柔軟性
- **インデックス最適化**: 日付範囲検索とソート処理の高速化

```sql
CREATE TABLE technical_indicators (
    ticker VARCHAR(10),
    indicator_date DATE,
    ma5 DECIMAL(10,2),
    ma25 DECIMAL(10,2),
    ma75 DECIMAL(10,2),
    rsi14 DECIMAL(5,2),
    rsi_period14 DECIMAL(5,2),
    bollinger_upper DECIMAL(10,2),
    bollinger_lower DECIMAL(10,2),
    macd DECIMAL(10,4),
    macd_signal DECIMAL(10,4),
    PRIMARY KEY (ticker, indicator_date),
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    INDEX idx_ticker_date (ticker, indicator_date)
);
```

#### screening_results（スクリーニング結果）
**テーブルの役割**:
スクリーニング結果テーブルは、各種戦略による銘柄選定結果とその後のパフォーマンスを記録する分析結果蓄積テーブルです。スクリーニングを実行した日付、選定された銘柄、適用された戦略パターン、その時点での指標値、および30/60/90日後のリターンを一元管理します。戦略の有効性検証とバックテスト分析の基盤データとして機能する重要なテーブルです。

**設計のポイント**:
- **複合主キー**: screening_date + ticker + patternによる一意性確保
- **戦略識別**: patternカラムによる多様なスクリーニング戦略の区別
- **リターン追跡**: 複数期間のリターンによる戦略効果の定量評価
- **市場環境記録**: market_scoreによる市場状況との関連分析
- **多重インデックス**: 日付・銘柄・パターン・スコア別の高速検索

```sql
CREATE TABLE screening_results (
    screening_date DATE,
    ticker VARCHAR(10),
    pattern VARCHAR(50),
    close_price DECIMAL(10,2) NOT NULL,
    ma5 DECIMAL(10,2),
    ma25 DECIMAL(10,2),
    rsi DECIMAL(5,2),
    per_ratio DECIMAL(8,2),
    roe DECIMAL(5,2),
    market_score INT,
    return_30d DECIMAL(6,2),
    return_60d DECIMAL(6,2),
    return_90d DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (screening_date, ticker, pattern),
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    INDEX idx_screening_date (screening_date),
    INDEX idx_ticker (ticker),
    INDEX idx_pattern (pattern),
    INDEX idx_market_score (market_score)
);
```

#### market_scores（相場スコア履歴）
**テーブルの役割**:
相場スコア履歴テーブルは、市場全体の状況を定量化した相場スコアとその構成要素を日別に記録する市場分析テーブルです。TOPIX指数から算出された勢い・位置・心理の3要素と統合スコアを保存し、スクリーニング戦略の実行判断と効果分析の基準として活用されます。市場環境の変化を追跡し、戦略の有効性を市場状況別に評価するための重要な参照データです。

**設計のポイント**:
- **主キー**: score_date（日付）による時系列データ管理
- **要素分解**: 勢い・位置・心理の各要素を個別記録
- **計算値保持**: R5リターン、D25乖離、RSI14値の詳細データ
- **統合評価**: total_scoreによる市場状況の一元的判定
- **検索最適化**: スコア値と日付による効率的なフィルタリング

```sql
CREATE TABLE market_scores (
    score_date DATE PRIMARY KEY,
    r5_return DECIMAL(6,2),
    d25_deviation DECIMAL(6,2),
    rsi14_value DECIMAL(5,2),
    momentum_score INT,
    position_score INT,
    psychology_score INT,
    total_score INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_total_score (total_score),
    INDEX idx_score_date (score_date)
);
```

### 4.2 パフォーマンス最適化設計

#### インデックス戦略
**最適化の目的**:
インデックス戦略とパーティショニングは、大容量の時系列データに対する高速クエリとスケーラブルなデータ管理を実現するためのパフォーマンス最適化手法です。複合インデックスにより多条件検索を高速化し、年別パーティショニングにより古いデータへのアクセス負荷を軽減します。

**設計の効果**:
- **複合インデックス**: 複数条件での絞り込み検索を1つのインデックスで効率化
- **選択度の高い順序**: より絞り込み効果の高いカラムを先頭に配置
- **パーティション分割**: 年度別分割により検索範囲を物理的に限定
- **クエリプランナ最適化**: MySQLオプティマイザによる最適な実行計画選択

```sql
-- 複合インデックス（クエリパフォーマンス向上）
CREATE INDEX idx_screening_date_score ON screening_results(screening_date, market_score);
CREATE INDEX idx_ticker_pattern_date ON screening_results(ticker, pattern, screening_date);

-- パーティショニング（大容量データ対応）
ALTER TABLE daily_prices PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

## 5. 技術実装パターン

### 5.1 データ取得最適化パターン

#### キャッシュ戦略
**処理内容**:
データキャッシュシステムは、外部API（yfinance）への過度なアクセスを防ぎ、処理速度を劇的に向上させる仕組みです。初回取得時にParquet形式でローカル保存し、以降のアクセスではキャッシュファイルから高速読み込みを実行します。ファイル存在チェック→キャッシュ読み込み→データ提供の流れにより、ネットワーク遅延とAPI制限を回避しつつ、分析処理のレスポンス性を大幅に改善します。
```python
import os
import pandas as pd
from pathlib import Path

class DataCache:
    def __init__(self, cache_dir='./data/cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cached_data(self, ticker, start_date, end_date):
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.parquet"
        if cache_file.exists():
            return pd.read_parquet(cache_file)
        return None
    
    def save_to_cache(self, data, ticker, start_date, end_date):
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.parquet"
        data.to_parquet(cache_file)
```

#### 増分更新パターン
**処理内容**:
増分更新システムは、既存のキャッシュデータを活用して必要最小限のデータのみを新規取得する効率化手法です。最新キャッシュの最終日付を確認し、その翌日以降のデータのみをAPI経由で取得して既存データに追加結合します。これにより初回の全期間取得後は日次の少量データ更新のみで最新状態を維持でき、処理時間とAPI使用量を大幅に削減します。
```python
def incremental_data_update(ticker, cache):
    # 最新キャッシュデータの確認
    cached_data = cache.get_latest_data(ticker)
    
    if cached_data is not None:
        last_date = cached_data.index.max()
        new_data = yf.download(ticker, start=last_date + pd.Timedelta(days=1))
        if not new_data.empty:
            updated_data = pd.concat([cached_data, new_data])
        else:
            updated_data = cached_data
    else:
        updated_data = yf.download(ticker, start='2020-01-01')
    
    cache.save_data(ticker, updated_data)
    return updated_data
```

### 5.2 並列処理パターン

#### 銘柄別並列スクリーニング
**処理内容**:
並列スクリーニングシステムは、数百から数千の銘柄を同時並行で処理することにより、スクリーニング実行時間を大幅に短縮する仕組みです。ThreadPoolExecutorを使用してワーカースレッドを管理し、各銘柄のスクリーニング処理を独立したタスクとして並行実行します。エラーハンドリングにより個別銘柄の処理失敗が全体に影響しないよう配慮し、大規模データ処理でも安定した動作を実現します。
```python
import concurrent.futures
from typing import List, Dict

def parallel_screening(tickers: List[str], screening_func, max_workers=10):
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(screening_func, ticker): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as exc:
                print(f'{ticker} generated an exception: {exc}')
    
    return results
```

### 5.3 設定駆動パターン

#### スクリーニング条件の外部化
**処理内容**:
設定駆動システムは、スクリーニング条件をYAMLファイルに外部化することで、プログラムの再起動やコード変更なしに戦略パラメータを動的に調整可能にします。市場環境の変化や戦略の改善に応じて、閾値や条件を即座に変更でき、複数の戦略設定を管理できます。設定ファイルの階層構造により、戦略タイプ別の整理と拡張性を確保し、運用の柔軟性を最大化します。
```python
# config/screening_config.yaml
screening_strategies:
  primary_financial:
    roe_min: 0.10
    per_max: 15
    operating_margin_min: 0.10
  
  technical_rsi:
    rsi_min: 25
    rsi_max: 75
    ma_deviation_max: 0.08
    
  market_conditions:
    bullish_score_min: 2
    bearish_score_max: -1

# 設定読み込みクラス
class ScreeningConfig:
    def __init__(self, config_path='config/screening_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def get_strategy_config(self, strategy_name):
        return self.config['screening_strategies'][strategy_name]
```

## 6. システム処理フロー

### 6.1 日次バッチ処理フロー
**処理内容**:
日次バッチ処理は、システムの中核となる自動化されたデータ更新・分析プロセスです。市場の営業終了後に実行され、相場環境の評価から始まり、株価データの更新、テクニカル指標の計算、スクリーニングの実行、結果の蓄積、パフォーマンス評価、レポート生成まで一連の処理を順次実行します。各ステップの依存関係を考慮した設計により、エラー発生時の復旧性と処理の信頼性を確保しています。
```python
def daily_batch_process():
    # 1. 相場スコア更新
    market_score = calculate_market_score()
    save_market_score(market_score)
    
    # 2. 株価データ増分更新
    tickers = get_active_tickers()
    update_price_data(tickers)
    
    # 3. テクニカル指標計算
    calculate_technical_indicators(tickers)
    
    # 4. スクリーニング実行
    screening_results = execute_screening_strategies(tickers, market_score)
    
    # 5. 結果保存
    save_screening_results(screening_results)
    
    # 6. パフォーマンス更新（過去データのリターン計算）
    update_historical_returns()
    
    # 7. レポート生成・通知
    generate_daily_report()
    send_notifications()
```

### 6.2 リアルタイム監視フロー
**処理内容**:
リアルタイム監視システムは、市場時間中の急激な環境変化を捕捉し、重要な状況変化を即座に通知する機能です。5分間隔で相場スコアの変動を監視し、スコアが2ポイント以上変動した場合や注目銘柄に異常が発生した場合にアラートを発行します。無限ループによる継続監視とエラー回復機能により、市場の重要な転換点を見逃すことなく投資判断をサポートします。
```python
def realtime_monitoring():
    while True:
        try:
            # 市場状況監視
            current_score = get_current_market_score()
            
            # アラート条件チェック
            if abs(current_score - previous_score) >= 2:
                send_alert(f"Market score changed significantly: {current_score}")
            
            # 注目銘柄の状況監視
            monitor_watchlist_stocks()
            
            time.sleep(300)  # 5分間隔
            
        except Exception as e:
            log_error(f"Monitoring error: {e}")
            time.sleep(60)
```

## 7. 運用・保守設計

### 7.1 監視項目
**処理内容**:
システム監視は、データの鮮度、処理の実行状況、リソース使用量を常時追跡し、サービス品質を維持するための仕組みです。各メトリクスに対して警告レベルを設定し、閾値を超過した場合に自動アラートを発行します。データ更新の遅延、スクリーニング処理の失敗、ストレージ容量の逼迫など、システム運用上の問題を早期発見し、サービス停止を未然に防ぎます。
```python
# システム監視指標
MONITORING_METRICS = {
    'data_freshness': {
        'metric': 'hours_since_last_update',
        'threshold': 24,
        'alert_level': 'warning'
    },
    'screening_execution': {
        'metric': 'daily_screening_count',
        'threshold': 1,
        'alert_level': 'critical'
    },
    'database_size': {
        'metric': 'gb_used',
        'threshold': 100,
        'alert_level': 'warning'
    }
}
```

### 7.2 ログ管理
**処理内容**:
構造化ログシステムは、システムの動作状況を詳細に記録し、問題発生時の迅速な原因特定を可能にします。JSON形式での統一ログ出力により、ログ解析ツールでの効率的な検索・集計が可能となります。タイムスタンプ、ログレベル、モジュール名、メッセージ、関数名を標準フィールドとして記録し、運用担当者による障害対応とシステム改善をサポートします。
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(self.JsonFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'module': record.module,
                'message': record.getMessage(),
                'function': record.funcName
            }
            return json.dumps(log_entry)
```

### 7.3 バックアップ戦略
**処理内容**:
自動バックアップシステムは、重要なスクリーニング結果データを定期的に保護し、データ損失リスクを最小化します。MySQLのイベントスケジューラを活用して、毎日決まった時間に直近30日分のデータをバックアップテーブルとして作成します。同時に90日以上経過した古いバックアップは自動削除し、ストレージ容量の効率的な管理を実現します。障害発生時の迅速なデータ復旧を可能にする重要な保護機能です。
```sql
-- 日次バックアップ
CREATE EVENT daily_backup
ON SCHEDULE EVERY 1 DAY
STARTS '2025-01-01 02:00:00'
DO
BEGIN
    -- スクリーニング結果のバックアップ
    CREATE TABLE screening_results_backup_`date +%Y%m%d`
    AS SELECT * FROM screening_results 
    WHERE screening_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
    
    -- 古い バックアップファイルの削除（90日以上）
    SET @sql = CONCAT('DROP TABLE IF EXISTS screening_results_backup_', 
                     DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 90 DAY), '%Y%m%d'));
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END;
```

## 8. パフォーマンス要件

### 8.1 処理時間目標
- 日次バッチ処理: 30分以内
- リアルタイム相場スコア更新: 5分以内
- スクリーニング結果照会: 3秒以内
- 過去データ分析: 10秒以内

### 8.2 拡張性設計
**処理内容**:
プラグイン式戦略システムは、新しいスクリーニング手法を既存システムに影響を与えることなく追加できる柔軟な設計です。抽象基底クラスとして戦略インターフェースを定義し、具体的な戦略を個別クラスとして実装します。戦略レジストリによる動的な戦略選択により、運用中の戦略切り替えやA/Bテストが可能となり、市場環境の変化に応じた迅速な戦略対応を実現します。
```python
# プラグイン式戦略設計
class ScreeningStrategy:
    def __init__(self, name):
        self.name = name
    
    def screen(self, data, config):
        raise NotImplementedError

class RSIStrategy(ScreeningStrategy):
    def screen(self, data, config):
        rsi = calculate_rsi(data['Close'])
        return data[
            (rsi >= config['rsi_min']) & 
            (rsi <= config['rsi_max'])
        ]

# 戦略レジストリ
strategy_registry = {
    'rsi': RSIStrategy,
    'moving_average': MovingAverageStrategy,
    'bollinger_bands': BollingerBandsStrategy
}
```

## 9. セキュリティ・コンプライアンス

### 9.1 データ保護
- 個人投資情報の暗号化
- アクセスログの記録
- 定期的なセキュリティ監査

### 9.2 金融データ利用規約遵守
- Yahoo Finance API利用規約の遵守
- データ二次利用制限の実装
- レート制限の実装

## 10. 今後の拡張計画

### 10.1 高度な分析機能
- 機械学習モデルの導入（PCA、ランダムフォレスト）
- 非線形特徴量の活用
- アンサンブル学習による予測精度向上

### 10.2 ユーザーインターフェース
- Webダッシュボードの開発
- モバイルアプリ対応
- カスタムアラート機能

### 10.3 外部システム連携
- 証券会社API連携
- ポートフォリオ管理システム連携
- 税務申告支援機能

---

この設計仕様書は、7つの連載記事で紹介された手法を体系化し、実用的な投資支援システムの構築指針を示しています。段階的な改善アプローチを重視し、拡張性と保守性を確保した設計となっています。