"""
株価スクリーニングメインスクリプト

複数銘柄に対してインジケーターを適用し、シグナルを生成します。
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import pandas as pd
import yaml
from datetime import datetime, timedelta
from joblib import Parallel, delayed
import warnings
warnings.filterwarnings('ignore')

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils_parquet import get_ticker_data, get_last_business_day
from src.indicators import BargainHunterIndicator
from src.indicators.base import IndicatorResult, Signal


class StockScreener:
    """
    株価スクリーニングクラス

    複数銘柄に対してインジケーターを適用し、
    売買シグナルを生成します。
    """

    def __init__(self, config_path: str = "config.yaml", auto_download: bool=False):
        """
        スクリーナーを初期化します。

        Args:
            config_path: 設定ファイルのパス
        """
        # 設定ファイルを読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # インジケーター設定を取得
        self.indicator_config = self.config.get('indicators', {}).get('bargain_hunter', {})
        self.n_jobs = self.indicator_config.get('n_jobs', -1)

        # インジケーターを初期化
        self.indicator = BargainHunterIndicator(self.indicator_config)

        # データディレクトリを設定
        self.data_dir = Path(self.config.get('data_source', {}).get('data_dir', "./stock_data"))
        if not self.data_dir.exists():
            raise FileNotFoundError(f"データディレクトリが見つかりません: {self.data_dir}")

        self.auto_download = auto_download

    def load_ticker_list(self, excel_path: str) -> pd.DataFrame:
        """
        Excelファイルからティッカーリストを読み込みます。

        Args:
            excel_path: Excelファイルのパス

        Returns:
            pd.DataFrame: ティッカー情報
        """
        try:
            if excel_path.split(".")[-1] == "csv":
                df = pd.read_csv(excel_path)
            else:
                df = pd.read_excel(excel_path)

            # 必要なカラムのみを抽出
            if 'コード' in df.columns and '銘柄名' in df.columns:
                ticker_df = df[['コード', '銘柄名']].copy()
                ticker_df.columns = ['ticker', 'company_name']
                # ティッカーコードを文字列に変換し、.Tを追加
                ticker_df['ticker'] = ticker_df['ticker'].astype(str) + '.T'
                return ticker_df
            else:
                raise ValueError("必要なカラムが見つかりません: 'コード', '銘柄名'")
        except Exception as e:
            print(f"Excelファイルの読み込みエラー: {e}")
            raise

    def process_single_ticker(
        self,
        ticker: str,
        company_name: str,
        start_date: str,
        end_date: str
    ) -> Optional[IndicatorResult]:
        """
        単一銘柄を処理します。

        Args:
            ticker: ティッカーシンボル
            company_name: 企業名
            start_date: データ取得開始日
            end_date: データ取得終了日

        Returns:
            Optional[IndicatorResult]: 計算結果
        """
        try:
            # 株価データを取得
            price_data = get_ticker_data(
                tickers=[ticker],
                directory=str(self.data_dir),
                start_date=start_date,
                end_date=end_date,
                auto_download=self.auto_download,
            )

            if price_data is None or price_data.empty:
                print(f"データなし: {ticker} ({company_name})")
                return None

            # インジケーターでシグナルを計算
            result = self.indicator.calculate_signal(ticker, company_name, price_data)
            return result

        except Exception as e:
            print(f"エラー処理中: {ticker} ({company_name}): {e}")
            return None

    def screen_stocks(
        self,
        ticker_df: pd.DataFrame,
        days_back: int = 365
    ) -> List[IndicatorResult]:
        """
        複数銘柄をスクリーニングします。

        Args:
            ticker_df: ティッカー情報のDataFrame
            days_back: 取得する過去日数

        Returns:
            List[IndicatorResult]: スクリーニング結果
        """
        # 日付範囲を設定（営業日を考慮）
        end_date = get_last_business_day()  # 土日や祝日を避けて最新の営業日を使用
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        print(f"スクリーニング開始: {len(ticker_df)}銘柄")
        print(f"期間: {start_date} ～ {end_date}")
        print(f"並列処理: {self.n_jobs}コア使用\n")

        # 並列処理で各銘柄を処理
        results = Parallel(n_jobs=self.n_jobs, verbos=10)(
            delayed(self.process_single_ticker)(
                row['ticker'],
                row['company_name'],
                start_date,
                end_date
            )
            for _, row in ticker_df.iterrows()
        )

        # Noneを除外
        results = [r for r in results if r is not None]

        return results

    def display_results(self, results: List[IndicatorResult]) -> None:
        """
        結果を表示します。

        Args:
            results: スクリーニング結果
        """
        import unicodedata

        def get_display_width(text: str) -> int:
            """文字列の表示幅を計算（東アジア文字考慮）"""
            width = 0
            for char in text:
                if unicodedata.east_asian_width(char) in ('F', 'W'):
                    width += 2  # 全角文字
                else:
                    width += 1  # 半角文字
            return width

        def pad_string(text: str, width: int) -> str:
            """文字列を指定幅にパディング（東アジア文字考慮）"""
            current_width = get_display_width(text)
            if current_width >= width:
                return text
            padding = width - current_width
            return text + ' ' * padding

        # シグナル別に分類
        buy_signals = [r for r in results if r.signal == Signal.BUY]
        sell_signals = [r for r in results if r.signal == Signal.SELL]

        # 銘柄名の最大表示幅を計算（買いシグナルと売りシグナル両方から）
        all_signals = buy_signals + sell_signals
        if all_signals:
            max_company_name_width = max(get_display_width(r.company_name) for r in all_signals)
            # 最小幅は10文字、最大幅は40文字に制限
            company_name_width = max(10, min(max_company_name_width, 40))
        else:
            company_name_width = 20  # デフォルト値

        print("\n" + "="*80)
        print("スクリーニング結果")
        print("="*80)

        # 買いシグナル
        if buy_signals:
            print("\n【買いシグナル】")
            print("-"*80)
            header_company_name = pad_string("銘柄名", company_name_width)
            print(f"{'ティッカー':<5} {header_company_name} {'現在価格':>6} {'100株価格':>9} {'MA比率':>7} {'2日変動':>7}")
            print("-"*80)
            for result in buy_signals:
                info = result.additional_info
                padded_company_name = pad_string(result.company_name, company_name_width)
                print(f"{result.ticker:<10} {padded_company_name} "
                      f"{result.current_price:>10,.0f} {result.lot_price:>12,.0f} "
                      f"{info['price_vs_ma']:>7.1f}% {info['change_2_days']:>7.1f}%")
        else:
            print("\n【買いシグナル】なし")

        # 売りシグナル
        if sell_signals:
            print("\n【売りシグナル】")
            print("-"*80)
            header_company_name = pad_string("銘柄名", company_name_width)
            print(f"{'ティッカー':<5} {header_company_name} {'現在価格':>6} {'100株価格':>9} {'MA比率':>7} {'2日変動':>7}")
            print("-"*80)
            for result in sell_signals:
                info = result.additional_info
                padded_company_name = pad_string(result.company_name, company_name_width)
                print(f"{result.ticker:<10} {padded_company_name} "
                      f"{result.current_price:>10,.0f} {result.lot_price:>12,.0f} "
                      f"{info['price_vs_ma']:>7.1f}% {info['change_2_days']:>7.1f}%")
        else:
            print("\n【売りシグナル】なし")

        # サマリー
        print("\n" + "="*80)
        print("サマリー")
        print("="*80)
        print(f"処理銘柄数: {len(results)}")
        print(f"買いシグナル: {len(buy_signals)}銘柄")
        print(f"売りシグナル: {len(sell_signals)}銘柄")

    def save_results_to_csv(
        self,
        results: List[IndicatorResult],
        output_path: str = "screening_results.csv",
        save_full: bool = False
    ) -> None:
        """
        結果をCSVファイルに保存します。

        Args:
            results: スクリーニング結果
            output_path: 出力ファイルパス
            save_full: Trueの場合、全銘柄を保存。Falseの場合、買い・売りシグナルのみ保存
        """
        # save_fullフラグに応じて保存対象をフィルタリング
        target_results = results
        if not save_full:
            target_results = [
                r for r in results if r.signal in [Signal.BUY, Signal.SELL]
            ]
            print(f"\nシグナルあり（{len(target_results)}件）のみCSVに保存します。")
        else:
            print(f"\n全銘柄（{len(results)}件）をCSVに保存します。")

        if not target_results:
            print("保存対象のデータがありません。")
            return

        # DataFrameに変換
        data = []
        for result in target_results:
            info = result.additional_info
            data.append({
                'ティッカー': result.ticker,
                '銘柄名': result.company_name,
                'シグナル': result.signal.value,
                '現在価格': result.current_price,
                '100株価格': result.lot_price,
                '200日MA': info.get('ma_200', 0),
                'MA比率(%)': info.get('price_vs_ma', 0),
                '割高': info.get('is_overvalued', False),
                '割安': info.get('is_undervalued', False),
                '2日変動率(%)': info.get('change_2_days', 0),
                'エラー': info.get('error', '')
            })

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n結果をCSVファイルに保存しました: {output_path}")


def main():
    """メイン処理"""
    # コマンドライン引数をパース
    parser = argparse.ArgumentParser(description='株価スクリーニングシステム')
    parser.add_argument('--ticker_path', default="data/data_j_with_financials.xlsx")
    parser.add_argument('--ticker', nargs="*", type=str, default=[])
    parser.add_argument('--auto-download', action='store_true',
                      help='株価情報を自動ダウンロードする')
    parser.add_argument('--debug', action='store_true',
                      help='デバッグモード（最初の10銘柄のみ処理）')
    parser.add_argument('--limit', type=int, default=None,
                      help='処理する銘柄数の上限を指定')
    parser.add_argument('-o', '--output', type=lambda s: Path(s).expanduser(),
                      default=Path.cwd(), metavar='DIR',
                      help='結果CSVを保存するディレクトリパス（存在しない場合は自動作成、デフォルト: カレントディレクトリ）')
    parser.add_argument('--save-full', action='store_true',
                      help='全銘柄（シグナルなし含む）をCSVに保存する（デフォルト: 買い・売りシグナルのみ保存）')
    args = parser.parse_args()

    try:
        # スクリーナーを初期化
        screener = StockScreener(auto_download=args.auto_download)

        # ティッカーリストを読み込み
        print("ティッカーリストを読み込み中...")
        if args.ticker:
            print(f"対象のティッカー: {" ".join(args.ticker)}")
            data = []
            for i, t in enumerate(args.ticker):
                data.append([t, str(i)])
            ticker_df = pd.DataFrame(data, columns=["ticker", "company_name"])
            print(ticker_df)
        else:
            ticker_df = screener.load_ticker_list(args.ticker_path)

        # デバッグモードまたは上限指定の場合は銘柄数を制限
        original_count = len(ticker_df)
        if args.debug:
            ticker_df = ticker_df.head(10)
            print(f"デバッグモード: {original_count}銘柄中、最初の10銘柄のみ処理")
        elif args.limit:
            ticker_df = ticker_df.head(args.limit)
            print(f"制限モード: {original_count}銘柄中、最初の{args.limit}銘柄のみ処理")
        else:
            print(f"通常モード: 全{original_count}銘柄を処理")

        # スクリーニング実行
        results = screener.screen_stocks(ticker_df)

        # 結果を表示
        screener.display_results(results)

        # 出力ディレクトリを作成
        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSVに保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"screening_results_{timestamp}.csv"
        screener.save_results_to_csv(results, str(output_file), save_full=args.save_full)

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
