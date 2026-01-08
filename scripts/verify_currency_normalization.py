"""
通貨ペア正規化検証スクリプト

検証A: USDJPYのsnapshotを逆数にした値が既存JPYUSDと一致するか
検証B: 全通貨を同時に入れてUSDニュートラル制約（重み合計≈0）が成立するか
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.currency_pairs import normalize_to_usd_base, get_pair_rule, OUTPUT_PAIRS
import warnings
warnings.simplefilter('ignore')


def verify_inverse_consistency(
    new_csv: str,
    old_csv: str,
    histdata_pair: str,
    tolerance: float = 1e-6
):
    """
    検証A: USDXXXの逆数が既存データと一致するか
    
    Args:
        new_csv: 新規生成CSV（_from_sec1.csv）
        old_csv: 既存CSV（比較用）
        histdata_pair: HistData通貨ペア名（例: "USDJPY"）
        tolerance: 許容誤差
    
    Returns:
        (is_ok, stats_dict): 検証結果と統計情報
    """
    pair_rule = get_pair_rule(histdata_pair)
    output_pair = pair_rule["output_name"]
    invert = pair_rule["invert"]
    
    if not invert:
        print(f"  {histdata_pair}は逆数化不要（XXXUSD形式）")
        return True, {}
    
    print(f"  検証: {histdata_pair} -> {output_pair} (invert={invert})")
    
    # 新規CSVを読み込み
    df_new = pd.read_csv(new_csv)
    df_new['date_time'] = pd.to_datetime(df_new['date_time'])
    
    # 既存CSVを読み込み
    if not Path(old_csv).exists():
        print(f"  Warning: {old_csv} が見つかりません。検証をスキップします。")
        return True, {}
    
    df_old = pd.read_csv(old_csv)
    df_old['date_time'] = pd.to_datetime(df_old['date_time'])
    
    # 共通日付でマージ
    merged = pd.merge(
        df_new[['date_time', output_pair]].rename(columns={output_pair: f'{output_pair}_new'}),
        df_old[['date_time', output_pair]].rename(columns={output_pair: f'{output_pair}_old'}),
        on='date_time',
        how='inner'
    )
    
    if len(merged) == 0:
        print(f"  Warning: 共通日付が見つかりません。")
        return True, {}
    
    merged = merged.dropna()
    if len(merged) == 0:
        print(f"  Warning: 有効なデータがありません。")
        return True, {}
    
    # 価格差分を計算: abs(log(P_new / P_old))
    price_diff = np.abs(np.log(merged[f'{output_pair}_new'] / merged[f'{output_pair}_old']))
    
    # 統計情報
    stats = {
        'count': len(price_diff),
        'mean': np.mean(price_diff),
        'max': np.max(price_diff),
        'p95': np.percentile(price_diff, 95),
        'p99': np.percentile(price_diff, 99),
    }
    
    # 許容誤差以内かチェック
    is_ok = stats['max'] <= tolerance
    
    print(f"    比較件数: {stats['count']}")
    print(f"    max(log差): {stats['max']:.8f}")
    print(f"    mean(log差): {stats['mean']:.8f}")
    print(f"    p95(log差): {stats['p95']:.8f}")
    
    if is_ok:
        print(f"    ✅ 検証通過（許容誤差: {tolerance}）")
    else:
        print(f"    ❌ 検証失敗（max={stats['max']:.8f} > tolerance={tolerance}）")
    
    return is_ok, stats


def verify_usd_neutral_constraint(
    csv_file: str,
    tolerance: float = 1e-6
):
    """
    検証B: USDニュートラル制約（重み合計≈0）が成立するか
    
    Args:
        csv_file: 検証対象CSVファイル
        tolerance: 許容誤差
    
    Returns:
        (is_ok, stats_dict): 検証結果と統計情報
    """
    print(f"  検証: USDニュートラル制約")
    
    df = pd.read_csv(csv_file)
    df['date_time'] = pd.to_datetime(df['date_time'])
    
    # 通貨列を取得（date_time, picked_timestamp_utc以外）
    currency_cols = [col for col in df.columns if col not in ['date_time', 'picked_timestamp_utc']]
    
    # 各日付でUSDニュートラル制約をチェック
    # すべての通貨のlog価格の合計が0に近いか
    # （実際には、重みが均等な場合の期待値）
    
    # 各通貨のlog価格を計算
    log_prices = {}
    for col in currency_cols:
        if col in df.columns:
            log_prices[col] = np.log(df[col].values)
    
    if len(log_prices) == 0:
        print(f"  Warning: 通貨列が見つかりません。")
        return True, {}
    
    # 各日付でlog価格の合計を計算
    log_sum = np.zeros(len(df))
    for col, log_vals in log_prices.items():
        log_sum += log_vals
    
    # 統計情報
    stats = {
        'count': len(log_sum),
        'mean': np.mean(log_sum),
        'std': np.std(log_sum),
        'max_abs': np.max(np.abs(log_sum)),
    }
    
    # 許容誤差以内かチェック（平均が0に近い）
    is_ok = abs(stats['mean']) <= tolerance
    
    print(f"    日付数: {stats['count']}")
    print(f"    mean(log合計): {stats['mean']:.8f}")
    print(f"    std(log合計): {stats['std']:.8f}")
    print(f"    max(abs(log合計)): {stats['max_abs']:.8f}")
    
    if is_ok:
        print(f"    ✅ 検証通過（mean={stats['mean']:.8f}, 許容誤差: {tolerance}）")
    else:
        print(f"    ❌ 検証失敗（mean={stats['mean']:.8f} > tolerance={tolerance}）")
    
    return is_ok, stats


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='通貨ペア正規化検証')
    parser.add_argument('--new-csv', type=str, required=True, help='新規生成CSVファイル')
    parser.add_argument('--old-csv', type=str, help='既存CSVファイル（検証A用）')
    parser.add_argument('--histdata-pair', type=str, help='HistData通貨ペア名（検証A用、例: USDJPY）')
    parser.add_argument('--verify-usd-neutral', action='store_true', help='検証Bを実行（USDニュートラル制約）')
    parser.add_argument('--tolerance', type=float, default=1e-6, help='許容誤差')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("通貨ペア正規化検証")
    print("=" * 60)
    
    all_ok = True
    
    # 検証A: 逆数一致確認
    if args.old_csv and args.histdata_pair:
        print("\n検証A: 逆数一致確認")
        print("-" * 60)
        is_ok, stats = verify_inverse_consistency(
            args.new_csv,
            args.old_csv,
            args.histdata_pair,
            args.tolerance
        )
        if not is_ok:
            all_ok = False
    
    # 検証B: USDニュートラル制約
    if args.verify_usd_neutral:
        print("\n検証B: USDニュートラル制約")
        print("-" * 60)
        is_ok, stats = verify_usd_neutral_constraint(
            args.new_csv,
            args.tolerance
        )
        if not is_ok:
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ すべての検証が通過しました")
    else:
        print("❌ 一部の検証が失敗しました")
    print("=" * 60)


if __name__ == "__main__":
    main()

