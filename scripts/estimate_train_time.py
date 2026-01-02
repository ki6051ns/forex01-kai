"""
train.pyの計算時間を推定するスクリプト
"""

import itertools

# パラメータ設定
REF_PERIOD_WIDTH = [12, 25, 50, 100, 150]  # 5通り
TRADE_PERIOD_WIDTH = [5, 12, 25, 50]  # 4通り
NUMBER_OF_PARAMETERS = [1, 3, 5, 10]  # 4通り
NUMBER_OF_HYPERPARAMETER = 4

FACTOR_CALCULATION_PERIOD_A = range(20, 31, 1)  # 11回
FACTOR_CALCULATION_PERIOD_B = range(100, 155, 5)  # 11回
FACTOR_CALCULATION_PERIOD_C = range(1, 13, 1)  # 12回

# シミュレーション期間
TRAIN_PERIOD_TO_A = range(2005, 2024)  # 19年
TRAIN_PERIOD_TO_B = range(2006, 2024)  # 18年
TRAIN_PERIOD_TO_C = range(2005, 2024)  # 19年

# ポジション関数の数（実際の値）
# position_functions_6.csv と position_functions_7.csv から読み込まれる
POSITION_FUNCTIONS_COUNT = 26  # 実際の値

# ベンチマーク結果（makeFactorReturn_fast）
# USE_FAST=False: 0.031秒
# USE_FAST=True: 0.003秒
# Speedup: 10倍

# 1回のmakeFactorReturn_fastの実行時間（高速化版）
MAKEFACTORRETURN_FAST_TIME = 0.003  # 秒

# その他の処理時間（rolling().std().rank()など）
# makeFactorReturn_fastの10倍の時間がかかると仮定（保守的）
OTHER_PROCESSING_TIME = 0.03  # 秒

# 1回のmakeFactorReturn呼び出しの総時間
SINGLE_MAKEFACTORRETURN_TIME = MAKEFACTORRETURN_FAST_TIME + OTHER_PROCESSING_TIME

# simulate()関数の計算量
def estimate_simulate_time():
    """simulate()関数の実行時間を推定"""
    # REF_PERIOD_WIDTH × TRADE_PERIOD_WIDTH × NUMBER_OF_PARAMETERS
    combinations = len(REF_PERIOD_WIDTH) * len(TRADE_PERIOD_WIDTH) * len(NUMBER_OF_PARAMETERS)
    # 各組み合わせでsimulateIndividualStrategyForSimを実行
    # 1回のsimulateIndividualStrategyForSimは、データ量に依存するが、仮に0.1秒と仮定
    simulate_individual_time = 0.1  # 秒
    return combinations * simulate_individual_time


# train()関数の計算量
def estimate_train_time(strategy_type='A'):
    """train()関数の実行時間を推定"""
    
    # FACTOR_CALCULATION_PERIODの回数
    if strategy_type == 'A':
        factor_periods = len(list(FACTOR_CALCULATION_PERIOD_A))
        simulation_periods = len(list(TRAIN_PERIOD_TO_A))
    elif strategy_type == 'B':
        factor_periods = len(list(FACTOR_CALCULATION_PERIOD_B))
        simulation_periods = len(list(TRAIN_PERIOD_TO_B))
    else:  # C
        factor_periods = len(list(FACTOR_CALCULATION_PERIOD_C))
        simulation_periods = len(list(TRAIN_PERIOD_TO_C))
    
    # ポジション関数の組み合わせ数
    position_combinations = len(list(itertools.combinations_with_replacement(
        range(0, POSITION_FUNCTIONS_COUNT), 2
    )))
    
    # makeFactorReturnの呼び出し回数
    # 各ポジション関数の組み合わせで、factor_periods回呼び出される
    makeFactorReturn_calls = position_combinations * factor_periods
    
    # makeFactorReturnの総時間
    makeFactorReturn_total_time = makeFactorReturn_calls * SINGLE_MAKEFACTORRETURN_TIME
    
    # simulate()の呼び出し回数
    simulate_calls = position_combinations
    
    # simulate()の総時間
    simulate_total_time = simulate_calls * estimate_simulate_time()
    
    # その他の処理（weight計算など）
    # 各ポジション関数の組み合わせでcalculateWeightを呼び出す
    other_time = position_combinations * 0.01  # 仮に0.01秒
    
    total_time = makeFactorReturn_total_time + simulate_total_time + other_time
    
    return {
        'makeFactorReturn_calls': makeFactorReturn_calls,
        'makeFactorReturn_time': makeFactorReturn_total_time,
        'simulate_calls': simulate_calls,
        'simulate_time': simulate_total_time,
        'other_time': other_time,
        'total_time': total_time
    }


def main():
    print("=" * 60)
    print("train.py の計算時間推定")
    print("=" * 60)
    print()
    
    print("【パラメータ設定】")
    print(f"  ポジション関数の数（仮定）: {POSITION_FUNCTIONS_COUNT}")
    print(f"  REF_PERIOD_WIDTH: {len(REF_PERIOD_WIDTH)}通り")
    print(f"  TRADE_PERIOD_WIDTH: {len(TRADE_PERIOD_WIDTH)}通り")
    print(f"  NUMBER_OF_PARAMETERS: {len(NUMBER_OF_PARAMETERS)}通り")
    print(f"  simulate()の組み合わせ数: {len(REF_PERIOD_WIDTH) * len(TRADE_PERIOD_WIDTH) * len(NUMBER_OF_PARAMETERS)}通り")
    print()
    
    print("【各戦略の計算時間推定】")
    print()
    
    total_time_all = 0
    
    for strategy_type in ['A', 'B', 'C']:
        result = estimate_train_time(strategy_type)
        total_time_all += result['total_time']
        
        print(f"戦略{strategy_type}:")
        print(f"  makeFactorReturn呼び出し回数: {result['makeFactorReturn_calls']:,}")
        print(f"  makeFactorReturn時間: {result['makeFactorReturn_time']:.1f}秒 ({result['makeFactorReturn_time']/60:.1f}分)")
        print(f"  simulate呼び出し回数: {result['simulate_calls']:,}")
        print(f"  simulate時間: {result['simulate_time']:.1f}秒 ({result['simulate_time']/60:.1f}分)")
        print(f"  その他: {result['other_time']:.1f}秒")
        print(f"  合計: {result['total_time']:.1f}秒 ({result['total_time']/60:.1f}分)")
        print()
    
    print("=" * 60)
    print("【全体の推定時間】")
    print("=" * 60)
    print(f"全6プロセス（並列実行）:")
    print(f"  最長プロセスの時間: {total_time_all/6:.1f}秒 ({total_time_all/6/60:.1f}分)")
    print(f"  全プロセスの合計時間: {total_time_all:.1f}秒 ({total_time_all/60:.1f}分)")
    print()
    print("【注意事項】")
    print("  - これは推定値です。実際の時間はデータ量やシステム性能に依存します。")
    print("  - USE_FAST=True で約10倍高速化されていることを考慮しています。")
    print("  - 並列処理により、6プロセスが同時実行されます。")
    print("  - 実際のポジション関数の数は position_functions_*.csv から読み込まれます。")
    print("  - データ量が多い場合、時間が長くなる可能性があります。")


if __name__ == "__main__":
    main()

