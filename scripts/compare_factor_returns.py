"""
ファクターリターン比較スクリプト

旧spotデータとsec1から生成したspotデータのファクターリターン誤差を評価する。
評価指標: MAE, RMSE, MAX (abs diff)
日付はintersection（共通日）に揃える。
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
import sys
import os

# lib.pyをインポートするためにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import lib


def load_spot_data(tz: str, spot_suffix: str):
    """
    spotデータを読み込んで、lib.pyの処理と同じ形式に整形する
    
    Args:
        tz: タイムゾーン（"TK20" or "NY17"）
        spot_suffix: ファイル名のサフィックス（例: "_from_sec1"）
    
    Returns:
        整形されたspotレートDataFrame
    """
    if tz == "TK20":
        spot_df = lib.loadSpotRate_TK20(spot_suffix=spot_suffix)
        spot_df = spot_df.rename(columns={'date_time': 'start_time'})
        # TK20: hour=20, weekday=1 (Tuesday)
        spot_df = spot_df[
            (spot_df['start_time'].dt.hour == 20) & 
            (spot_df['start_time'].dt.weekday == 1)
        ].reset_index(drop=True)
    elif tz == "NY17":
        spot_df = lib.loadSpotRate_NY17(spot_suffix=spot_suffix)
        spot_df = spot_df.rename(columns={'date_time': 'start_time'})
        # NY17: hour=17, weekday=0 (Monday)
        spot_df = spot_df[
            (spot_df['start_time'].dt.hour == 17) & 
            (spot_df['start_time'].dt.weekday == 0)
        ].reset_index(drop=True)
    else:
        raise ValueError(f"Unknown timezone: {tz}. Use 'TK20' or 'NY17'")
    
    return spot_df


def get_spot_for_strategy(spot_df, strategy: str):
    """
    Strategyに応じた通貨リストでspotデータをフィルタリング
    
    Args:
        spot_df: spotレートDataFrame
        strategy: 戦略（"A", "B", "C"）
    
    Returns:
        フィルタリングされたspotレートDataFrame
    """
    if strategy == "A":
        currencies = lib.CURRENCY_A
    elif strategy == "B":
        currencies = lib.CURRENCY_B
    elif strategy == "C":
        currencies = lib.CURRENCY_C
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'A', 'B', or 'C'")
    
    return spot_df[["start_time"] + currencies]


def get_forward_for_strategy(tz: str, strategy: str):
    """
    Strategyに応じたforwardレートを取得
    
    Args:
        tz: タイムゾーン（"TK20" or "NY17"）
        strategy: 戦略（"A", "B", "C"）
    
    Returns:
        forwardレートDataFrame
    """
    if strategy == "A":
        if tz == "TK20":
            return lib.FWDRATE_A_TK20
        elif tz == "NY17":
            return lib.FWDRATE_A_NY17
    elif strategy == "B":
        if tz == "TK20":
            return lib.FWDRATE_B_TK20
        elif tz == "NY17":
            return lib.FWDRATE_B_NY17
    elif strategy == "C":
        if tz == "TK20":
            return lib.FWDRATE_C_TK20
        elif tz == "NY17":
            return lib.FWDRATE_C_NY17
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'A', 'B', or 'C'")
    
    raise ValueError(f"Unknown timezone: {tz}. Use 'TK20' or 'NY17'")


def calculate_factor_returns(tz: str, strategy: str, spot_suffix: str, 
                             start_date: str = None, end_date: str = None):
    """
    ファクターリターンを計算
    
    Args:
        tz: タイムゾーン（"TK20" or "NY17"）
        strategy: 戦略（"A", "B", "C"）
        spot_suffix: ファイル名のサフィックス
        start_date: 開始日（YYYY-MM-DD形式、オプション）
        end_date: 終了日（YYYY-MM-DD形式、オプション）
    
    Returns:
        ファクターリターンDataFrame（start_timeをindexに持つ）
    """
    # spotデータを読み込んで整形
    spot_df = load_spot_data(tz, spot_suffix)
    spot_strategy = get_spot_for_strategy(spot_df, strategy)
    
    # forwardデータを取得
    fwd_strategy = get_forward_for_strategy(tz, strategy)
    
    # 日付フィルタリング
    if start_date:
        start_date = pd.to_datetime(start_date)
        spot_strategy = spot_strategy[spot_strategy['start_time'] >= start_date]
        fwd_strategy = fwd_strategy[fwd_strategy['start_time'] >= start_date]
    if end_date:
        end_date = pd.to_datetime(end_date)
        spot_strategy = spot_strategy[spot_strategy['start_time'] <= end_date]
        fwd_strategy = fwd_strategy[fwd_strategy['start_time'] <= end_date]
    
    # ファクターリターンを計算
    factor_returns = pd.DataFrame()
    position_id = 0  # デフォルトのposition_id
    
    if strategy == "A":
        factor_returns = lib.makeFactorReturnA(
            fwd_strategy, factor_returns, position_id, fwd_strategy, spot_strategy
        )
    elif strategy == "B":
        factor_returns = lib.makeFactorReturnB(
            fwd_strategy, factor_returns, position_id, fwd_strategy, spot_strategy
        )
    elif strategy == "C":
        factor_returns = lib.makeFactorReturnC(
            fwd_strategy, factor_returns, position_id, fwd_strategy, spot_strategy
        )
    
    # start_timeをindexに設定
    if 'start_time' in factor_returns.columns:
        factor_returns = factor_returns.set_index('start_time')
    
    return factor_returns


def compare_factor_returns(tz: str, strategy: str, old_suffix: str, new_suffix: str,
                           start_date: str = None, end_date: str = None):
    """
    旧spotと新spotのファクターリターンを比較
    
    Args:
        tz: タイムゾーン（"TK20" or "NY17"）
        strategy: 戦略（"A", "B", "C"）
        old_suffix: 旧データのサフィックス（通常は""）
        new_suffix: 新データのサフィックス（例: "_from_sec1"）
        start_date: 開始日（YYYY-MM-DD形式、オプション）
        end_date: 終了日（YYYY-MM-DD形式、オプション）
    
    Returns:
        (stats_dict, top10_df): 統計情報と上位10件の差分
    """
    # 旧データでファクターリターンを計算
    r_old = calculate_factor_returns(tz, strategy, old_suffix, start_date, end_date)
    
    # 新データでファクターリターンを計算
    r_new = calculate_factor_returns(tz, strategy, new_suffix, start_date, end_date)
    
    # 共通日を取得（intersection）
    common_idx = r_old.index.intersection(r_new.index)
    
    if len(common_idx) == 0:
        print("Warning: No common dates found!")
        return {}, pd.DataFrame()
    
    # 共通日のみで比較
    r_old_common = r_old.reindex(common_idx)
    r_new_common = r_new.reindex(common_idx)
    
    # 各期間のファクターリターン列を取得
    factor_cols = [col for col in r_old_common.columns if col not in ['end_time']]
    
    # 全期間のファクターリターンの合計を計算（各期間の列を合計）
    r_old_total = r_old_common[factor_cols].sum(axis=1)
    r_new_total = r_new_common[factor_cols].sum(axis=1)
    
    # 差分を計算
    diff = r_new_total - r_old_total
    
    # 統計情報を計算
    n = len(diff)
    mae = np.mean(np.abs(diff))
    rmse = np.sqrt(np.mean(diff ** 2))
    max_abs_diff = np.max(np.abs(diff))
    
    stats = {
        'n': n,
        'mae': mae,
        'rmse': rmse,
        'max': max_abs_diff
    }
    
    # 上位10件の差分を取得
    top10_idx = np.abs(diff).nlargest(10).index
    top10_df = pd.DataFrame({
        'date': top10_idx,
        'r_old': r_old_total.loc[top10_idx],
        'r_new': r_new_total.loc[top10_idx],
        'diff': diff.loc[top10_idx],
        'abs_diff': np.abs(diff.loc[top10_idx])
    }).sort_values('abs_diff', ascending=False)
    
    return stats, top10_df


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='旧spot vs sec1生成spotのファクターリターン誤差評価'
    )
    parser.add_argument('--tz', type=str, required=True, 
                       choices=['TK20', 'NY17'],
                       help='タイムゾーン（TK20 or NY17）')
    parser.add_argument('--strategy', type=str, required=True,
                       choices=['A', 'B', 'C'],
                       help='戦略（A, B, or C）')
    parser.add_argument('--old-suffix', type=str, default='',
                       help='旧データのサフィックス（デフォルト: ""）')
    parser.add_argument('--new-suffix', type=str, default='_from_sec1',
                       help='新データのサフィックス（デフォルト: "_from_sec1"）')
    parser.add_argument('--start-date', type=str, default=None,
                       help='開始日（YYYY-MM-DD形式）')
    parser.add_argument('--end-date', type=str, default=None,
                       help='終了日（YYYY-MM-DD形式）')
    parser.add_argument('--output', type=str, default=None,
                       help='結果CSV保存先（オプション）')
    
    args = parser.parse_args()
    
    # 比較実行
    stats, top10_df = compare_factor_returns(
        args.tz, args.strategy, args.old_suffix, args.new_suffix,
        args.start_date, args.end_date
    )
    
    if len(stats) == 0:
        print("Error: Comparison failed!")
        return
    
    # 結果を表示
    print("=" * 60)
    print(f"ファクターリターン比較結果")
    print("=" * 60)
    print(f"TZ: {args.tz}")
    print(f"Strategy: {args.strategy}")
    if args.start_date:
        print(f"開始日: {args.start_date}")
    if args.end_date:
        print(f"終了日: {args.end_date}")
    print()
    print(f"n (共通日数): {stats['n']}")
    print(f"MAE: {stats['mae']:.8f}")
    print(f"RMSE: {stats['rmse']:.8f}")
    print(f"MAX (abs diff): {stats['max']:.8f}")
    print()
    
    if len(top10_df) > 0:
        print("上位10件（abs(diff)最大）:")
        print("-" * 60)
        for idx, row in top10_df.iterrows():
            print(f"  {row['date']}: r_old={row['r_old']:.8f}, "
                  f"r_new={row['r_new']:.8f}, diff={row['diff']:.8f}")
        print()
    
    # CSV保存（オプション）
    if args.output:
        output_df = pd.DataFrame([stats])
        output_df.to_csv(args.output, index=False)
        print(f"結果を保存しました: {args.output}")


if __name__ == '__main__':
    main()

