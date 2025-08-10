# -*- coding: utf-8 -*-
"""
incremental_load_yfinance.py の動作確認用テストスクリプト

このスクリプトは、テストデータを使用して差分更新機能の動作を確認します。
"""

import subprocess
import os
import sys
from pathlib import Path

def run_test_command(description, command, expect_success=True):
    """
    テストコマンドを実行し、結果を表示
    """
    print(f"\n{'='*60}")
    print(f"テスト: {description}")
    print(f"コマンド: {' '.join(command)}")
    print('='*60)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=300  # 5分でタイムアウト
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"終了コード: {result.returncode}")
        
        if expect_success and result.returncode == 0:
            print("✅ テスト成功")
        elif not expect_success and result.returncode != 0:
            print("✅ 期待通りの失敗")
        else:
            print("❌ テスト失敗")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """
    メイン処理
    """
    print("incremental_load_yfinance.py の動作確認テスト")
    
    # テスト環境の設定
    base_dir = Path(__file__).parent
    excel_path = base_dir / "test_data_selected_companies.xlsx"
    test_output_dir = base_dir / "test_stock_data"
    script_path = base_dir / "src" / "incremental_load_yfinance.py"
    
    # テスト出力ディレクトリをクリーンアップ
    if test_output_dir.exists():
        import shutil
        shutil.rmtree(test_output_dir)
    
    print(f"テスト設定:")
    print(f"  Excelファイル: {excel_path}")
    print(f"  出力ディレクトリ: {test_output_dir}")
    print(f"  スクリプト: {script_path}")
    
    # 1. ヘルプの表示テスト
    run_test_command(
        "ヘルプ表示",
        ["uv", "run", "python", str(script_path), "--help"]
    )
    
    # 2. 必須引数なしでの実行（エラーを期待）
    run_test_command(
        "必須引数なしでの実行（エラー期待）",
        ["uv", "run", "python", str(script_path)],
        expect_success=False
    )
    
    # 3. 存在しないExcelファイル（エラーを期待）
    run_test_command(
        "存在しないExcelファイル（エラー期待）",
        ["uv", "run", "python", str(script_path), 
         "--excel-path", "nonexistent.xlsx", 
         "--output-dir", str(test_output_dir)],
        expect_success=False
    )
    
    # 4. 実際のテストデータでの実行前確認（Dry Run）
    if excel_path.exists():
        run_test_command(
            "テストデータでのDry Run",
            ["uv", "run", "python", str(script_path), 
             "--excel-path", str(excel_path), 
             "--output-dir", str(test_output_dir),
             "--dry-run"]
        )
        
        # 5. 実際のデータダウンロード（少数のティッカーで）
        print(f"\n{'='*60}")
        print("実際のデータダウンロードテストを実行しますか？")
        print("（注意: yfinance APIを使用してインターネットからデータをダウンロードします）")
        choice = input("実行する場合は 'yes' を入力してください: ").lower().strip()
        
        if choice == 'yes':
            run_test_command(
                "実際のデータダウンロード（ログレベル=DEBUG）",
                ["uv", "run", "python", str(script_path), 
                 "--excel-path", str(excel_path), 
                 "--output-dir", str(test_output_dir),
                 "--delay", "2.0",  # レート制限を厳しくしてテスト
                 "--lookback", "7",  # 短期間のデータのみ
                 "--log-level", "DEBUG"]
            )
            
            # 6. 出力ファイルの確認
            print(f"\n{'='*60}")
            print("出力ファイルの確認")
            print('='*60)
            
            if test_output_dir.exists():
                raw_dir = test_output_dir / "raw"
                if raw_dir.exists():
                    parquet_files = list(raw_dir.glob("*.parquet"))
                    print(f"作成されたparquetファイル数: {len(parquet_files)}")
                    
                    if parquet_files:
                        print("最初の5ファイル:")
                        for f in parquet_files[:5]:
                            print(f"  - {f.name}")
                            # ファイルサイズも表示
                            size_kb = f.stat().st_size / 1024
                            print(f"    サイズ: {size_kb:.1f} KB")
                    
                    # バッチファイルの確認
                    batch_dir = test_output_dir / "batch_size"
                    if batch_dir.exists():
                        batch_files = list(batch_dir.glob("batch_*.parquet"))
                        print(f"\nバッチファイル数: {len(batch_files)}")
                    
                    # マスターファイルの確認
                    master_file = test_output_dir / "ticker_combined_OHLCV.parquet"
                    if master_file.exists():
                        size_mb = master_file.stat().st_size / (1024 * 1024)
                        print(f"\nマスターファイル: {master_file.name}")
                        print(f"  サイズ: {size_mb:.1f} MB")
                    
                else:
                    print("❌ rawディレクトリが見つかりません")
            else:
                print("❌ 出力ディレクトリが見つかりません")
        else:
            print("実際のデータダウンロードテストをスキップしました")
    else:
        print(f"❌ テストデータファイルが見つかりません: {excel_path}")
        print("先に create_test_data.py を実行してテストデータを作成してください")
    
    print(f"\n{'='*60}")
    print("テスト完了")
    print('='*60)

if __name__ == "__main__":
    main()