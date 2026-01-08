"""
タイムゾーン・差分検証（自動）

検証A（必須）:
    picked_timestamp_utcをローカル変換
    目標時刻（20:00 / 17:00）との差が±30秒以内
    NG日付は一覧で出力

検証B（補助）:
    既存spot_rates_*.csvと価格差分比較
    指標: abs(log(P_new / P_old))
    p50 / p95 / max
    外れ日をリスト化
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
import warnings
warnings.simplefilter('ignore')

# タイムゾーン処理: zoneinfo（Python 3.9+）またはpytz（フォールバック）
try:
    from zoneinfo import ZoneInfo
    USE_ZONEINFO = True
except ImportError:
    try:
        import pytz
        USE_ZONEINFO = False
        
        # ZoneInfo互換クラス
        class ZoneInfo:
            def __init__(self, key):
                self.tz = pytz.timezone(key)
            
            def __getattr__(self, name):
                return getattr(self.tz, name)
    except ImportError:
        raise ImportError("zoneinfo (Python 3.9+) or pytz is required. Install with: pip install pytz")


def validate_timezone_diff(
    csv_file: str,
    target_tz: ZoneInfo,
    target_hour: int,
    target_minute: int = 0,
    tolerance_seconds: int = 30
):
    """
    検証A: タイムゾーン差分検証
    
    Args:
        csv_file: 検証対象CSVファイル
        target_tz: 目標タイムゾーン
        target_hour: 目標時刻（時）
        target_minute: 目標時刻（分）
        tolerance_seconds: 許容誤差（秒）
    
    Returns:
        (ok_count, ng_list): OK件数とNG日付リスト
    """
    df = pd.read_csv(csv_file)
    # date_time列またはstart_time列に対応
    if 'date_time' in df.columns:
        df['date_time'] = pd.to_datetime(df['date_time'])
        time_col = 'date_time'
    elif 'start_time' in df.columns:
        df['start_time'] = pd.to_datetime(df['start_time'])
        time_col = 'start_time'
    else:
        print(f"Error: {csv_file} does not have 'date_time' or 'start_time' column")
        return 0, []
    
    if 'picked_timestamp_utc' not in df.columns:
        print(f"Warning: {csv_file} does not have 'picked_timestamp_utc' column")
        return 0, []
    
    df['picked_timestamp_utc'] = pd.to_datetime(df['picked_timestamp_utc'], utc=True)
    
    ok_count = 0
    ng_list = []
    
    for idx, row in df.iterrows():
        start_time = row[time_col]
        picked_utc = row['picked_timestamp_utc']
        
        if pd.isna(picked_utc):
            ng_list.append({
                'date': start_time,
                'reason': 'picked_timestamp_utc is NaN'
            })
            continue
        
        # picked_timestamp_utcをローカル時刻に変換
        picked_local = picked_utc.astimezone(target_tz)
        
        # 目標時刻を構築（start_timeのタイムゾーン情報を保持）
        if USE_ZONEINFO:
            # start_timeがタイムゾーン情報を持っていない場合、target_tzを適用
            if start_time.tz is None:
                start_time_tz = start_time.tz_localize(target_tz)
            else:
                start_time_tz = start_time
            target_time = start_time_tz.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        else:
            # pytzの場合
            if start_time.tz is None:
                start_time_tz = target_tz.localize(start_time)
            else:
                start_time_tz = start_time
            target_time = start_time_tz.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # 時刻差を計算（両方ともタイムゾーン付きにする）
        time_diff = abs((picked_local - target_time).total_seconds())
        
        if time_diff <= tolerance_seconds:
            ok_count += 1
        else:
            ng_list.append({
                'date': start_time,
                'target_time': target_time,
                'picked_local': picked_local,
                'diff_seconds': time_diff,
                'reason': f'Time difference {time_diff:.1f}s exceeds tolerance {tolerance_seconds}s'
            })
    
    return ok_count, ng_list


def validate_price_diff(
    new_csv: str,
    old_csv: str,
    currency: str
):
    """
    検証B: 価格差分比較
    
    Args:
        new_csv: 新規CSVファイル
        old_csv: 既存CSVファイル
        currency: 通貨ペア
    
    Returns:
        (stats_dict, outlier_list): 統計情報と外れ日リスト
    """
    df_new = pd.read_csv(new_csv)
    # date_time列またはstart_time列に対応
    if 'date_time' in df_new.columns:
        df_new['date_time'] = pd.to_datetime(df_new['date_time'])
        time_col_new = 'date_time'
    elif 'start_time' in df_new.columns:
        df_new['start_time'] = pd.to_datetime(df_new['start_time'])
        time_col_new = 'start_time'
    else:
        return {}, []
    
    df_old = pd.read_csv(old_csv)
    # date_time列またはstart_time列に対応
    if 'date_time' in df_old.columns:
        df_old['date_time'] = pd.to_datetime(df_old['date_time'])
        time_col_old = 'date_time'
    elif 'start_time' in df_old.columns:
        df_old['start_time'] = pd.to_datetime(df_old['start_time'])
        time_col_old = 'start_time'
    else:
        return {}, []
    
    # 共通日付でマージ
    merged = pd.merge(
        df_new[[time_col_new, currency]].rename(columns={currency: f'{currency}_new', time_col_new: 'date_time'}),
        df_old[[time_col_old, currency]].rename(columns={currency: f'{currency}_old', time_col_old: 'date_time'}),
        on='date_time',
        how='inner'
    )
    
    if len(merged) == 0:
        return {}, []
    
    # 価格差分を計算: abs(log(P_new / P_old))
    merged = merged.dropna()
    if len(merged) == 0:
        return {}, []
    
    price_diff = np.abs(np.log(merged[f'{currency}_new'] / merged[f'{currency}_old']))
    
    # 統計情報
    stats = {
        'count': len(price_diff),
        'p50': np.percentile(price_diff, 50),
        'p95': np.percentile(price_diff, 95),
        'p99': np.percentile(price_diff, 99),
        'max': np.max(price_diff),
        'mean': np.mean(price_diff),
        'std': np.std(price_diff)
    }
    
    # 外れ日を検出（p95を超える場合）
    threshold = stats['p95']
    outlier_mask = price_diff > threshold
    outlier_list = merged[outlier_mask][['date_time', f'{currency}_new', f'{currency}_old']].copy()
    outlier_list['price_diff'] = price_diff[outlier_mask]
    outlier_list = outlier_list.rename(columns={'date_time': 'start_time'})
    outlier_list = outlier_list.to_dict('records')
    
    return stats, outlier_list


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='タイムゾーン・差分検証')
    parser.add_argument('--new-csv', type=str, required=True, help='新規CSVファイル')
    parser.add_argument('--old-csv', type=str, help='既存CSVファイル（価格差分検証用）')
    parser.add_argument('--target-tz', type=str, default='Asia/Tokyo', help='目標タイムゾーン')
    parser.add_argument('--target-hour', type=int, default=20, help='目標時刻（時）')
    parser.add_argument('--target-minute', type=int, default=0, help='目標時刻（分）')
    parser.add_argument('--currency', type=str, help='通貨ペア（価格差分検証用）')
    parser.add_argument('--tolerance', type=int, default=30, help='許容誤差（秒）')
    
    args = parser.parse_args()
    
    # タイムゾーンオブジェクトを取得
    if USE_ZONEINFO:
        target_tz = ZoneInfo(args.target_tz)
    else:
        target_tz = pytz.timezone(args.target_tz)
    
    # 検証A: タイムゾーン差分検証
    print("=" * 60)
    print("検証A: タイムゾーン差分検証")
    print("=" * 60)
    
    ok_count, ng_list = validate_timezone_diff(
        args.new_csv,
        target_tz,
        args.target_hour,
        args.target_minute,
        args.tolerance
    )
    
    total_count = ok_count + len(ng_list)
    print(f"総件数: {total_count}")
    print(f"OK: {ok_count} ({ok_count/total_count*100:.1f}%)")
    print(f"NG (bad): {len(ng_list)} ({len(ng_list)/total_count*100:.1f}%)")
    
    if ng_list:
        print("\nNG日付一覧:")
        for ng in ng_list[:20]:  # 最初の20件のみ表示
            print(f"  {ng['date']}: {ng['reason']}")
        if len(ng_list) > 20:
            print(f"  ... (他 {len(ng_list) - 20} 件)")
    
    # 検証B: 価格差分検証（既存ファイルが指定されている場合）
    if args.old_csv and args.currency:
        print("\n" + "=" * 60)
        print("検証B: 価格差分比較")
        print("=" * 60)
        
        stats, outlier_list = validate_price_diff(
            args.new_csv,
            args.old_csv,
            args.currency
        )
        
        if stats:
            print(f"比較件数: {stats['count']}")
            print(f"価格差分 (abs(log(gen/ref))):")
            print(f"  p50: {stats['p50']:.6f}")
            print(f"  p95: {stats['p95']:.6f}")
            print(f"  max: {stats['max']:.6f}")
            print(f"  mean: {stats['mean']:.6f}")
            print(f"  std: {stats['std']:.6f}")
            
            if outlier_list:
                print(f"\n外れ日 ({len(outlier_list)} 件):")
                for outlier in outlier_list[:20]:  # 最初の20件のみ表示
                    print(f"  {outlier['start_time']}: diff={outlier['price_diff']:.6f}, "
                          f"new={outlier[f'{args.currency}_new']:.5f}, "
                          f"old={outlier[f'{args.currency}_old']:.5f}")
                if len(outlier_list) > 20:
                    print(f"  ... (他 {len(outlier_list) - 20} 件)")
        else:
            print("比較データが見つかりませんでした")
    
    print("\n検証完了!")


if __name__ == "__main__":
    main()

