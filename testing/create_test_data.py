# -*- coding: utf-8 -*-
"""
テストデータ作成スクリプト
17業種区分から各2社ずつ、計34社を抽出

選抜基準：
1. 営業利益率（最重要）
2. ROE（第二優先）
3. PER（第三優先、低いほど良い）
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

def load_financial_data(file_path):
    """
    財務データファイルを読み込み、データ構造を確認
    """
    try:
        # Excelファイルを読み込み
        df = pd.read_excel(file_path)
        print(f"データ件数: {len(df)}")
        print(f"列数: {len(df.columns)}")
        print("\n=== 列名一覧 ===")
        for i, col in enumerate(df.columns):
            print(f"{i+1:2d}. {col}")
        
        print("\n=== データの概要 ===")
        print(df.info())
        
        print("\n=== 最初の3行のサンプル ===")
        print(df.head(3))
        
        return df
    
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        return None

def analyze_sector_distribution(df, sector_column):
    """
    業種区分の分布を分析
    """
    print(f"\n=== 業種区分分析 ({sector_column}) ===")
    sector_counts = df[sector_column].value_counts()
    print(f"業種数: {len(sector_counts)}")
    print(sector_counts)
    return sector_counts

def calculate_composite_score(df, operating_margin_col, roe_col, per_col):
    """
    複合スコアを計算（営業利益率 > ROE > PER の優先順位）
    
    スコアリング方式：
    1. 営業利益率: 高いほど良い（50%の重み）
    2. ROE: 高いほど良い（30%の重み）
    3. PER: 低いほど良い（20%の重み）
    """
    # 各指標を正規化（0-1の範囲）
    operating_margin_normalized = (df[operating_margin_col] - df[operating_margin_col].min()) / (df[operating_margin_col].max() - df[operating_margin_col].min())
    roe_normalized = (df[roe_col] - df[roe_col].min()) / (df[roe_col].max() - df[roe_col].min())
    
    # PERは低いほど良いので反転
    per_normalized = 1 - (df[per_col] - df[per_col].min()) / (df[per_col].max() - df[per_col].min())
    
    # 複合スコア計算（重み付け）
    composite_score = (
        operating_margin_normalized * 0.5 +  # 営業利益率（50%）
        roe_normalized * 0.3 +               # ROE（30%）
        per_normalized * 0.2                 # PER（20%）
    )
    
    return composite_score

def select_top_companies_by_sector(df, sector_column, score_column, companies_per_sector=2):
    """
    各業種から上位企業を選抜
    """
    selected_companies = []
    
    for sector in df[sector_column].unique():
        if pd.isna(sector):
            continue
            
        sector_df = df[df[sector_column] == sector].copy()
        
        # スコア順にソート（降順）
        sector_df = sector_df.sort_values(score_column, ascending=False)
        
        # 上位N社を選択
        top_companies = sector_df.head(companies_per_sector)
        selected_companies.append(top_companies)
        
        print(f"\n=== {sector} ===")
        print(f"対象企業数: {len(sector_df)}")
        print("選抜企業:")
        for idx, (_, row) in enumerate(top_companies.iterrows(), 1):
            print(f"  {idx}. {row.get('銘柄コード', 'N/A')} {row.get('銘柄名', 'N/A')} "
                  f"(スコア: {row[score_column]:.3f})")
    
    return pd.concat(selected_companies, ignore_index=True)

def main():
    """
    メイン処理
    """
    # ファイルパス
    base_dir = Path(__file__).parent
    input_file = base_dir / "data" / "data_j_with_financials.xlsx"
    
    if not input_file.exists():
        print(f"ファイルが見つかりません: {input_file}")
        return
    
    print("=== テストデータ作成処理開始 ===")
    
    # 1. データ読み込み
    df = load_financial_data(input_file)
    if df is None:
        return
    
    # 2. 列名を確認して適切な列名を特定する必要があります
    # まずは列名を確認
    print("\n=== 列名確認 ===")
    column_mapping = {}
    
    # 想定される列名パターン
    potential_columns = {
        'sector': ['業種', '業種区分', '17業種区分', 'Sector', 'sector'],
        'operating_margin': ['営業利益率', '営業利益マージン', 'Operating Margin', 'operating_margin'],
        'roe': ['ROE', 'roe', '自己資本利益率'],
        'per': ['PER', 'per', '株価収益率'],
        'ticker': ['銘柄コード', 'コード', 'Code', 'Ticker', 'ticker'],
        'company_name': ['銘柄名', '会社名', 'Company Name', 'Name', 'name']
    }
    
    # 列名マッチング
    for key, patterns in potential_columns.items():
        for pattern in patterns:
            if pattern in df.columns:
                column_mapping[key] = pattern
                break
    
    print(f"検出された列名マッピング: {column_mapping}")
    
    # 必須列の確認
    required_keys = ['sector', 'operating_margin', 'roe', 'per']
    missing_keys = [key for key in required_keys if key not in column_mapping]
    
    if missing_keys:
        print(f"\n必須列が見つかりません: {missing_keys}")
        print("利用可能な列名:")
        for col in df.columns:
            print(f"  - {col}")
        return
    
    # 3. 業種分布分析
    sector_counts = analyze_sector_distribution(df, column_mapping['sector'])
    
    # 4. 複合スコア計算
    print("\n=== スコア計算 ===")
    df['composite_score'] = calculate_composite_score(
        df, 
        column_mapping['operating_margin'], 
        column_mapping['roe'], 
        column_mapping['per']
    )
    
    # 5. 業種別選抜
    print("\n=== 業種別選抜 ===")
    selected_df = select_top_companies_by_sector(
        df, 
        column_mapping['sector'], 
        'composite_score', 
        companies_per_sector=2
    )
    
    # 6. 結果保存
    output_file = base_dir / "test_data_selected_companies.xlsx"
    selected_df.to_excel(output_file, index=False)
    print(f"\n=== 処理完了 ===")
    print(f"選抜企業数: {len(selected_df)}")
    print(f"出力ファイル: {output_file}")
    
    # 7. サマリー出力
    print(f"\n=== 選抜結果サマリー ===")
    if 'ticker' in column_mapping and 'company_name' in column_mapping:
        summary_cols = [
            column_mapping['ticker'], 
            column_mapping['company_name'],
            column_mapping['sector'],
            column_mapping['operating_margin'],
            column_mapping['roe'],
            column_mapping['per'],
            'composite_score'
        ]
        
        summary_df = selected_df[summary_cols].copy()
        summary_df = summary_df.sort_values('composite_score', ascending=False)
        
        print(summary_df.to_string(index=False))
        
        # CSV版も出力
        csv_file = base_dir / "test_data_selected_companies.csv"
        summary_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"\nCSV出力: {csv_file}")

if __name__ == "__main__":
    main()