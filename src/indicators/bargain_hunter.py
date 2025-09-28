"""
バーゲンハンターインジケーター

割安・割高判定と価格変動に基づいて売買シグナルを生成します。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np
from .base import BaseIndicator, IndicatorResult, Signal


class BargainHunterIndicator(BaseIndicator):
    """
    バーゲンハンターインジケーター

    200日移動平均線を基準に割安・割高を判定し、
    短期的な価格変動から売買シグナルを生成します。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        インジケーターを初期化します。

        Args:
            config: インジケーター設定
                - ma_period: 移動平均期間（デフォルト: 200）
                - drop_percentage: 買いシグナルの下落率閾値（デフォルト: 3.0）
                - rise_percentage: 売りシグナルの上昇率閾値（デフォルト: 5.0）
        """
        self.ma_period = config.get('ma_period', 200)
        self.drop_percentage = config.get('drop_percentage', 3.0)
        self.rise_percentage = config.get('rise_percentage', 5.0)
        super().__init__(config)

    def _validate_config(self) -> None:
        """設定の妥当性を検証します。"""
        if self.ma_period <= 0:
            raise ValueError(f"移動平均期間は正の値である必要があります: {self.ma_period}")

        if self.drop_percentage <= 0:
            raise ValueError(f"下落率閾値は正の値である必要があります: {self.drop_percentage}")

        if self.rise_percentage <= 0:
            raise ValueError(f"上昇率閾値は正の値である必要があります: {self.rise_percentage}")

    def calculate_signal(
        self,
        ticker: str,
        company_name: str,
        price_data: pd.DataFrame
    ) -> IndicatorResult:
        """
        単一銘柄のシグナルを計算します。

        Args:
            ticker: ティッカーシンボル
            company_name: 企業名
            price_data: 株価データ

        Returns:
            IndicatorResult: 計算結果
        """
        # データ検証（最低限必要な日数: 移動平均期間 + 3日）
        required_days = self.ma_period + 3
        if not self.is_valid_data(price_data, required_days):
            return IndicatorResult(
                ticker=ticker,
                company_name=company_name,
                signal=Signal.NONE,
                current_price=0.0,
                lot_price=0.0,
                additional_info={"error": f"データ不足: {len(price_data)}日分（必要: {required_days}日）"}
            )

        # 最新のデータから必要な日数分を取得
        price_data = price_data.tail(required_days).copy()
        price_data.reset_index(drop=True, inplace=True)

        # 終値データを取得
        close_prices = price_data['Close']

        # 200日移動平均を計算
        ma_200 = self.calculate_moving_average(close_prices, self.ma_period)

        # 最新の価格と移動平均
        current_price = close_prices.iloc[-1]
        current_ma = ma_200.iloc[-1]

        # 過去3日分の価格
        price_3_days_ago = close_prices.iloc[-3]
        price_2_days_ago = close_prices.iloc[-2]
        price_1_day_ago = close_prices.iloc[-1]

        # 割高・割安判定
        is_overvalued = current_price > current_ma
        is_undervalued = current_price < current_ma
        # is_overvalued = False
        # is_undervalued = False

        # 価格変動の計算
        # 2日前から1日前への変動
        change_2_to_1 = ((price_2_days_ago - price_3_days_ago) / price_3_days_ago) * 100
        # 1日前から現在への変動
        change_1_to_0 = ((price_1_day_ago - price_2_days_ago) / price_2_days_ago) * 100
        # 2日前から現在までの合計変動率
        total_change = ((price_1_day_ago - price_3_days_ago) / price_3_days_ago) * 100

        # シグナル判定
        signal = Signal.NONE

        # 買いエントリー条件
        # 割高でなく、2つ前のバーから下降開始し、合計下落率がdropPercentage以上
        if not is_overvalued and change_2_to_1 < 0 and change_1_to_0 < 0:
            if abs(total_change) >= self.drop_percentage:
                signal = Signal.BUY

        # 売りエントリー条件
        # 割安でなく、2つ前のバーから上昇開始し、合計上昇率がrisePercentage以上
        elif not is_undervalued and change_2_to_1 > 0 and change_1_to_0 > 0:
            if total_change >= self.rise_percentage:
                signal = Signal.SELL
        # signal = Signal.BUY

        # 100株単位の価格を計算
        lot_price = current_price * 100

        # 追加情報を作成
        additional_info = {
            "ma_200": round(current_ma, 2),
            "price_vs_ma": round(((current_price - current_ma) / current_ma) * 100, 2),
            "is_overvalued": is_overvalued,
            "is_undervalued": is_undervalued,
            "change_2_days": round(total_change, 2),
            "change_2_to_1": round(change_2_to_1, 2),
            "change_1_to_0": round(change_1_to_0, 2)
        }

        return IndicatorResult(
            ticker=ticker,
            company_name=company_name,
            signal=signal,
            current_price=round(current_price, 2),
            lot_price=round(lot_price, 0),
            additional_info=additional_info
        )
