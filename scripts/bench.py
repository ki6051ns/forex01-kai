"""
ベンチマークスクリプト

USE_FAST=False と True で makeFactorReturn の実行時間を比較
"""

import time
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# lib.pyをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
import lib


def benchmark_makeFactorReturn(
    use_fast: bool,
    iterations: int = 5,
    currency: str = 'EURUSD',
    year: int = 2020,
    month: int = 1
):
    """
    makeFactorReturn のベンチマーク
    
    Args:
        use_fast: USE_FASTフラグ
        iterations: 繰り返し回数
        currency: 通貨ペア
        year: 年
        month: 月
    
    Returns:
        (avg_time, min_time, max_time): 平均・最小・最大実行時間（秒）
    """
    # USE_FASTフラグを設定
    lib.USE_FAST = use_fast
    
    # テストデータを準備
    # 実際のデータを使用するか、ダミーデータを生成
    dates = pd.date_range(f'{year}-{month}-01', periods=100, freq='D')
    
    # ダミーのrankingデータ
    ranking = pd.DataFrame(
        index=dates,
        data=np.random.randn(100, 6),
        columns=['AUDUSD', 'CADUSD', 'CHFUSD', 'EURUSD', 'GBPUSD', 'NZDUSD']
    )
    
    # ダミーのfwdRateとspotRate
    fwdRate = pd.DataFrame({
        'start_time': dates,
        'AUDUSD': 0.7 + np.random.randn(100) * 0.01,
        'CADUSD': 0.75 + np.random.randn(100) * 0.01,
        'CHFUSD': 0.9 + np.random.randn(100) * 0.01,
        'EURUSD': 1.1 + np.random.randn(100) * 0.01,
        'GBPUSD': 1.25 + np.random.randn(100) * 0.01,
        'NZDUSD': 0.65 + np.random.randn(100) * 0.01,
    })
    
    spotRate = fwdRate.copy()
    spotRate.iloc[:, 1:] = spotRate.iloc[:, 1:] * (1 + np.random.randn(100, 6) * 0.001)
    
    # ウォームアップ
    factorReturns_ = pd.DataFrame()
    
    if use_fast:
        # 高速版はインデックスを期待
        ranking_idx = ranking.set_index(dates[:len(ranking)])
        _ = lib.makeFactorReturn_fast(
            factorReturns_,
            ranking_idx,
            20,
            fwdRate,
            spotRate
        )
    else:
        # 既存版はstart_time列を必要とするため、rankingをリセット
        ranking_with_time = ranking.copy()
        ranking_with_time['start_time'] = dates[:len(ranking_with_time)]
        ranking_with_time = ranking_with_time.reset_index(drop=True)
        _ = lib.makeFactorReturn(
            factorReturns_,
            ranking_with_time,
            20,
            fwdRate,
            spotRate
        )
    
    # ベンチマーク実行
    times = []
    
    for i in range(iterations):
        factorReturns_ = pd.DataFrame()
        
        start_time = time.time()
        
        if use_fast:
            # 高速版はインデックスを期待
            ranking_idx = ranking.set_index(dates[:len(ranking)])
            _ = lib.makeFactorReturn_fast(
                factorReturns_,
                ranking_idx,
                20,
                fwdRate,
                spotRate
            )
        else:
            # 既存版はstart_time列を必要とする
            ranking_with_time = ranking.copy()
            ranking_with_time['start_time'] = dates[:len(ranking_with_time)]
            ranking_with_time = ranking_with_time.reset_index(drop=True)
            _ = lib.makeFactorReturn(
                factorReturns_,
                ranking_with_time,
                20,
                fwdRate,
                spotRate
            )
        
        elapsed = time.time() - start_time
        times.append(elapsed)
    
    return np.mean(times), np.min(times), np.max(times)


def benchmark_full_pipeline(
    use_fast: bool,
    iterations: int = 3
):
    """
    フルパイプラインのベンチマーク（makeFactorReturnA/B/Cを含む）
    
    Args:
        use_fast: USE_FASTフラグ
        iterations: 繰り返し回数
    
    Returns:
        (avg_time, min_time, max_time): 平均・最小・最大実行時間（秒）
    """
    # USE_FASTフラグを設定
    lib.USE_FAST = use_fast
    
    # 実際のデータを使用（既存のデータが読み込まれている前提）
    times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        # makeFactorReturnA_NY17を実行（1ケースのみ）
        factorReturns_ = pd.DataFrame()
        _ = lib.makeFactorReturnA_NY17(factorReturns_, position_id_=0)
        
        elapsed = time.time() - start_time
        times.append(elapsed)
    
    return np.mean(times), np.min(times), np.max(times)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ベンチマーク実行')
    parser.add_argument('--iterations', type=int, default=5, help='繰り返し回数')
    parser.add_argument('--full', action='store_true', help='フルパイプラインをベンチマーク')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ベンチマーク: makeFactorReturn の実行時間比較")
    print("=" * 60)
    print(f"Iterations: {args.iterations}")
    print()
    
    if args.full:
        # フルパイプライン
        print("【フルパイプライン】")
        print("USE_FAST=False...")
        avg_false, min_false, max_false = benchmark_full_pipeline(False, args.iterations)
        print(f"  Average: {avg_false:.3f}s (min: {min_false:.3f}s, max: {max_false:.3f}s)")
        
        print("USE_FAST=True...")
        avg_true, min_true, max_true = benchmark_full_pipeline(True, args.iterations)
        print(f"  Average: {avg_true:.3f}s (min: {min_true:.3f}s, max: {max_true:.3f}s)")
    else:
        # makeFactorReturnのみ
        print("【makeFactorReturn のみ】")
        print("USE_FAST=False...")
        avg_false, min_false, max_false = benchmark_makeFactorReturn(False, args.iterations)
        print(f"  Average: {avg_false:.3f}s (min: {min_false:.3f}s, max: {max_false:.3f}s)")
        
        print("USE_FAST=True...")
        avg_true, min_true, max_true = benchmark_makeFactorReturn(True, args.iterations)
        print(f"  Average: {avg_true:.3f}s (min: {min_true:.3f}s, max: {max_true:.3f}s)")
    
    print()
    print("=" * 60)
    speedup = avg_false / avg_true
    print(f"Speedup: {speedup:.2f}x")
    
    if speedup >= 3.0:
        print("[OK] 目標達成（3倍以上）")
        sys.exit(0)
    elif speedup >= 1.5:
        print("[WARNING] 改善あり（1.5倍以上）が、目標未達")
        print("          makeFactorReturn_fast の実装を再確認してください。")
        sys.exit(0)
    else:
        print("[ERROR] 改善が不十分（1.5倍未満）")
        print("        pd.merge や for通貨ループが残っている可能性があります。")
        sys.exit(1)


if __name__ == "__main__":
    main()

