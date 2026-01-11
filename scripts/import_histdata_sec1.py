"""
秒足データ取り込みパイプライン（HistData → Parquet）

入力:
    D:\forex03_data2\histdata_raw\EURUSD\sec1\
      ├─ HISTDATA_COM_NT_EURUSD_T_BIDYYYYMM.zip
      ├─ HISTDATA_COM_NT_EURUSD_T_ASKYYYYMM.zip
      └─ HISTDATA_COM_NT_EURUSD_T_LASTYYYYMM.zip

出力:
    D:\forex01_data\sec1_parquet\EURUSD_sec1_YYYYMM.parquet

列:
    timestamp_utc, bid, ask, mid, last
    mid = (bid + ask) / 2
    ※欠損時のみ last 補完可（フラグ化）
"""

import os
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import warnings
warnings.simplefilter('ignore')

# 設定
HISTDATA_ROOT = r"D:\forex03_data2\histdata_raw"
OUTPUT_ROOT = r"D:\forex01_data\sec1_parquet"
CURRENCIES = ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDJPY', 'USDCAD', 'USDCHF']
USE_LAST_AS_FALLBACK = True  # 欠損時にlastを使用するか


def parse_histdata_csv(content: str, price_type: str) -> pd.DataFrame:
    """
    HistData CSV形式をパース
    
    Args:
        content: CSV文字列
        price_type: 'BID', 'ASK', 'LAST'
    
    Returns:
        DataFrame with columns: timestamp_utc, price
    
    Note:
        HistData形式はセミコロン区切り: YYYYMMDD HHMMSS;price;volume
    """
    lines = content.strip().split('\n')
    data = []
    
    for line in lines:
        if not line.strip() or line.startswith('#'):
            continue
        
        # セミコロン区切りとカンマ区切りの両方に対応
        if ';' in line:
            parts = line.split(';')
        else:
            parts = line.split(',')
        
        if len(parts) < 2:
            continue
        
        try:
            # HistData形式: YYYYMMDD HHMMSS;price;volume または YYYYMMDD HHMMSS,price
            date_str = parts[0].strip()
            price = float(parts[1].strip())
            
            # タイムスタンプをパース
            if len(date_str) == 15:  # YYYYMMDD HHMMSS
                timestamp = pd.to_datetime(date_str, format='%Y%m%d %H%M%S', utc=True)
            elif len(date_str) == 14:  # YYYYMMDDHHMMSS
                timestamp = pd.to_datetime(date_str, format='%Y%m%d%H%M%S', utc=True)
            else:
                continue
            
            data.append({
                'timestamp_utc': timestamp,
                price_type.lower(): price
            })
        except (ValueError, IndexError):
            continue
    
    if not data:
        return pd.DataFrame(columns=['timestamp_utc', price_type.lower()])
    
    df = pd.DataFrame(data)
    df = df.set_index('timestamp_utc').sort_index()
    return df


