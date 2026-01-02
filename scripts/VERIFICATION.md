# 検証手順（forex01-kai 高速化・秒足パイプライン）

## ⚠️ 重要：検証の順番

**この順番で実行すること。前のステップが通らない限り次に進まない。**

---

## 1. 高速化の回帰確認（最優先）

### 目的
`USE_FAST=False` と `True` で結果が完全一致すること（swapなし）

### 手順

#### 1-1. USE_FAST=False で実行

```bash
# lib.py を編集
# USE_FAST = False に設定

# 1ケースのみ実行（例：NY17→TK20 の Aのみ）
python train.py
# または、train.pyを一時的に修正して1ケースのみ実行

# 出力を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
```

#### 1-2. USE_FAST=True で実行

```bash
# lib.py を編集
# USE_FAST = True に設定

# 同じケースを実行
python train.py

# 出力を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

#### 1-3. 結果を比較

```bash
# 比較スクリプトを実行
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

### 比較基準

- ✅ **主要指標が一致**（小数誤差レベル）
  - Sharpe ratio
  - CAGR
  - Max Drawdown
  - Hit rate
- ✅ **日次PL系列の差分が極小**
  - `max(abs(diff)) < 1e-10` 程度

### ❌ 失敗時の対処

- 差分が大きい場合 → `makeFactorReturn_fast`の実装を確認
- 特に`reindex`後のNaN処理、コスト計算、PL計算の順序を確認

---

## 2. ベンチマーク（3〜8倍の確認）

### 目的
高速化の効果を数字で固定（今後の探索の前提）

### 手順

```bash
# ベンチマークを実行
python scripts/bench.py
```

### 期待結果

- ✅ **USE_FAST=True で 3倍以上**の高速化
- ✅ 最低でも1.5倍以上（それ以下ならmergeやfor通貨が残っている可能性）

### 出力例

```
Benchmark Results:
  USE_FAST=False: 45.2 seconds
  USE_FAST=True:  12.1 seconds
  Speedup: 3.7x ✅
```

### ❌ 失敗時の対処

- 1.5倍程度しか出ない場合 → `makeFactorReturn_fast`内のmerge/forループを再確認
- 特に`reindex`の使い方、NumPy行列演算の適用範囲を確認

---

## 3. 秒足→スナップショットのタイムゾーン検証（±30秒）

### 目的
時刻ズレゼロを機械的に担保（探索の土台）

### 手順

#### 3-1. EURUSD の単月でParquet生成

```bash
# 例：2002年7月のみ
python scripts/import_histdata_sec1.py \
    --currency EURUSD \
    --start-year 2002 \
    --end-year 2002

# 確認：Parquetファイルが生成されているか
ls data/sec1_parquet/EURUSD_sec1_200207.parquet
```

#### 3-2. 日次スナップショット生成

```bash
# TK20スナップショット生成
python scripts/generate_daily_snapshots.py \
    --currency EURUSD \
    --parquet-root data/sec1_parquet \
    --output-root train/input/market

# 確認：picked_timestamp_utc列が含まれているか
head -5 train/input/market/spot_rates_tk20.csv
```

#### 3-3. タイムゾーン検証（検証A）

```bash
# 検証A：時刻ズレチェック
python scripts/validate_timezone_diff.py \
    --new-csv train/input/market/spot_rates_tk20.csv \
    --target-tz Asia/Tokyo \
    --target-hour 20 \
    --target-minute 0 \
    --tolerance 30
```

### 期待結果

- ✅ **bad=0**（NG日付が0件）
- ✅ すべての日付で`picked_timestamp_utc`が目標時刻±30秒以内

### ❌ 失敗時の対処

#### よくある落とし穴

1. **DST（夏時間）が効いていない**
   - `zoneinfo`を使用しているか確認
   - `America/New_York`のDST切り替え日（3月第2日曜、11月第1日曜）を確認

2. **picked_timestamp_utcが目標時刻を書いてしまっている**
   - `generate_daily_snapshots.py`の`find_nearest_second`関数を確認
   - 実際に採用したtickの時刻を記録しているか確認

3. **reindex後のNaNを埋めてしまっている**
   - 特に祝日や欠損が混じる月で、誤った価格で計算していないか確認
   - `fillna`を使っていないか確認

---

## 4. swap差し込みの無害性確認

### 目的
swapを入れない限り結果が変わらない（回帰保証）

### 手順

#### 4-1. swap_df=None で高速版と一致確認

```python
# テストスクリプトで確認
python scripts/verify_swap_none.py
```

期待結果：
- ✅ `swap_df=None`の場合、高速版（swapなし）と完全一致

#### 4-2. swapにダミー定数を入れて平行移動確認

```python
# テストスクリプトで確認
python scripts/verify_swap_constant.py
```

期待結果：
- ✅ 全通貨に+0.0001を入れた場合、結果がその分だけ平行移動する

### ❌ 失敗時の対処

- swapがNoneでも結果が変わる場合 → `makeFactorReturn_fast`のswap処理ロジックを確認
- 平行移動しない場合 → swap計算式を確認

---

## 次のステップ（探索）に入る条件

以下が**すべて**揃ったら、entry探索（火曜、時刻グリッド、1週間固定）に入ってOKです。

- ✅ USE_FAST 回帰一致
- ✅ ベンチで 3倍以上
- ✅ 検証A（時刻ズレ） bad=0
- ✅ swap差し込み（Noneで無害）OK

---

## よくある落とし穴チェックリスト

### タイムゾーン関連

- [ ] `America/New_York`のDSTが効いているか（`zoneinfo`使用）
- [ ] `Asia/Tokyo`はDSTがないので問題なし
- [ ] DST切り替え日（3月第2日曜、11月第1日曜）で時刻が正しいか

### データ処理関連

- [ ] `picked_timestamp_utc`が「実際に採用したtick」を記録しているか
- [ ] `reindex`後のNaNを埋めていないか（特に祝日・欠損月）
- [ ] `find_nearest_second`が±30秒以内のtickを正しく選んでいるか

### 高速化関連

- [ ] `pd.merge`が完全に削除されているか
- [ ] 通貨ループ（`for ccy_ in ccyList_`）がNumPy行列演算に置き換わっているか
- [ ] `append`ループが削除されているか

---

## 検証用スクリプト一覧

- `scripts/verify_regression.py` - 回帰テスト（USE_FAST=False vs True）
- `scripts/bench.py` - ベンチマーク（速度測定）
- `scripts/verify_swap_none.py` - swap=Noneの無害性確認
- `scripts/verify_swap_constant.py` - swap定数の平行移動確認

