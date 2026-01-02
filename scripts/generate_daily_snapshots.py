"""
秒足 → 日次スナップショット生成

Parquetファイルから日次のスナップショットを生成し、既存のCSV形式と互換性を保つ。

出力:
    train/input/market/spot_rates_tk20.csv
    train/input/market/spot_rates_ny17.csv

仕様:
    - 使用価格: mid
    - 抽出方法:
      - Asia/Tokyo 20:00
      - America/New_York 17:00
    - DST対応: zoneinfo使用
    - 「最も近い秒足」を採用
    - 出力CSVに必ずpicked_timestamp_utc列を含める（差分検証用）
"""

import pandas as pd
import numpy as np
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, time
from typing import Optional
import warnings
warnings.simplefilter('ignore')

# 設定
PARQUET_ROOT = "data/sec1_parquet"
OUTPUT_ROOT = "train/input/market"
CURRENCIES = ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDJPY', 'USDCAD', 'USDCHF']
# 通貨名のマッピング（USDJPY -> JPYUSDなど）
CURRENCY_MAPPING = {
    'USDJPY': 'JPYUSD',
    'USDCAD': 'CADUSD',
    'USDCHF': 'CHFUSD',
}


def find_nearest_second(df: pd.DataFrame, target_time: pd.Timestamp) -> Optional[pd.Series]:
    """
    最も近い秒足を取得
    
    Args:
        df: 秒足DataFrame（timestamp_utcをindexに持つ）
        target_time: 目標時刻（UTC）
    
    Returns:
        最も近い行のSeries、見つからない場合はNone
    """
    if len(df) == 0:
        return None
    
    # 目標時刻との差を計算
    time_diff = (df.index - target_time).abs()
    nearest_idx = time_diff.idxmin()
    
    # ±30秒以内かチェック（検証用）
    time_diff_seconds = abs((nearest_idx - target_time).total_seconds())
    if time_diff_seconds > 30:
        return None  # 30秒以上離れている場合はNoneを返す
    
    return df.loc[nearest_idx]


def load_parquet_month(currency: str, year: int, month: int, parquet_root: str) -> Optional[pd.DataFrame]:
    """
    特定の通貨ペア・年月のParquetファイルを読み込み
    
    Args:
        currency: 通貨ペア
        year: 年
        month: 月
        parquet_root: Parquetルートディレクトリ
    
    Returns:
        DataFrame with columns: timestamp_utc, bid, ask, mid, last
    """
    yyyymm = f"{year}{month:02d}"
    parquet_file = Path(parquet_root) / f"{currency}_sec1_{yyyymm}.parquet"
    
    if not parquet_file.exists():
        return None
    
    try:
        df = pd.read_parquet(parquet_file)
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True)
        df = df.set_index('timestamp_utc')
        return df
    except Exception as e:
        print(f"Error loading {parquet_file}: {e}")
        return None


def generate_daily_snapshots(
    currency: str,
    parquet_root: str,
    output_file: str,
    target_tz: ZoneInfo,
    target_hour: int,
    target_minute: int = 0,
    weekday: Optional[int] = None,
    start_year: int = 2000,
    end_year: int = 2025
):
    """
    日次スナップショットを生成
    
    Args:
        currency: 通貨ペア
        parquet_root: Parquetルートディレクトリ
        output_file: 出力CSVファイルパス
        target_tz: 目標タイムゾーン
        target_hour: 目標時刻（時）
        target_minute: 目標時刻（分）
        weekday: 目標曜日（0=月曜、None=全曜日）
        start_year: 開始年
        end_year: 終了年
    """
    results = []
    
    print(f"Generating snapshots for {currency} at {target_tz} {target_hour:02d}:{target_minute:02d}...")
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # 月のParquetファイルを読み込み
            df_month = load_parquet_month(currency, year, month, parquet_root)
            if df_month is None or len(df_month) == 0:
                continue
            
            # 月の各日を処理
            start_date = pd.Timestamp(year, month, 1, tzinfo=target_tz)
            if month == 12:
                end_date = pd.Timestamp(year + 1, 1, 1, tzinfo=target_tz)
            else:
                end_date = pd.Timestamp(year, month + 1, 1, tzinfo=target_tz)
            
            current_date = start_date
            while current_date < end_date:
                # 曜日チェック
                if weekday is not None and current_date.weekday() != weekday:
                    current_date += pd.Timedelta(days=1)
                    continue
                
                # 目標時刻を構築
                target_local = current_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                target_utc = target_local.astimezone(ZoneInfo('UTC'))
                
                # 該当日のデータを抽出
                day_start = target_utc.replace(hour=0, minute=0, second=0)
                day_end = day_start + pd.Timedelta(days=1)
                df_day = df_month[(df_month.index >= day_start) & (df_month.index < day_end)]
                
                if len(df_day) > 0:
                    # 最も近い秒足を取得
                    nearest = find_nearest_second(df_day, target_utc)
                    
                    if nearest is not None and not pd.isna(nearest.get('mid')):
                        results.append({
                            'start_time': target_local,  # ローカル時刻
                            'picked_timestamp_utc': nearest.name,  # 実際に選ばれたUTC時刻
                            currency: nearest['mid']  # 価格
                        })
                
                current_date += pd.Timedelta(days=1)
    
    if not results:
        print(f"  No data found for {currency}")
        return
    
    # DataFrameに変換
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('start_time').reset_index(drop=True)
    
    # 既存ファイルがあれば読み込んで結合
    output_path = Path(output_file)
    if output_path.exists():
        existing_df = pd.read_csv(output_path)
        existing_df['start_time'] = pd.to_datetime(existing_df['start_time'])
        
        # 既存データと新規データを結合（start_timeでマージ）
        result_df = pd.merge(
            existing_df,
            result_df[['start_time', currency, 'picked_timestamp_utc']],
            on='start_time',
            how='outer',
            suffixes=('', '_new')
        )
        
        # 新規データで上書き
        result_df[currency] = result_df[f'{currency}_new'].fillna(result_df[currency])
        result_df = result_df.drop(columns=[f'{currency}_new'], errors='ignore')
        
        # picked_timestamp_utcを更新
        if 'picked_timestamp_utc_new' in result_df.columns:
            result_df['picked_timestamp_utc'] = result_df['picked_timestamp_utc_new'].fillna(result_df.get('picked_timestamp_utc', pd.NaT))
            result_df = result_df.drop(columns=['picked_timestamp_utc_new'], errors='ignore')
    
    # ソート
    result_df = result_df.sort_values('start_time').reset_index(drop=True)
    
    # CSVに保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"  Saved {len(result_df)} records to {output_file}")


