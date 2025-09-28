"""
インジケーター基底クラス

全てのインジケーターが継承する抽象基底クラスを定義します。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    """取引シグナルの種類"""
    BUY = "買い"
    SELL = "売り"
    HOLD = "保有"
    NONE = "なし"


@dataclass
class IndicatorResult:
    """インジケーター計算結果"""
    ticker: str
    company_name: str
    signal: Signal
    current_price: float
    lot_price: float  # 100株単位の価格
    additional_info: Dict[str, Any]  # インジケーター固有の追加情報


class BaseIndicator(ABC):
    """
    インジケーター基底クラス

    全てのインジケーターはこのクラスを継承し、
    calculate_signalメソッドを実装する必要があります。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        インジケーターを初期化します。

        Args:
            config: インジケーター設定辞書
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        設定の妥当性を検証します。

        Raises:
            ValueError: 設定が不正な場合
        """
        pass

    @abstractmethod
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
            price_data: 株価データ (Date, Open, High, Low, Close, Volume)

        Returns:
            IndicatorResult: 計算結果
        """
        pass

    def calculate_signals_batch(
        self,
        ticker_data_list: List[Tuple[str, str, pd.DataFrame]]
    ) -> List[IndicatorResult]:
        """
        複数銘柄のシグナルを一括計算します。

        Args:
            ticker_data_list: (ticker, company_name, price_data)のリスト

        Returns:
            List[IndicatorResult]: 計算結果のリスト
        """
        results = []
        for ticker, company_name, price_data in ticker_data_list:
            try:
                result = self.calculate_signal(ticker, company_name, price_data)
                results.append(result)
            except Exception as e:
                # エラーが発生した場合はNONEシグナルで結果を作成
                results.append(IndicatorResult(
                    ticker=ticker,
                    company_name=company_name,
                    signal=Signal.NONE,
                    current_price=0.0,
                    lot_price=0.0,
                    additional_info={"error": str(e)}
                ))
        return results

    @staticmethod
    def calculate_moving_average(
        prices: pd.Series,
        period: int
    ) -> pd.Series:
        """
        移動平均を計算します。

        Args:
            prices: 価格データ
            period: 移動平均期間

        Returns:
            pd.Series: 移動平均値
        """
        return prices.rolling(window=period).mean()

    @staticmethod
    def calculate_price_change(
        prices: pd.Series,
        periods: int = 1
    ) -> pd.Series:
        """
        価格変化率を計算します。

        Args:
            prices: 価格データ
            periods: 比較期間

        Returns:
            pd.Series: 変化率 (%)
        """
        return ((prices - prices.shift(periods)) / prices.shift(periods)) * 100

    @staticmethod
    def is_valid_data(
        price_data: pd.DataFrame,
        required_days: int
    ) -> bool:
        """
        データの妥当性を検証します。

        Args:
            price_data: 株価データ
            required_days: 必要な最小日数

        Returns:
            bool: データが有効な場合True
        """
        if price_data is None or price_data.empty:
            return False

        if len(price_data) < required_days:
            return False

        # 必須カラムの確認
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in price_data.columns for col in required_columns):
            return False

        # NaNチェック
        if price_data[required_columns].isnull().any().any():
            return False

        return True
