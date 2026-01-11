"""
performance_*.csv / performance_summary_*.csv 比較スクリプト

Ground Truth（参照CSV）と現repoで生成したCSVを比較する。

- performance_*.csv: 日付（YYYY-MM-DD）で揃えて、total列の差分を確認
- performance_summary_*.csv: year列で揃えて、各指標列（sum, mean, std, sr, mdd, sortino）の差分を確認

使用方法:
    python tools/compare_performance.py --ref <ref_csv> --new <new_csv> [--type <type>]

例:
    # performance_*.csv を比較
    python tools/compare_performance.py --ref "D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"
    
    # performance_summary_*.csv を比較
    python tools/compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_summary_20250520.csv" --new "test\output\performance\performance_summary_20250520.csv" --type summary
"""
import argparse
import pandas as pd
import numpy as np
import sys
import io
from pathlib import Path

# Windows環境でのUnicodeエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_date(date_str):
    """start_timeから日付部分（YYYY-MM-DD）を抽出"""
    if isinstance(date_str, pd.Timestamp):
        return date_str.strftime('%Y-%m-%d')
    elif isinstance(date_str, str):
        # 先頭10文字を取得（YYYY-MM-DD）
        return date_str[:10]
    else:
        return str(date_str)[:10]

def compare_performance(ref_csv, new_csv, csv_type='auto'):
    """
    2つのperformance CSVを比較
    
    Args:
        ref_csv: 参照CSV（Ground Truth）
        new_csv: 比較対象CSV（現repoで生成）
        csv_type: CSVタイプ（'auto', 'performance', 'summary'）
                 'auto': ファイル名から自動判定
                 'performance': performance_*.csv 形式（start_time列あり）
                 'summary': performance_summary_*.csv 形式（year列あり）
    
    Returns:
        bool: 一致していればTrue
    """
    print("=" * 80)
    print("Performance CSV 比較")
    print("=" * 80)
    print(f"参照CSV: {ref_csv}")
    print(f"比較CSV: {new_csv}")
    print()
    
    # CSVタイプの自動判定
    if csv_type == 'auto':
        if 'performance_summary' in ref_csv.lower() or 'performance_summary' in new_csv.lower():
            csv_type = 'summary'
        else:
            csv_type = 'performance'
    
    print(f"CSVタイプ: {csv_type}")
    print()
    
    # CSV読み込み
    try:
        ref_df = pd.read_csv(ref_csv)
        new_df = pd.read_csv(new_csv)
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return False
    
    print(f"参照CSV行数: {len(ref_df)}")
    print(f"比較CSV行数: {len(new_df)}")
    print()
    
    if csv_type == 'summary':
        return compare_performance_summary(ref_df, new_df, ref_csv, new_csv)
    else:
        return compare_performance_detail(ref_df, new_df, ref_csv, new_csv)


