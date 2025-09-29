"""一次スクリーニングとして財務状態でスクリーニング
"""
import pandas as pd
import yfinance_cache as yfc
import time
import concurrent.futures
from utils_fa import get_latest_month_end_tse_listing

# Tickerが記録されたファイルのパス
file_path = 'data/data_j.xls'  # 使用する際は実際のパスに変更

get_latest_month_end_tse_listing(file_path)
df_tickers = pd.read_excel(file_path)

# プライム市場の銘柄のみ抽出
df_tickers = df_tickers[df_tickers["市場・商品区分"] == "プライム（内国株式）"].copy()

# 銘柄コードを整数型に変換（先頭ゼロ落ち防止）
df_tickers["コード"] = df_tickers["コード"].astype(str).str.zfill(4)
ticker_list = df_tickers["コード"].astype(str) + ".T"

def fetch_financial_data(ticker, index, total):
    stock = yfc.Ticker(ticker)
    try:
        time.sleep(3)  # 3秒の待機（アクセス制限回避）
        info = stock.info
        roe = info.get("returnOnEquity", None) * 100 if info.get("returnOnEquity") is not None else None
        per = info.get("trailingPE", None)
        opm = info.get("operatingMargins", None) * 100 if info.get("operatingMargins") is not None else None

        return {
            "Ticker": ticker,
            "ROE": roe,
            "PER": per,
            "営業利益率": opm
        }
    except Exception as e:
        print(f"{ticker} の処理中にエラー: {e}")
    finally:
        progress = (index + 1) / total * 100  # 進行状況の表示
        print(f"データ取得中: {ticker} ({index + 1}/{total} - {progress:.2f}%)")
    return None

all_financial_data = []
# ThreadPoolExecutorを使ってticker_listを並列処理
total_tickers = len(ticker_list)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(fetch_financial_data, ticker, i, total_tickers) for i, ticker in enumerate(ticker_list)]

    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if result:
            all_financial_data.append(result)

df_financials = pd.DataFrame(all_financial_data)
# 'Ticker'列の".T"サフィックスを削除してdf_tickersの形式に合わせる
df_financials['Ticker'] = df_financials['Ticker'].astype(str).str.replace('.T', '', regex=False)
# df_tickersとdf_financialsを銘柄コードでマージ（左外部結合）
df_merged_data = pd.merge(df_tickers, df_financials, left_on='コード', right_on='Ticker', how='left')
# 重複する'Ticker'列を削除
df_merged_data = df_merged_data.drop('Ticker', axis=1)

# 結果をCSVとして保存
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_filename = f"{timestamp}_data_j_financial.csv"
df_merged_data.to_csv(output_filename, index=False, encoding='utf-8-sig')
print(f"財務データを保存しました: {output_filename}")
print(f"保存レコード数: {len(df_merged_data)}")
print(f"財務データ取得成功: {len(all_financial_data)}銘柄")