def generate_all_snapshots(parquet_root: str, output_root: str):
    """
    全通貨ペアのスナップショットを生成
    
    Args:
        parquet_root: Parquetルートディレクトリ
        output_root: 出力ルートディレクトリ
    """
    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # TK20: 東京時間20:00、火曜日
    tk20_file = output_dir / "spot_rates_tk20.csv"
    # NY17: ニューヨーク時間17:00、月曜日
    ny17_file = output_dir / "spot_rates_ny17.csv"
    
    # 各通貨ペアを処理
    for currency in CURRENCIES:
        # 通貨名をマッピング（USDJPY -> JPYUSDなど）
        output_currency = CURRENCY_MAPPING.get(currency, currency)
        
        # TK20スナップショット生成
        generate_daily_snapshots(
            currency=currency,
            parquet_root=parquet_root,
            output_file=str(tk20_file),
            target_tz=ZoneInfo('Asia/Tokyo'),
            target_hour=20,
            target_minute=0,
            weekday=1,  # 火曜日
        )
        
        # NY17スナップショット生成
        generate_daily_snapshots(
            currency=currency,
            parquet_root=parquet_root,
            output_file=str(ny17_file),
            target_tz=ZoneInfo('America/New_York'),
            target_hour=17,
            target_minute=0,
            weekday=0,  # 月曜日
        )


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='秒足データから日次スナップショットを生成')
    parser.add_argument('--parquet-root', type=str, default=PARQUET_ROOT, help='Parquetルートディレクトリ')
    parser.add_argument('--output-root', type=str, default=OUTPUT_ROOT, help='出力ルートディレクトリ')
    parser.add_argument('--currency', type=str, help='処理する通貨ペア（指定しない場合は全通貨）')
    
    args = parser.parse_args()
    
    if args.currency:
        # 単一通貨のみ処理
        currencies = [args.currency]
    else:
        # 全通貨処理
        currencies = CURRENCIES
    
    # 各通貨ペアを処理
    output_dir = Path(args.output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tk20_file = output_dir / "spot_rates_tk20.csv"
    ny17_file = output_dir / "spot_rates_ny17.csv"
    
    for currency in currencies:
        output_currency = CURRENCY_MAPPING.get(currency, currency)
        
        # TK20
        generate_daily_snapshots(
            currency=currency,
            parquet_root=args.parquet_root,
            output_file=str(tk20_file),
            target_tz=ZoneInfo('Asia/Tokyo'),
            target_hour=20,
            target_minute=0,
            weekday=1,
        )
        
        # NY17
        generate_daily_snapshots(
            currency=currency,
            parquet_root=args.parquet_root,
            output_file=str(ny17_file),
            target_tz=ZoneInfo('America/New_York'),
            target_hour=17,
            target_minute=0,
            weekday=0,
        )
    
    print("Snapshot generation completed!")


if __name__ == "__main__":
    main()