def compare_performance_detail(ref_df, new_df, ref_csv, new_csv):
    """
    performance_*.csv 形式の比較（start_time列あり）
    """
    # start_timeをdatetime型に変換
    ref_df['start_time'] = pd.to_datetime(ref_df['start_time'])
    new_df['start_time'] = pd.to_datetime(new_df['start_time'])
    
    # 日付列を追加（YYYY-MM-DD）
    ref_df['date'] = ref_df['start_time'].apply(extract_date)
    new_df['date'] = new_df['start_time'].apply(extract_date)
    
    # dateでinner join（intersection）
    merged = pd.merge(
        ref_df[['date', 'total']].rename(columns={'total': 'ref_total'}),
        new_df[['date', 'total']].rename(columns={'total': 'new_total'}),
        on='date',
        how='inner'
    )
    
    print(f"共通日数（inner join）: {len(merged)}")
    print()
    
    if len(merged) == 0:
        print("❌ 共通日がありません。入力データや日付範囲を確認してください。")
        return False
    
    # total列の差分を計算
    merged['diff'] = merged['new_total'] - merged['ref_total']
    merged['abs_diff'] = merged['diff'].abs()
    
    # 統計情報
    max_abs_diff = merged['abs_diff'].max()
    mean_abs_diff = merged['abs_diff'].mean()
    median_abs_diff = merged['abs_diff'].median()
    std_abs_diff = merged['abs_diff'].std()
    
    print("【差分統計】")
    print(f"  最大絶対誤差（MAX）: {max_abs_diff:.15e}")
    print(f"  平均絶対誤差（MAE）: {mean_abs_diff:.15e}")
    print(f"  中央値絶対誤差: {median_abs_diff:.15e}")
    print(f"  標準偏差: {std_abs_diff:.15e}")
    print()
    
    # PASS条件チェック
    tolerance = 1e-12
    passed = max_abs_diff <= tolerance
    
    print(f"【判定】")
    if passed:
        print(f"✅ PASSED (max_abs_diff = {max_abs_diff:.15e} <= tolerance = {tolerance:.2e})")
    else:
        print(f"❌ FAILED (max_abs_diff = {max_abs_diff:.15e} > tolerance = {tolerance:.2e})")
    print()
    
    # 上位5件の差分（デバッグ用）
    top_diff = merged.nlargest(5, 'abs_diff')[['date', 'ref_total', 'new_total', 'diff', 'abs_diff']]
    
    print("【上位5件（abs_diff最大）】")
    print(top_diff.to_string(index=False))
    print()
    
    # 参照CSVにあって比較CSVにない日付
    ref_only = set(ref_df['date']) - set(new_df['date'])
    if ref_only:
        print(f"【参照CSVにのみ存在する日付（{len(ref_only)}件）】")
        for date in sorted(list(ref_only))[:10]:  # 最大10件表示
            print(f"  {date}")
        if len(ref_only) > 10:
            print(f"  ... (他 {len(ref_only) - 10} 件)")
        print()
    
    # 比較CSVにあって参照CSVにない日付
    new_only = set(new_df['date']) - set(ref_df['date'])
    if new_only:
        print(f"【比較CSVにのみ存在する日付（{len(new_only)}件）】")
        for date in sorted(list(new_only))[:10]:  # 最大10件表示
            print(f"  {date}")
        if len(new_only) > 10:
            print(f"  ... (他 {len(new_only) - 10} 件)")
        print()
    
    return passed


