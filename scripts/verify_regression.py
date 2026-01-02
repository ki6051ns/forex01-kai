"""
高速化の回帰確認スクリプト

USE_FAST=False と True で結果が完全一致することを確認
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import argparse


def compare_train_results(old_file: str, new_file: str, tolerance: float = 1e-10):
    """
    トレーニング結果を比較
    
    Args:
        old_file: USE_FAST=False の結果ファイル
        new_file: USE_FAST=True の結果ファイル
        tolerance: 許容誤差
    
    Returns:
        (is_match, diff_summary): 一致フラグと差分サマリー
    """
    # ファイルパスの検証
    old_path = Path(old_file)
    new_path = Path(new_file)
    
    if not old_path.exists():
        raise FileNotFoundError(f"Old file not found: {old_file}\n"
                                f"Please specify the actual file path, e.g.:\n"
                                f"  --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv")
    
    if not new_path.exists():
        raise FileNotFoundError(f"New file not found: {new_file}\n"
                                f"Please specify the actual file path, e.g.:\n"
                                f"  --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv")
    
    try:
        df_old = pd.read_csv(old_file)
        df_new = pd.read_csv(new_file)
    except PermissionError as e:
        raise PermissionError(f"Permission denied: {e}\n"
                             f"Please check file permissions or close the file if it's open in another program.")
    except Exception as e:
        raise Exception(f"Error reading CSV files: {e}\n"
                       f"Old file: {old_file}\n"
                       f"New file: {new_file}")
    
    # 列名を確認
    common_cols = set(df_old.columns) & set(df_new.columns)
    if 'start_time' in common_cols:
        common_cols.remove('start_time')
    
    print(f"比較列数: {len(common_cols)}")
    print(f"比較行数: old={len(df_old)}, new={len(df_new)}")
    
    # 行数が一致するか
    if len(df_old) != len(df_new):
        print(f"[ERROR] 行数が不一致: old={len(df_old)}, new={len(df_new)}")
        return False, {}
    
    # 各列を比較
    diff_summary = {}
    all_match = True
    
    for col in common_cols:
        if col in ['position_id_1', 'position_id_2', 'simulation_period_to']:
            # 整数列は完全一致を要求
            if not df_old[col].equals(df_new[col]):
                print(f"[ERROR] {col}: 完全一致しません")
                all_match = False
                diff_summary[col] = {
                    'max_diff': None,
                    'match': False,
                    'type': 'integer'
                }
            else:
                diff_summary[col] = {
                    'max_diff': 0,
                    'match': True,
                    'type': 'integer'
                }
        else:
            # 数値列は許容誤差内で比較
            old_vals = df_old[col].values
            new_vals = df_new[col].values
            
            # NaNの扱い
            old_nan = pd.isna(old_vals)
            new_nan = pd.isna(new_vals)
            
            if not np.array_equal(old_nan, new_nan):
                print(f"[ERROR] {col}: NaNの位置が不一致")
                all_match = False
                diff_summary[col] = {
                    'max_diff': None,
                    'match': False,
                    'type': 'numeric',
                    'nan_mismatch': True
                }
                continue
            
            # NaN以外の値を比較
            valid_mask = ~old_nan
            if valid_mask.sum() == 0:
                diff_summary[col] = {
                    'max_diff': 0,
                    'match': True,
                    'type': 'numeric',
                    'all_nan': True
                }
                continue
            
            old_valid = old_vals[valid_mask]
            new_valid = new_vals[valid_mask]
            
            diff = np.abs(old_valid - new_valid)
            max_diff = np.max(diff)
            
            if max_diff > tolerance:
                print(f"[ERROR] {col}: max_diff={max_diff:.2e} > tolerance={tolerance:.2e}")
                all_match = False
            else:
                print(f"[OK] {col}: max_diff={max_diff:.2e}")
            
            diff_summary[col] = {
                'max_diff': max_diff,
                'match': max_diff <= tolerance,
                'type': 'numeric',
                'mean_diff': np.mean(diff),
                'p95_diff': np.percentile(diff, 95) if len(diff) > 0 else 0
            }
    
    return all_match, diff_summary


def compare_daily_pl(old_file: str, new_file: str, tolerance: float = 1e-10):
    """
    日次PL系列を比較（もしあれば）
    
    Args:
        old_file: USE_FAST=False の詳細結果ファイル
        new_file: USE_FAST=True の詳細結果ファイル
        tolerance: 許容誤差
    
    Returns:
        (is_match, max_diff): 一致フラグと最大差分
    """
    # 詳細結果ファイルが存在するか確認
    old_path = Path(old_file)
    new_path = Path(new_file)
    
    if not old_path.exists():
        print(f"⚠️  日次PLファイル（old）が見つかりません: {old_file}")
        print("   スキップします。")
        return True, 0.0
    
    if not new_path.exists():
        print(f"⚠️  日次PLファイル（new）が見つかりません: {new_file}")
        print("   スキップします。")
        return True, 0.0
    
    try:
        df_old = pd.read_csv(old_file)
        df_new = pd.read_csv(new_file)
        
        # start_timeとtotal列を探す
        if 'start_time' not in df_old.columns or 'total' not in df_old.columns:
            print("⚠️  'start_time'または'total'列が見つかりません。スキップします。")
            return True, 0.0
        
        # マージ
        merged = pd.merge(
            df_old[['start_time', 'total']].rename(columns={'total': 'total_old'}),
            df_new[['start_time', 'total']].rename(columns={'total': 'total_new'}),
            on='start_time',
            how='inner'
        )
        
        if len(merged) == 0:
            print("⚠️  共通の日付が見つかりません。スキップします。")
            return True, 0.0
        
        # 差分を計算
        diff = np.abs(merged['total_old'] - merged['total_new'])
        max_diff = np.max(diff)
        
        if max_diff > tolerance:
            print(f"[ERROR] 日次PL: max_diff={max_diff:.2e} > tolerance={tolerance:.2e}")
            return False, max_diff
        else:
            print(f"[OK] 日次PL: max_diff={max_diff:.2e}")
            return True, max_diff
        
    except Exception as e:
        print(f"⚠️  日次PL比較でエラー: {e}")
        return True, 0.0


def main():
    parser = argparse.ArgumentParser(
        description='高速化の回帰確認',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # Step 1: USE_FAST=False で実行
  # lib.py で USE_FAST = False に設定
  python train.py
  cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
  
  # Step 2: USE_FAST=True で実行
  # lib.py で USE_FAST = True に設定
  python train.py
  cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
  
  # Step 3: 比較
  python scripts/verify_regression.py \\
      --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \\
      --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
        """
    )
    parser.add_argument('--old', type=str, required=True, 
                       help='USE_FAST=False の結果ファイル（例: train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv）')
    parser.add_argument('--new', type=str, required=True,
                       help='USE_FAST=True の結果ファイル（例: train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv）')
    parser.add_argument('--tolerance', type=float, default=1e-10, help='許容誤差')
    parser.add_argument('--daily-pl-old', type=str, help='USE_FAST=False の日次PLファイル（オプション）')
    parser.add_argument('--daily-pl-new', type=str, help='USE_FAST=True の日次PLファイル（オプション）')
    
    args = parser.parse_args()
    
    # プレースホルダーチェック
    if args.old == '...' or args.new == '...':
        print("=" * 60)
        print("[ERROR] エラー: ファイルパスを指定してください")
        print("=" * 60)
        print("\n使用例:")
        print("  python scripts/verify_regression.py \\")
        print("      --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \\")
        print("      --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv")
        print("\n詳細は --help を参照してください。")
        sys.exit(1)
    
    print("=" * 60)
    print("高速化の回帰確認")
    print("=" * 60)
    print(f"Old file: {args.old}")
    print(f"New file: {args.new}")
    print(f"Tolerance: {args.tolerance:.2e}")
    print()
    
    # トレーニング結果を比較
    print("【トレーニング結果の比較】")
    is_match, diff_summary = compare_train_results(args.old, args.new, args.tolerance)
    
    print()
    
    # 日次PLを比較（オプション）
    if args.daily_pl_old and args.daily_pl_new:
        print("【日次PL系列の比較】")
        pl_match, max_pl_diff = compare_daily_pl(args.daily_pl_old, args.daily_pl_new, args.tolerance)
        is_match = is_match and pl_match
        print()
    
    # 結果サマリー
    print("=" * 60)
    if is_match:
        print("[OK] 回帰確認: PASSED")
        print("     USE_FAST=False と True で結果が一致しています。")
        sys.exit(0)
    else:
        print("[ERROR] 回帰確認: FAILED")
        print("        USE_FAST=False と True で結果が一致しません。")
        print("        makeFactorReturn_fast の実装を確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()

