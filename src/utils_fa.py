# download_xls_robust.py
import requests
from requests.adapters import HTTPAdapter, Retry
import os


# ここから、エクセルファイルをダウンロードする ---------------------------------------------------------
# ストリーミング方式で少しずつ保存 → メモリ効率が良い（大容量ファイルもOK）
# Retry を設定 → ネットワークの一時的な失敗を自動でリトライ
# .part 一時ファイルに書き込み → ダウンロードが成功した時だけ本ファイルに置き換える（壊れたファイル防止）
# Content-Length が分かれば進捗バー（%表示）も可能
URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
CHUNK_SIZE = 8192  # 8 KB

def get_latest_month_end_tse_listing(output_path):
    download_stream(URL, output_path, show_progress=True)


def create_session(retries=3, backoff_factor=0.3, status_forcelist=(500,502,504)):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist, allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def download_stream(url, dest, show_progress=False):
    session = create_session()
    with session.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        written = 0
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if show_progress and total:
                    percent = written * 100 / total
                    print(f"\rDownloaded {written}/{total} bytes ({percent:.1f}%)", end="", flush=True)
        if show_progress:
            print()  # 改行
        os.replace(tmp, dest)
    print(f"Saved: {dest}")
# ここまで、エクセルファイルをダウンロードする ---------------------------------------------------------


# ここから、財務情報をもとに1次スクリーニングするときの便利関数 -----------------------------------------
# get_trailing_pe       PER, yfinanceにtrailingPEがなかった時に、自前計算する
# get_return_on_equity  ROE, yfinanceにreturnOnEquityがなかった時に、自前計算する
# get_equity            株主資本(equity)、ROEの自前計算に必要なequityの表記ゆれ対応
def get_trailing_pe(stock):
    info = stock.info  # yfinance の info
    pe = info.get("trailingPE")
    if pe is not None:
        return pe

    # fallback: try computing from currentPrice and trailingEps
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps = info.get("trailingEps")
    if price is None or eps in (None, 0):
        return None  # 計算不可
    # EPS が負なら negative PE を返すか None にするかは方針次第
    return price / eps


def get_equity(balance_sheet):
    equity_candidates = [
        "Total Stockholder Equity",
        "Stockholders Equity",
        "Shareholders Equity",
        "Total Equity",
        "Ordinary Shares"
    ]
    for key in equity_candidates:
        if key in balance_sheet.index:
            return balance_sheet.loc[key].iloc[0]
    return None


def get_return_on_equity(ticker_symbol, stock):
    info = stock.info
    # 1. info から直接取得
    roe = info.get("returnOnEquity")
    if roe is not None:
        return roe
    else:
        print(f"[WARN] {ticker_symbol}: info['returnOnEquity'] が None でした。fallback 計算に切り替えます。")

    # 2. fallback: 財務諸表から計算
    financials = stock.financials
    balance_sheet = stock.balance_sheet

    # 純利益
    try:
        net_income = financials.loc["Net Income"].iloc[0]
    except Exception as e:
        print(f"[ERROR] {ticker_symbol}: Net Income が取得できませんでした。({e})")
        return None


    # 株主資本
    equity = get_equity(balance_sheet)
    if equity in (None, 0):
        print(f"[ERROR] equity が取得できません。利用可能な項目: {list(balance_sheet.index)}")
        return None

    return round(float(net_income / equity * 100), 6)
# ここまで、財務情報をもとに1次スクリーニングするときの便利関数 -----------------------------------------


if __name__ == "__main__":
    DEST = "data_j.xls"
    # True にすると Content-Length がわかる場合に進捗が表示されます
    get_latest_month_end_tse_listing(DEST)