def compare_performance_summary(ref_df, new_df, ref_csv, new_csv):
    """
    performance_summary_*.csv 形式の比較（year列あり）
    """
    # year列でinner join（intersection）
    # year列をindexに設定（total行は除外）
    ref_df_year = ref_df[ref_df['year'] != 'total'].copy()
    new_df_year = new_df[new_df['year'] != 'total'].copy()
    
    ref_df_year['year'] = ref_df_year['year'].astype(str)
    new_df_year['year'] = new_df_year['year'].astype(str)
    
    # 比較対象の列（数値列のみ）
    numeric_cols = ['sum', 'mean', 'std', 'sr', 'mdd', 'sortino']
    available_cols = [col for col in numeric_cols if col in ref_df_year.columns and col in new_df_year.columns]
    
    if not available_cols:
        print("❌ 比較対象の数値列が見つかりません。")
        return False
    
    merged = pd.merge(
        ref_df_year[['year'] + available_cols],
        new_df_year[['year'] + available_cols],
        on='year',
        how='inner',
        suffixes=('_ref', '_new')
    )
    
    print(f"共通年数（inner join）: {len(merged)}")
    print(f"比較対象列: {', '.join(available_cols)}")
    print()
    
    if len(merged) == 0:
        print("❌ 共通年がありません。入力データを確認してください。")
        return False
    
    # 各列の差分を計算
    all_diffs = []
    for col in available_cols:
        ref_col = f'{col}_ref'
        new_col = f'{col}_new'
        merged[f'{col}_diff'] = merged[new_col] - merged[ref_col]
        merged[f'{col}_abs_diff'] = merged[f'{col}_diff'].abs()
        all_diffs.extend(merged[f'{col}_abs_diff'].values)
    
    # 統計情報（全列の差分をまとめて）
    all_diffs = pd.Series(all_diffs)
    max_abs_diff = all_diffs.max()
    mean_abs_diff = all_diffs.mean()
    median_abs_diff = all_diffs.median()
    std_abs_diff = all_diffs.std()
    
    # RMSE計算（全列の差分の二乗平均平方根）
    rmse = np.sqrt(np.mean([d**2 for d in all_diffs]))
    
    print("【差分統計（全列合計）】")
    print(f"  最大絶対誤差（MAX）: {max_abs_diff:.15e}")
    print(f"  平均絶対誤差（MAE）: {mean_abs_diff:.15e}")
    print(f"  二乗平均平方根誤差（RMSE）: {rmse:.15e}")
    print(f"  中央値絶対誤差: {median_abs_diff:.15e}")
    print(f"  標準偏差: {std_abs_diff:.15e}")
    print()
    
    # 列ごとの統計
    print("【列ごとの差分統計】")
    for col in available_cols:
        col_max = merged[f'{col}_abs_diff'].max()
        col_mae = merged[f'{col}_abs_diff'].mean()
        col_rmse = np.sqrt(np.mean(merged[f'{col}_diff']**2))
        print(f"  {col}: MAX={col_max:.15e}, MAE={col_mae:.15e}, RMSE={col_rmse:.15e}")
    print()
    
    # PASS条件チェック
    tolerance = 1e-12
    passed = max_abs_diff <= tolerance
    
    print(f"【判定】")
    if passed:
        print(f"✅ PASSED (max_abs_diff = {max_abs_diff:.15e} <= tolerance = {tolerance:.2e})")
    else:
        print(f"❌ FAILED (max_abs_diff = {max_abs_diff:.15e} > tolerance = {tolerance:.2e})")
    print()
    
    # 上位5件の差分（デバッグ用、最大abs_diffの列を表示）
    # 各年ごとの最大abs_diffを計算
    merged['max_abs_diff'] = merged[[f'{col}_abs_diff' for col in available_cols]].max(axis=1)
    top_diff = merged.nlargest(5, 'max_abs_diff')[['year'] + [f'{col}_ref' for col in available_cols] + [f'{col}_new' for col in available_cols] + ['max_abs_diff']]
    
    print("【上位5件（max_abs_diff最大）】")
    print(top_diff.to_string(index=False))
    print()
    
    # 参照CSVにあって比較CSVにない年
    ref_only = set(ref_df_year['year']) - set(new_df_year['year'])
    if ref_only:
        print(f"【参照CSVにのみ存在する年（{len(ref_only)}件）】")
        for year in sorted(list(ref_only))[:10]:  # 最大10件表示
            print(f"  {year}")
        if len(ref_only) > 10:
            print(f"  ... (他 {len(ref_only) - 10} 件)")
        print()
    
    # 比較CSVにあって参照CSVにない年
    new_only = set(new_df_year['year']) - set(ref_df_year['year'])
    if new_only:
        print(f"【比較CSVにのみ存在する年（{len(new_only)}件）】")
        for year in sorted(list(new_only))[:10]:  # 最大10件表示
            print(f"  {year}")
        if len(new_only) > 10:
            print(f"  ... (他 {len(new_only) - 10} 件)")
        print()
    
    return passed

def main():
    parser = argparse.ArgumentParser(
        description='Performance CSV比較スクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--ref', required=True, help='参照CSV（Ground Truth）のパス')
    parser.add_argument('--new', required=True, help='比較CSV（現repoで生成）のパス')
    parser.add_argument('--type', choices=['auto', 'performance', 'summary'], default='auto',
                        help='CSVタイプ（auto: 自動判定, performance: performance_*.csv, summary: performance_summary_*.csv）')
    
    args = parser.parse_args()
    
    # ファイル存在確認
    if not Path(args.ref).exists():
        print(f"❌ 参照CSVが見つかりません: {args.ref}")
        sys.exit(1)
    
    if not Path(args.new).exists():
        print(f"❌ 比較CSVが見つかりません: {args.new}")
        sys.exit(1)
    
    # 比較実行
    passed = compare_performance(args.ref, args.new, csv_type=args.type)
    
    # 終了コード
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()