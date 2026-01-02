# forex01-kai 改修スクリプト

## 概要

forex01-kaiプロジェクトの高速化とデータ主権確立のためのスクリプト集です。

## 実装内容

### ✅ タスク1: lib.py高速化
- `makeFactorReturn_fast`関数を実装
- `pd.merge`を全面禁止し、`reindex`に置換
- 通貨ループを廃止し、NumPy行列演算で一括計算
- コスト計算の`append`ループを廃止
- `USE_FAST`フラグで既存版/高速版を切り替え可能
- スワップ損益を後付けできる設計（`swap_df`パラメータ）

### ✅ タスク2: 秒足データ取り込みパイプライン
- `scripts/import_histdata_sec1.py`
- HistData ZIPファイルからParquet形式に変換
- 月単位で分割保存
- 列: `timestamp_utc`, `bid`, `ask`, `mid`, `last`

### ✅ タスク3: 秒足→日次スナップショット生成
- `scripts/generate_daily_snapshots.py`
- Parquetファイルから日次スナップショットを生成
- TK20（東京20:00、火曜日）とNY17（NY17:00、月曜日）を抽出
- DST対応（zoneinfo使用）
- 最も近い秒足を採用（±30秒以内）
- `picked_timestamp_utc`列を含める（検証用）

### ✅ タスク4: タイムゾーン差分検証
- `scripts/validate_timezone_diff.py`
- 検証A: タイムゾーン差分検証（±30秒以内）
- 検証B: 既存データとの価格差分比較

## 使用方法

### 1. 秒足データの取り込み

```bash
# 全通貨を処理
python scripts/import_histdata_sec1.py

# 特定の通貨のみ処理
python scripts/import_histdata_sec1.py --currency EURUSD

# 期間を指定
python scripts/import_histdata_sec1.py --start-year 2020 --end-year 2024
```

**入力**: `D:\forex03_data2\histdata_raw\{CURRENCY}\sec1\HISTDATA_COM_NT_{CURRENCY}_T_*.zip`  
**出力**: `data/sec1_parquet/{CURRENCY}_sec1_{YYYYMM}.parquet`

### 2. 日次スナップショットの生成

```bash
# 全通貨を処理
python scripts/generate_daily_snapshots.py

# 特定の通貨のみ処理
python scripts/generate_daily_snapshots.py --currency EURUSD

# カスタムパス
python scripts/generate_daily_snapshots.py --parquet-root data/sec1_parquet --output-root train/input/market
```

**入力**: `data/sec1_parquet/{CURRENCY}_sec1_{YYYYMM}.parquet`  
**出力**: 
- `train/input/market/spot_rates_tk20.csv`
- `train/input/market/spot_rates_ny17.csv`

### 3. タイムゾーン差分検証

```bash
# 検証Aのみ（タイムゾーン差分）
python scripts/validate_timezone_diff.py \
    --new-csv train/input/market/spot_rates_tk20.csv \
    --target-tz Asia/Tokyo \
    --target-hour 20

# 検証A + 検証B（価格差分比較）
python scripts/validate_timezone_diff.py \
    --new-csv train/input/market/spot_rates_tk20.csv \
    --old-csv train/input/market/old/spot_rates_tk20.csv \
    --currency EURUSD \
    --target-tz Asia/Tokyo \
    --target-hour 20
```

## lib.pyの使用方法

### 高速化版の有効化

```python
# lib.pyの先頭で設定
USE_FAST = True  # 高速版を使用
USE_FAST = False  # 既存版を使用（互換性確認用）
```

### スワップ損益の追加（将来拡張）

```python
# スワップ損益DataFrameを準備
swap_df = pd.DataFrame({
    'start_time': [...],
    'EURUSD': [...],  # 1週間保有あたりのリターン率
    'GBPUSD': [...],
    ...
})

# makeFactorReturnA/B/Cに渡す
factorReturns_ = makeFactorReturnA(
    fwdRateFactor_,
    factorReturns_,
    position_id_,
    fwdRatePosition_,
    spotRate_,
    swap_df=swap_df  # スワップ損益を追加
)
```

## 注意事項

1. **Parquetファイルの依存関係**
   - `pyarrow`パッケージが必要です: `pip install pyarrow`

2. **タイムゾーン処理**
   - Python 3.9+が必要（`zoneinfo`モジュール使用）
   - DST（夏時間）は自動で処理されます

3. **既存データとの互換性**
   - 出力CSVの列名とフォーマットは既存仕様と完全互換
   - `picked_timestamp_utc`列が追加されますが、既存コードには影響しません

4. **性能改善**
   - `USE_FAST = True`で3〜8倍の高速化が期待されます
   - まずEURUSD単一ペア・単月で検証してから全展開することを推奨

## ファイル構成

```
forex01-kai/
├── lib.py                          # 高速化版実装済み
├── scripts/
│   ├── import_histdata_sec1.py     # タスク2: HistData→Parquet
│   ├── generate_daily_snapshots.py # タスク3: 日次スナップショット生成
│   ├── validate_timezone_diff.py   # タスク4: タイムゾーン検証
│   ├── verify_regression.py         # 検証: 回帰確認
│   ├── bench.py                    # 検証: ベンチマーク
│   ├── verify_swap_none.py         # 検証: swap=None無害性
│   ├── verify_swap_constant.py     # 検証: swap定数平行移動
│   ├── VERIFICATION.md             # 検証手順詳細
│   └── README.md                   # このファイル
└── data/
    └── sec1_parquet/               # Parquetファイル保存先
```

## 検証手順

**重要**: 実装後は必ず検証を実行してください。詳細は `VERIFICATION.md` を参照。

### クイック検証

```bash
# 1. 高速化の回帰確認
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# 2. ベンチマーク
python scripts/bench.py

# 3. タイムゾーン検証
python scripts/validate_timezone_diff.py \
    --new-csv train/input/market/spot_rates_tk20.csv \
    --target-tz Asia/Tokyo \
    --target-hour 20

# 4. swap無害性確認
python scripts/verify_swap_none.py
python scripts/verify_swap_constant.py
```

### 検証の順番（重要）

1. **高速化の回帰確認**（最優先）
2. **ベンチマーク**（3倍以上を確認）
3. **タイムゾーン検証**（±30秒以内）
4. **swap無害性確認**（Noneで無害、定数で平行移動）

詳細は `VERIFICATION.md` を参照してください。

## トラブルシューティング

### Parquetファイルが読み込めない
- `pyarrow`がインストールされているか確認: `pip install pyarrow`

### タイムゾーンエラー
- Python 3.9以上を使用しているか確認
- `zoneinfo`モジュールが利用可能か確認

### 既存データとの差分が大きい
- `validate_timezone_diff.py`で検証を実行
- NG日付の原因を確認（データ欠損、DST切り替え日など）