def process_currency_month(currency: str, year: int, month: int, histdata_root: str) -> Optional[pd.DataFrame]:
    """
    特定の通貨ペア・年月の秒足データを処理
    
    Args:
        currency: 通貨ペア（例: 'EURUSD'）
        year: 年
        month: 月
        histdata_root: HistDataルートディレクトリ
    
    Returns:
        DataFrame with columns: timestamp_utc, bid, ask, mid, last
    """
    yyyymm = f"{year}{month:02d}"
    sec1_dir = Path(histdata_root) / currency / "sec1"
    
    if not sec1_dir.exists():
        return None
    
    # ZIPファイル名を構築
    bid_file = sec1_dir / f"HISTDATA_COM_NT_{currency}_T_BID{yyyymm}.zip"
    ask_file = sec1_dir / f"HISTDATA_COM_NT_{currency}_T_ASK{yyyymm}.zip"
    last_file = sec1_dir / f"HISTDATA_COM_NT_{currency}_T_LAST{yyyymm}.zip"
    
    # BIDとASKは必須
    if not bid_file.exists() or not ask_file.exists():
        return None
    
    try:
        # BIDデータを読み込み
        with zipfile.ZipFile(bid_file, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                return None
            bid_content = z.read(csv_files[0]).decode('utf-8')
            bid_df = parse_histdata_csv(bid_content, 'BID')
        
        # ASKデータを読み込み
        with zipfile.ZipFile(ask_file, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                return None
            ask_content = z.read(csv_files[0]).decode('utf-8')
            ask_df = parse_histdata_csv(ask_content, 'ASK')
        
        # LASTデータを読み込み（オプション）
        last_df = None
        if last_file.exists():
            try:
                with zipfile.ZipFile(last_file, 'r') as z:
                    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                    if csv_files:
                        last_content = z.read(csv_files[0]).decode('utf-8')
                        last_df = parse_histdata_csv(last_content, 'LAST')
            except Exception as e:
                print(f"Warning: Failed to read LAST file for {currency} {yyyymm}: {e}")
        
        # インデックスを統一して結合
        # 共通のタイムスタンプを取得
        common_idx = bid_df.index.intersection(ask_df.index)
        if len(common_idx) == 0:
            return None
        
        result_df = pd.DataFrame(index=common_idx)
        result_df['bid'] = bid_df.reindex(common_idx)['bid']
        result_df['ask'] = ask_df.reindex(common_idx)['ask']
        
        # mid = (bid + ask) / 2
        result_df['mid'] = (result_df['bid'] + result_df['ask']) / 2.0
        
        # LASTデータを追加（存在する場合）
        if last_df is not None:
            result_df['last'] = last_df.reindex(common_idx)['last']
            # 欠損時にlastで補完（フラグがTrueの場合）
            if USE_LAST_AS_FALLBACK:
                result_df['mid'] = result_df['mid'].fillna(result_df['last'])
        else:
            result_df['last'] = np.nan
        
        # インデックスを列に戻す
        result_df = result_df.reset_index()
        result_df = result_df.rename(columns={'index': 'timestamp_utc'})
        
        return result_df
        
    except Exception as e:
        print(f"Error processing {currency} {yyyymm}: {e}")
        return None


def import_currency(currency: str, histdata_root: str, output_root: str, start_year: int = 2000, end_year: int = 2025):
    """
    通貨ペアの全期間データをインポート（月単位で追記可能、重複timestampは除外）
    
    Args:
        currency: 通貨ペア
        histdata_root: HistDataルートディレクトリ
        output_root: 出力ルートディレクトリ
        start_year: 開始年
        end_year: 終了年
    """
    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {currency}...")
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            df_new = process_currency_month(currency, year, month, histdata_root)
            
            if df_new is not None and len(df_new) > 0:
                yyyymm = f"{year}{month:02d}"
                output_file = output_dir / f"{currency}_sec1_{yyyymm}.parquet"
                
                # 既存ファイルがあれば読み込んで結合
                if output_file.exists():
                    try:
                        df_existing = pd.read_parquet(output_file)
                        df_existing['timestamp_utc'] = pd.to_datetime(df_existing['timestamp_utc'], utc=True)
                        
                        # 新規データと既存データを結合
                        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                        
                        # 重複timestampを除外（最新のデータを優先）
                        df_combined = df_combined.drop_duplicates(subset=['timestamp_utc'], keep='last')
                        df_combined = df_combined.sort_values('timestamp_utc').reset_index(drop=True)
                        
                        df = df_combined
                        print(f"  Merged {currency} {yyyymm}: {len(df_new)} new records, {len(df)} total records")
                    except Exception as e:
                        print(f"  Warning: Failed to merge existing file for {currency} {yyyymm}: {e}")
                        df = df_new
                else:
                    df = df_new
                
                # Parquet形式で保存
                df.to_parquet(output_file, index=False, engine='pyarrow', compression='snappy')
                print(f"  Saved {currency} {yyyymm}: {len(df)} records")
            else:
                yyyymm = f"{year}{month:02d}"
                print(f"  Skipped {currency} {yyyymm}: No data")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HistData秒足データをParquetに変換')
    parser.add_argument('--currency', type=str, help='処理する通貨ペア（指定しない場合は全通貨）')
    parser.add_argument('--start-year', type=int, default=2000, help='開始年')
    parser.add_argument('--end-year', type=int, default=2025, help='終了年')
    parser.add_argument('--histdata-root', type=str, default=HISTDATA_ROOT, help='HistDataルートディレクトリ')
    parser.add_argument('--output-root', type=str, default=OUTPUT_ROOT, help='出力ルートディレクトリ')
    
    args = parser.parse_args()
    
    if args.currency:
        # 単一通貨のみ処理
        currencies = [args.currency]
    else:
        # 全通貨処理
        currencies = CURRENCIES
    
    for currency in currencies:
        import_currency(
            currency,
            args.histdata_root,
            args.output_root,
            args.start_year,
            args.end_year
        )
    
    print("Import completed!")


if __name__ == "__main__":
    main()

