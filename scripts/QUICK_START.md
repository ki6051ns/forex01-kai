# クイックスタートガイド

## 検証の実行順序（必須）

### Step 1: 高速化の回帰確認

```bash
# lib.py で USE_FAST = False に設定
python train.py  # 1ケースのみ実行（例：NY17TK20_A）
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv

# lib.py で USE_FAST = True に設定
python train.py  # 同じケースを実行
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# 比較
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

**期待結果**: ✅ PASSED

---

### Step 2: ベンチマーク

```bash
python scripts/bench.py
```

**期待結果**: Speedup 3.0x以上

---

### Step 3: 秒足→スナップショット（EURUSD単月で検証）

```bash
# 1. Parquet生成
python scripts/import_histdata_sec1.py \
    --currency EURUSD \
    --start-year 2002 \
    --end-year 2002

# 2. スナップショット生成
python scripts/generate_daily_snapshots.py \
    --currency EURUSD \
    --parquet-root D:/forex01_data/sec1_parquet \
    --output-root train/input/market

# 3. タイムゾーン検証
python scripts/validate_timezone_diff.py \
    --new-csv train/input/market/spot_rates_tk20.csv \
    --target-tz Asia/Tokyo \
    --target-hour 20 \
    --tolerance 30
```

**期待結果**: NG日付 = 0件

---

### Step 4: swap無害性確認

```bash
# swap=None で無害
python scripts/verify_swap_none.py

# swap定数で平行移動
python scripts/verify_swap_constant.py
```

**期待結果**: ✅ PASSED

---

## よくある落とし穴チェック

### ❌ DST（夏時間）が効いていない

```python
# 確認: zoneinfoを使用しているか
from zoneinfo import ZoneInfo
tz = ZoneInfo('America/New_York')  # ✅ OK
# tz = pytz.timezone('America/New_York')  # ❌ 古い方法
```

### ❌ picked_timestamp_utcが目標時刻を書いている

```python
# ❌ 間違い
result_df['picked_timestamp_utc'] = target_utc

# ✅ 正しい
nearest = find_nearest_second(df_day, target_utc)
result_df['picked_timestamp_utc'] = nearest.name  # 実際に選んだtick
```

### ❌ reindex後のNaNを埋めている

```python
# ❌ 間違い
df = df.reindex(common_idx).fillna(method='ffill')

# ✅ 正しい
df = df.reindex(common_idx)  # NaNはそのまま残す
# 欠損がある場合は計算をスキップ
```

---

## 次のステップ（探索）に入る条件

以下が**すべて**揃ったら、entry探索に入ってOKです。

- ✅ USE_FAST 回帰一致
- ✅ ベンチで 3倍以上
- ✅ 検証A（時刻ズレ） bad=0
- ✅ swap差し込み（Noneで無害）OK

