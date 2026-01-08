"""
swap差し込みの無害性確認（swap=None）

swap_df=None の場合、高速版（swapなし）と完全一致することを確認
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# lib.pyをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
import lib


def test_swap_none():
    """
    swap_df=None で高速版と一致することを確認
    """
    print("=" * 60)
    print("swap差し込みの無害性確認（swap=None）")
    print("=" * 60)
    
    # テストデータを準備
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    
    # ダミーのrankingデータ
    ranking = pd.DataFrame(
        index=dates,
        data=np.random.randn(50, 6),
        columns=['AUDUSD', 'CADUSD', 'CHFUSD', 'EURUSD', 'GBPUSD', 'NZDUSD']
    )
    
    # ダミーのfwdRateとspotRate
    fwdRate = pd.DataFrame({
        'start_time': dates,
        'AUDUSD': 0.7 + np.random.randn(50) * 0.01,
        'CADUSD': 0.75 + np.random.randn(50) * 0.01,
        'CHFUSD': 0.9 + np.random.randn(50) * 0.01,
        'EURUSD': 1.1 + np.random.randn(50) * 0.01,
        'GBPUSD': 1.25 + np.random.randn(50) * 0.01,
        'NZDUSD': 0.65 + np.random.randn(50) * 0.01,
    })
    
    spotRate = fwdRate.copy()
    spotRate.iloc[:, 1:] = spotRate.iloc[:, 1:] * (1 + np.random.randn(50, 6) * 0.001)
    
    # USE_FAST=True を設定
    lib.USE_FAST = True
    
    # swap=None で実行
    factorReturns_none = pd.DataFrame()
    ranking_idx = ranking.set_index(ranking.index)
    
    result_none = lib.makeFactorReturn_fast(
        factorReturns_none,
        ranking_idx,
        20,
        fwdRate,
        spotRate,
        swap_df=None
    )
    
    # swapなしで実行（既存の高速版）
    factorReturns_no_swap = pd.DataFrame()
    
    result_no_swap = lib.makeFactorReturn_fast(
        factorReturns_no_swap,
        ranking_idx,
        20,
        fwdRate,
        spotRate
    )
    
    # 結果を比較
    print("\n【結果比較】")
    
    if len(result_none) != len(result_no_swap):
        print(f"❌ 行数が不一致: none={len(result_none)}, no_swap={len(result_no_swap)}")
        return False
    
    # 列を比較
    common_cols = set(result_none.columns) & set(result_no_swap.columns)
    
    all_match = True
    tolerance = 1e-10
    
    for col in common_cols:
        if col == 'start_time':
            continue
        
        none_vals = result_none[col].values
        no_swap_vals = result_no_swap[col].values
        
        diff = np.abs(none_vals - no_swap_vals)
        max_diff = np.max(diff)
        
        if max_diff > tolerance:
            print(f"❌ {col}: max_diff={max_diff:.2e} > tolerance={tolerance:.2e}")
            all_match = False
        else:
            print(f"✅ {col}: max_diff={max_diff:.2e}")
    
    return all_match


def main():
    success = test_swap_none()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ swap=None の無害性確認: PASSED")
        print("   swap_df=None の場合、高速版（swapなし）と完全一致しています。")
        sys.exit(0)
    else:
        print("❌ swap=None の無害性確認: FAILED")
        print("   swap_df=None の場合でも結果が変わっています。")
        print("   makeFactorReturn_fast のswap処理ロジックを確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()

