# -*- coding: utf-8 -*-
"""Command-line interface for portfolio management"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import pandas as pd
from zoneinfo import ZoneInfo

from .models import Trade, Position
from .storage import PortfolioStorage
from .pricing import StockPricingService


class PortfolioCLI:
    """Handles command-line interactions for portfolio management"""

    def __init__(self, storage: PortfolioStorage, pricing: StockPricingService, market: str = "TSE"):
        """Initialize CLI

        Args:
            storage: PortfolioStorage instance
            pricing: StockPricingService instance
            market: Default market (e.g., "TSE")
        """
        self.storage = storage
        self.pricing = pricing
        self.market = market

    def register_mode(self):
        """Interactive registration mode for adding trades"""
        print("\n=== 銘柄登録モード ===")
        print("対話形式で銘柄情報を登録します。")
        print("終了するには、ティッカー入力時に空欄でEnterを押してください。\n")

        while True:
            try:
                # Ticker input
                ticker_local = input("ティッカーコード (例: 7203): ").strip()
                if not ticker_local:
                    print("\n登録を終了します。")
                    break

                # Format to yfinance symbol
                ticker_yf = self.pricing.format_ticker(ticker_local, self.market)

                # Get stock name
                print(f"銘柄名を取得中... ({ticker_yf})")
                stock_name = self.pricing.get_stock_name(ticker_local, ticker_yf)
                print(f"銘柄名: {stock_name}")

                # Quantity
                quantity_str = input("購入数量: ").strip()
                if not quantity_str:
                    print("エラー: 数量を入力してください。\n")
                    continue
                quantity = int(quantity_str)

                # Price
                price_str = input("購入価格 (円): ").strip()
                if not price_str:
                    print("エラー: 価格を入力してください。\n")
                    continue
                price = Decimal(price_str)

                # Commission (optional)
                commission_str = input("手数料 (円, デフォルト: 0): ").strip()
                commission = Decimal(commission_str) if commission_str else Decimal("0")

                # Trade date (default: today in JST)
                today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date()
                date_str = input(f"購入日 (YYYY-MM-DD, デフォルト: {today_jst}): ").strip()
                if date_str:
                    trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    trade_date = today_jst

                # Notes (optional)
                notes = input("メモ (任意): ").strip()

                # Create trade
                trade = Trade(
                    trade_date=trade_date,
                    ticker_local=ticker_local,
                    ticker_yf=ticker_yf,
                    stock_name=stock_name,
                    side="BUY",
                    quantity=quantity,
                    price=price,
                    commission=commission,
                    market=self.market,
                    currency="JPY",
                    notes=notes
                )

                # Save to CSV
                self.storage.append_trade(trade)

                # Display confirmation
                print("\n--- 登録完了 ---")
                print(f"取引ID: {trade.trade_id}")
                print(f"日付: {trade.trade_date}")
                print(f"銘柄: {trade.stock_name} ({trade.ticker_local})")
                print(f"数量: {trade.quantity}")
                print(f"単価: {trade.price} 円")
                print(f"手数料: {trade.commission} 円")
                print(f"合計: {trade.total_cost} 円")
                if trade.notes:
                    print(f"メモ: {trade.notes}")
                print("---------------\n")

            except ValueError as e:
                print(f"エラー: 入力が無効です - {e}\n")
            except KeyboardInterrupt:
                print("\n\n登録を中断します。")
                break
            except Exception as e:
                print(f"エラー: {e}\n")

    def display_mode(self):
        """Display mode showing current portfolio with P&L"""
        print("\n=== ポートフォリオ表示 ===\n")

        # Get current positions
        positions = self.storage.get_current_positions()

        if not positions:
            print("保有銘柄がありません。\n")
            return

        print(f"保有銘柄数: {len(positions)}")
        print("現在価格を取得中...\n")

        # Fetch current prices
        for position in positions:
            current_price = self.pricing.get_current_price(position.ticker_yf)
            position.current_price = current_price

        # Create display DataFrame
        display_data = []
        for pos in positions:
            display_data.append({
                'ティッカー': pos.ticker_local,
                '銘柄名': pos.stock_name,
                '保有数': pos.quantity,
                '平均取得単価': f"¥{pos.avg_cost:,.2f}",
                '取得総額': f"¥{pos.total_cost:,.0f}",
                '現在価格': f"¥{pos.current_price:,.2f}" if pos.current_price else "N/A",
                '評価額': f"¥{pos.market_value:,.0f}" if pos.market_value else "N/A",
                '損益': f"¥{pos.unrealized_pnl:+,.0f}" if pos.unrealized_pnl else "N/A",
                '損益率': f"{pos.unrealized_pnl_pct:+.2f}%" if pos.unrealized_pnl_pct else "N/A"
            })

        df = pd.DataFrame(display_data)

        # Display table
        print(df.to_string(index=False))

        # Calculate totals
        total_cost = sum(pos.total_cost for pos in positions)
        total_market_value = sum(pos.market_value for pos in positions if pos.market_value)
        total_pnl = sum(pos.unrealized_pnl for pos in positions if pos.unrealized_pnl)
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        print("\n--- 合計 ---")
        print(f"取得総額: ¥{total_cost:,.0f}")
        print(f"評価額: ¥{total_market_value:,.0f}")
        print(f"評価損益: ¥{total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)")
        print("-----------\n")
