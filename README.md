# forex01-kai 改修プロジェクト

## 📋 プロジェクト概要

forex01-kaiは外国為替（FX）トレーディング戦略のバックテスト・トレーニングシステムです。本改修では、**計算高速化**と**データ主権の確立**を実現します。

## 🎯 改修の目的

1. **計算高速化を最優先**（エントリーポイント探索を現実的時間で回す）
2. **データ主権の確立**（Bloomberg依存排除、秒足→自前生成）
3. **将来拡張**（スワップ損益）を後付け可能にする

---

## ✅ 1st_commit: 土台固定（Implemented）

### 🚀 lib.py高速化

**実装内容**:
- `makeFactorReturn_fast`関数を実装
- `pd.merge`を全面禁止し、`reindex`に置換
- 通貨ループ（`for ccy_ in ccyList_`）を廃止し、NumPy行列演算で一括計算
- コスト計算の`append`ループを廃止
- `USE_FAST`フラグで既存版/高速版を切り替え可能（デフォルト: `True`）

**性能改善**:
- ベンチマーク結果: **約7.5倍の高速化**（目標3倍を上回る）
- 回帰確認: USE_FAST=False と True で結果が完全一致

**使用方法**:
```python
# lib.pyの先頭で設定
USE_FAST = True  # 高速版を使用（デフォルト）
USE_FAST = False  # 既存版を使用（互換性確認用）
```

### 💰 スワップ損益（インターフェースのみ）

**実装内容**:
- `makeFactorReturn_fast`に`swap_df`パラメータを追加（インターフェース定義）
- スワップが`None`の場合は現行結果と完全一致（回帰保証）
- スワップがある場合: `pnl_total = pnl_price + pnl_swap`（将来実装）

**使用方法**:
```python
# スワップ損益DataFrameを準備（将来実装）
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
    swap_df=swap_df  # スワップ損益を追加（将来実装）
)
```

### 🔍 検証スクリプト

**実装内容**:
- `scripts/bench.py`: ベンチマーク実行（USE_FAST=False vs True）
- `scripts/verify_regression.py`: 回帰確認（結果の一致確認）
- `scripts/check_use_fast.py`: USE_FASTフラグの確認

**使用方法**:
```bash
# ベンチマーク
python scripts/bench.py

# 回帰確認
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# USE_FASTフラグ確認
python scripts/check_use_fast.py
```

### 📊 検証結果

- **ベンチマーク**: 約7.5倍の高速化（USE_FAST=False: 0.043秒 → USE_FAST=True: 0.006秒）
- **回帰確認**: USE_FAST=False と True で結果が完全一致（すべての列で差分0）

---

---

## ✅ 2nd_commit: データパイプライン（Implemented）

### 📊 HistData → Parquet → Snapshot パイプライン

**実装内容**:
- `scripts/import_histdata_sec1.py`: HistData ZIPファイルからParquet形式に変換
- `scripts/generate_daily_snapshots.py`: Parquetファイルから日次スナップショットを生成
- `scripts/validate_timezone_diff.py`: タイムゾーン・差分検証

**入力**: `D:\forex03_data2\histdata_raw\{CURRENCY}\sec1\HISTDATA_COM_NT_{CURRENCY}_T_*.zip`  
**出力**: 
- `D:\forex01_data\sec1_parquet\{CURRENCY}_sec1_{YYYYMM}.parquet`
- `train/input/market/spot_rates_tk20_from_sec1.csv`
- `train/input/market/spot_rates_ny17_from_sec1.csv`

### 🚀 実行手順（コピペ用）

#### Step 0: データディレクトリの準備（初回のみ）

**注意**: `sec1_parquet`ディレクトリはCursorのSync負荷軽減のため、Dドライブに配置します。

**既存データを移動する場合（PowerShell）:**
```powershell
# ディレクトリ作成
New-Item -ItemType Directory -Path "D:\forex01_data\sec1_parquet" -Force

# 既存データを移動（repo配下からDドライブへ）
Move-Item -Path "data\sec1_parquet\*" -Destination "D:\forex01_data\sec1_parquet\" -Force

# 空のディレクトリを削除（オプション）
Remove-Item -Path "data\sec1_parquet" -Force -ErrorAction SilentlyContinue
```

**新規セットアップの場合:**
- ディレクトリは自動生成されます（スクリプト実行時に`mkdir(parents=True, exist_ok=True)`で作成）

#### Step 1: HistData ZIP → Parquet変換

**PowerShell（Windows）の場合:**

```powershell
# EURUSD単月の例（2002年7月）
python scripts/import_histdata_sec1.py --currency EURUSD --start-year 2002 --end-year 2002 --histdata-root "D:\forex03_data2\histdata_raw"

# 全通貨・全期間（時間がかかります）
python scripts/import_histdata_sec1.py --histdata-root "D:\forex03_data2\histdata_raw"
```

**bash（Linux/Mac）の場合:**

```bash
# EURUSD単月の例（2002年7月）
python scripts/import_histdata_sec1.py \
    --currency EURUSD \
    --start-year 2002 \
    --end-year 2002 \
    --histdata-root "D:\forex03_data2\histdata_raw"

# 全通貨・全期間（時間がかかります）
python scripts/import_histdata_sec1.py \
    --histdata-root "D:\forex03_data2\histdata_raw"
```

#### Step 2: Parquet → 日次スナップショット生成

**PowerShell（Windows）の場合:**

```powershell
# EURUSD単月の例
python scripts/generate_daily_snapshots.py --currency EURUSD --parquet-root "D:\forex01_data\sec1_parquet" --output-root "train/input/market"

# 全通貨
python scripts/generate_daily_snapshots.py --parquet-root "D:\forex01_data\sec1_parquet" --output-root "train/input/market"
```

**bash（Linux/Mac）の場合:**

```bash
# EURUSD単月の例
python scripts/generate_daily_snapshots.py \
    --currency EURUSD \
    --parquet-root "D:\forex01_data\sec1_parquet" \
    --output-root "train/input/market"

# 全通貨
python scripts/generate_daily_snapshots.py \
    --parquet-root "D:\forex01_data\sec1_parquet" \
    --output-root "train/input/market"
```

#### Step 3: タイムゾーン検証

**PowerShell（Windows）の場合:**

```powershell
# TK20検証
python scripts/validate_timezone_diff.py --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" --target-tz "Asia/Tokyo" --target-hour 20 --tolerance 30

# NY17検証
python scripts/validate_timezone_diff.py --new-csv "train/input/market/spot_rates_ny17_from_sec1.csv" --target-tz "America/New_York" --target-hour 17 --tolerance 30

# 価格差分検証（既存CSVと比較）
python scripts/validate_timezone_diff.py --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" --old-csv "train/input/market/spot_rates_tk20.csv" --target-tz "Asia/Tokyo" --target-hour 20 --currency EURUSD --tolerance 30
```

**bash（Linux/Mac）の場合:**

```bash
# TK20検証
python scripts/validate_timezone_diff.py \
    --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" \
    --target-tz "Asia/Tokyo" \
    --target-hour 20 \
    --tolerance 30

# NY17検証
python scripts/validate_timezone_diff.py \
    --new-csv "train/input/market/spot_rates_ny17_from_sec1.csv" \
    --target-tz "America/New_York" \
    --target-hour 17 \
    --tolerance 30

# 価格差分検証（既存CSVと比較）
python scripts/validate_timezone_diff.py \
    --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" \
    --old-csv "train/input/market/spot_rates_tk20.csv" \
    --target-tz "Asia/Tokyo" \
    --target-hour 20 \
    --currency EURUSD \
    --tolerance 30
```

### 📋 仕様詳細

#### import_histdata_sec1.py

- **入力**: HistData ZIPファイル（BID/ASK/LAST）
- **出力**: Parquetファイル（`timestamp_utc`, `bid`, `ask`, `mid`, `last`）
- **特徴**:
  - `mid = (bid + ask) / 2`
  - 欠損時は原則NaN（`USE_LAST_AS_FALLBACK`フラグでlast補完可）
  - 月単位で追記可能（重複timestampは除外）

#### generate_daily_snapshots.py

- **入力**: Parquetファイル
- **出力**: `spot_rates_tk20_from_sec1.csv`, `spot_rates_ny17_from_sec1.csv`
- **特徴**:
  - 価格は`mid`を使用
  - 抽出は「最も近い秒足」（±30秒以内）
  - `picked_timestamp_utc`列を付与（検証用）
  - TK20: Asia/Tokyo 20:00（火曜日）
  - NY17: America/New_York 17:00（月曜日、DST対応）

#### validate_timezone_diff.py

- **検証A（必須）**: 目標時刻との差（秒）→ bad件数（許容±30秒）
- **検証B（補助）**: 価格差分（`abs(log(gen/ref))`）のp50/p95/max、外れ日一覧

### 📝 picked_timestamp_utc列について

`picked_timestamp_utc`列は、実際に選ばれた秒足のUTC時刻を記録します。これにより、目標時刻（TK20/NY17）との差分を検証できます。既存コードには影響しません（追加列のみ）。

### 💱 通貨ペア正規化ルール（USD基準統一）

**設計原則**:
- 内部表現はUSD基準（USDニュートラル）に統一
- すべて「USD / 通貨」表現に正規化
- HistDataの元表記（EURUSD/USDJPYなど）は入口で吸収

**正規化ルール**:
- **XXXUSD**（EURUSD, GBPUSD, AUDUSD, NZDUSD）: そのまま使用
- **USDXXX**（USDJPY, USDCAD, USDCHF）: 逆数にする（1 / USDJPY → JPYUSD）

**実装**:
- `config/currency_pairs.py`: 通貨ペア正規化ルール定義
- `scripts/generate_daily_snapshots.py`: snapshot生成時に自動正規化
- CSV列名は正規化後の通貨名（JPYUSD, CADUSD, CHFUSD）

**検証**:
```powershell
# 検証A: USDJPY→JPYUSDの逆数一致確認
python scripts/verify_currency_normalization.py --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" --old-csv "train/input/market/spot_rates_tk20.csv" --histdata-pair USDJPY

# 検証B: USDニュートラル制約
python scripts/verify_currency_normalization.py --new-csv "train/input/market/spot_rates_tk20_from_sec1.csv" --verify-usd-neutral
```

### 🔍 ファクターリターン誤差評価

**実装内容**:
- `scripts/compare_factor_returns.py`: 旧spotデータとsec1から生成したspotデータのファクターリターン誤差を評価
- `lib.py`: spot読み込み関数にsuffixパラメータを追加（データソース切替可能）

**評価指標**:
- **MAE**: Mean Absolute Error（平均絶対誤差）
- **RMSE**: Root Mean Squared Error（二乗平均平方根誤差）
- **MAX**: 最大絶対誤差

**注意事項**:
- 日付は**intersection（共通日）**に揃える
- `picked_timestamp_utc`列は比較には不要なので自動除外

**使用方法**:

**PowerShell（Windows）の場合:**

```powershell
# TK20 × StrategyA × 2015-2025
python scripts/compare_factor_returns.py --tz TK20 --strategy A --start-date 2015-01-01 --end-date 2025-12-31 --old-suffix '""' --new-suffix "_from_sec1"

# NY17 × StrategyB × 全期間
python scripts/compare_factor_returns.py --tz NY17 --strategy B --old-suffix '""' --new-suffix "_from_sec1"

# 結果をCSV保存
python scripts/compare_factor_returns.py --tz TK20 --strategy A --start-date 2015-01-01 --end-date 2025-12-31 --old-suffix '""' --new-suffix "_from_sec1" --output results/factor_return_comparison.csv
```

**bash（Linux/Mac）の場合:**

```bash
# TK20 × StrategyA × 2015-2025
python scripts/compare_factor_returns.py \
    --tz TK20 \
    --strategy A \
    --start-date 2015-01-01 \
    --end-date 2025-12-31 \
    --old-suffix "" \
    --new-suffix "_from_sec1"

# NY17 × StrategyB × 全期間
python scripts/compare_factor_returns.py \
    --tz NY17 \
    --strategy B \
    --old-suffix "" \
    --new-suffix "_from_sec1"

# 結果をCSV保存
python scripts/compare_factor_returns.py \
    --tz TK20 \
    --strategy A \
    --start-date 2015-01-01 \
    --end-date 2025-12-31 \
    --old-suffix "" \
    --new-suffix "_from_sec1" \
    --output results/factor_return_comparison.csv
```

**出力例**:
```
============================================================
ファクターリターン比較結果
============================================================
TZ: TK20
Strategy: A
開始日: 2015-01-01
終了日: 2025-12-31

n (共通日数): 520
MAE: 0.00001234
RMSE: 0.00002345
MAX (abs diff): 0.00012345

上位10件（abs(diff)最大）:
------------------------------------------------------------
  2015-03-10: r_old=0.00123456, r_new=0.00134567, diff=0.00011111
  ...
```

### ✅ Done条件（2nd_commitの合格ライン）

- ✅ EURUSD単月でzip→parquet→snapshotが完走
- ✅ `validate_timezone_diff.py`検証Aがbad=0
- ✅ 生成CSVに`picked_timestamp_utc`が入っている
- ✅ READMEに手順が書いてある
- ✅ `compare_factor_returns.py`でファクターリターン誤差評価が可能

---

## ✅ 3rd_commit: データソース切替機能（Implemented）

### 🔄 動的データソース切替

**実装内容**:
- `lib.py`: `init_spot_globals()`関数を追加し、実行時にspotデータソースを切替可能に
- `test_prod.py`, `train.py`: 環境変数`SPOT_SUFFIX`によるspotデータ切替対応
- 段階的なデータ移行に対応（段階1: testのみ新データ、段階2: trainから新データ）

**機能**:
- 環境変数`SPOT_SUFFIX`でspotファイルのサフィックスを指定
  - `SPOT_SUFFIX=""`: 旧データ（`spot_rates_*.csv`）
  - `SPOT_SUFFIX="_from_sec1"`: 新データ（`spot_rates_*_from_sec1.csv`）
- `lib.init_spot_globals(spot_suffix)`でグローバル変数を再初期化
- ログ出力（`[SPOT] loading: ...`）で使用中のファイルを確認可能

**使用方法**:
```powershell
# 新データでtest_prod.pyを実行
$env:SPOT_SUFFIX = "_from_sec1"
python test_prod.py 2025-05-20

# 新データでtrain.pyを実行
$env:SPOT_SUFFIX = "_from_sec1"
python train.py
```

### 📊 比較スクリプト拡張

**実装内容**:
- `tools/compare_performance.py`: `performance_summary_*.csv`形式に対応
- `--type`オプション追加（`auto`, `performance`, `summary`）
- 自動判定機能（ファイル名に`performance_summary`が含まれる場合は`summary`として扱う）

**評価指標**:
- `performance_*.csv`: 日別の`total`列の差分（MAE, RMSE, MAX）
- `performance_summary_*.csv`: 年別の各指標列（sum, mean, std, sr, mdd, sortino）の差分（MAE, RMSE, MAX）

**使用方法**:
```powershell
# performance_*.csv を比較
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"

# performance_summary_*.csv を比較
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_summary_20250520.csv" --new "test\output\performance\performance_summary_20250520.csv" --type summary
```

### 🐛 バグ修正

**実装内容**:
- `lib.py`: `performanceSummary()`関数の`groupby().agg()`でdatetime列が混入する問題を修正
- `lib.py`: `mdd`関数をSeriesを受け取るように修正（DataFrame処理のエラーを回避）

**修正内容**:
- `groupby("year")[["pl"]].agg(...)`で数値列のみを集計対象に
- `groupby("year")["pl"].apply(mdd).to_frame()`でSeries処理に統一

### ✅ Done条件（3rd_commitの合格ライン）

- ✅ `SPOT_SUFFIX`環境変数によるspotデータ切替が動作する
- ✅ `test_prod.py`を新データで実行可能（段階1）
- ✅ `performance_summary_*.csv`の比較が可能
- ✅ READMEにデータソース切替手順が記載されている
- ✅ バグ修正により`test_prod.py`が正常に完了する

---

## 🔄 Ground Truth再現手順

### 目的

Ground Truth（参照系）から同じ結果を再現する。以下2つの参照系を再現可能にする：
- **18th_commit（Forward）**: `D:\forex\18th_commit\program6`
- **all_spot_TK20（Spot/TK20）**: `D:\forex\all_spot_TK20\program6`

### 実行方法

#### 方法1: PowerShellスクリプト（推奨）

```powershell
# 18th_commit を再現
.\tools\reproduce_ground_truth.ps1 -GroundTruth "18th_commit" -Date "2025-05-20"

# all_spot_TK20 を再現
.\tools\reproduce_ground_truth.ps1 -GroundTruth "all_spot_TK20" -Date "2025-05-20"
```

**注意**: `test_prod.py`は火曜日のみ実行されます。日付を確認してください。

#### 方法2: 手動実行

詳細は `tools/REPRODUCTION_STEPS.md` を参照してください。

### 比較スクリプト

```powershell
# performance_*.csv を比較
python tools\compare_performance.py --ref "D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"

# performance_summary_*.csv を比較（--type summary を指定）
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_summary_20250520.csv" --new "test\output\performance\performance_summary_20250520.csv" --type summary
```

**PASS条件**: `max_abs_diff <= 1e-12`

---

## 📊 データソース切替（新データ評価）

### 段階1: testのみ新データで実行

**目的**: 新spotデータ（`_from_sec1.csv`）を使用して`test_prod.py`を実行し、結果を確認する。

**実行コマンド**:

```powershell
# 環境変数を設定してtest_prod.pyを実行
$env:SPOT_SUFFIX = "_from_sec1"
python test_prod.py 2025-05-20
```

**出力先**（この2つが"成功判定"）:

- `test/output/performance/performance_20250520.csv`
- `test/output/performance/performance_summary_20250520.csv`

**確認ポイント**:

- コンソールに `[RUN] SPOT_SUFFIX='_from_sec1'` が表示される
- コンソールに `[SPOT] loading: market/spot_rates_*_from_sec1.csv` が表示される
- 上記2つのCSVファイルが生成される

**注意**: `test_prod.py`は火曜日のみ実行されます。日付を確認してください。

### 段階2: trainから新データで作り直す

**目的**: 新spotデータで`train.py`を実行し、その結果を使って`test_prod.py`も実行する。

**実行コマンド**:

```powershell
# trainを新spotで実行
$env:SPOT_SUFFIX = "_from_sec1"
python train.py

# train結果をtestにコピー（既存の流れに従う）
# train/output/summary/train_result_*.csv を test/input/input_by_train/ にコピー

# testを実行（環境変数は設定済み）
python test_prod.py 2025-05-20
```

### 比較スクリプト（新データ評価）

```powershell
# performance_*.csv を比較（旧spot vs 新spot）
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"

# performance_summary_*.csv を比較（旧spot vs 新spot）
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_summary_20250520.csv" --new "test\output\performance\performance_summary_20250520.csv" --type summary
```

**評価指標**:

- **MAE**: Mean Absolute Error（平均絶対誤差）
- **RMSE**: Root Mean Squared Error（二乗平均平方根誤差）
- **MAX**: 最大絶対誤差
- 日付は**intersection（共通日）**に揃える

### トラブルシューティング

不一致が発生した場合の確認順序：

1. **`lib.py`の`INPUTPATH`確認**: `test\input\`を指しているか
2. **入力データの完全一致確認**: 行数・ハッシュ値の確認
3. **時刻基準の確認**: `test_prod.py`が同じ時刻基準（NY17/TK20）を呼んでいるか
4. **依存パッケージのバージョン差**: pandas/numpyバージョンの確認
5. **並列処理やソート順の違い**: rank tieの扱い等

詳細は `tools/REPRODUCTION_STEPS.md` を参照してください。

---

## 📅 Planned (next commit)

### 4th_commit予定

- 段階2の実装完了（trainから新データで作り直す）
- 新データでのtrain結果とtest結果の検証
- パフォーマンス指標の詳細比較と評価基準の確立

---

## 📁 プロジェクト構造

```
forex01-kai/
├── lib.py                          # コアライブラリ（高速化版実装済み）
├── train.py                        # トレーニング実行スクリプト
├── test_sim.py                     # シミュレーションテスト実行スクリプト
├── test_prod.py                    # 本番環境テスト実行スクリプト
│
├── scripts/                        # 改修スクリプト集
│   ├── verify_regression.py        # 検証: 回帰確認（1st_commit）
│   ├── bench.py                    # 検証: ベンチマーク（1st_commit）
│   ├── check_use_fast.py           # 検証: USE_FASTフラグ確認（1st_commit）
│   ├── verify_swap_none.py         # 検証: swap=None無害性（1st_commit）
│   ├── verify_swap_constant.py     # 検証: swap定数平行移動（1st_commit）
│   ├── estimate_train_time.py      # 計算時間推定（1st_commit）
│   ├── VERIFICATION.md             # 検証手順詳細（1st_commit）
│   ├── QUICK_START.md              # クイックスタートガイド（1st_commit）
│   ├── REGRESSION_TEST_STEPS.md    # 回帰テスト手順（1st_commit）
│   ├── README.md                   # スクリプト詳細説明（1st_commit）
│   │
│   ├── import_histdata_sec1.py     # タスク2: HistData→Parquet（2nd_commit予定）
│   ├── generate_daily_snapshots.py # タスク3: 日次スナップショット生成（2nd_commit予定）
│   └── validate_timezone_diff.py   # タスク4: タイムゾーン検証（2nd_commit予定）
│
├── train/                          # トレーニング関連
│   ├── input/                      # トレーニング用入力データ
│   │   ├── market/                 # 市場データ
│   │   └── position/               # ポジション関数定義
│   └── output/                     # トレーニング結果
│       └── summary/                # サマリー結果
│
├── test/                           # テスト関連
│   ├── input/                      # テスト用入力データ
│   └── output/                     # テスト結果
│
└── data/                           # データ（2nd_commit予定）
    # 注意: sec1_parquetはD:\forex01_data\sec1_parquetに移動済み（CursorのSync負荷軽減のため）
```

## 📁 プロジェクト構造

```
forex01-kai/
├── lib.py                          # コアライブラリ（高速化版実装済み）
├── train.py                        # トレーニング実行スクリプト
├── test_sim.py                     # シミュレーションテスト実行スクリプト
├── test_prod.py                    # 本番環境テスト実行スクリプト
│
├── scripts/                        # 改修スクリプト集
│   ├── import_histdata_sec1.py     # タスク2: HistData→Parquet
│   ├── generate_daily_snapshots.py # タスク3: 日次スナップショット生成
│   ├── validate_timezone_diff.py   # タスク4: タイムゾーン検証
│   ├── verify_regression.py        # 検証: 回帰確認
│   ├── bench.py                    # 検証: ベンチマーク
│   ├── verify_swap_none.py         # 検証: swap=None無害性
│   ├── verify_swap_constant.py     # 検証: swap定数平行移動
│   ├── check_use_fast.py           # 検証: USE_FASTフラグ確認
│   ├── estimate_train_time.py      # 計算時間推定
│   ├── VERIFICATION.md             # 検証手順詳細
│   ├── QUICK_START.md              # クイックスタートガイド
│   ├── REGRESSION_TEST_STEPS.md    # 回帰テスト手順
│   └── README.md                   # スクリプト詳細説明
│
├── train/                          # トレーニング関連
│   ├── input/                      # トレーニング用入力データ
│   │   ├── market/                 # 市場データ
│   │   └── position/               # ポジション関数定義
│   └── output/                     # トレーニング結果
│       └── summary/                # サマリー結果
│
├── test/                           # テスト関連
│   ├── input/                      # テスト用入力データ
│   └── output/                     # テスト結果
│
└── data/                           # データ（新規）
    # 注意: sec1_parquetはD:\forex01_data\sec1_parquetに移動済み（CursorのSync負荷軽減のため）
```

## 🚀 クイックスタート（1st_commit）

### 1. 高速化版の使用

```python
# lib.pyの先頭で設定（デフォルト: USE_FAST = True）
USE_FAST = True  # 高速版を使用
```

### 2. 検証の実行

```bash
# ベンチマーク
python scripts/bench.py

# 回帰確認
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# USE_FASTフラグの確認
python scripts/check_use_fast.py
```

### 3. トレーニングの実行

```bash
# 全6ケースを並列実行
python train.py

# 推定実行時間: 約25-30分（並列実行時）
```

## 📊 1st_commit 検証結果

### 高速化の効果

- **ベンチマーク結果**: 約7.5倍の高速化（目標3倍を上回る）
  - USE_FAST=False: 平均 0.043秒
  - USE_FAST=True: 平均 0.006秒

### 回帰確認

- **USE_FAST=False と True で結果が完全一致**
  - すべての列（mean, ref_period_width, trade_period_width, number_of_parameters）で差分が0
  - 互換性が保証されています

### 計算時間推定

- **各戦略**: 約49分/戦略
- **全6プロセス（並列実行）**: 約25-30分
- **ボトルネック**: `simulate()`関数（約46.8分/戦略）

詳細は `scripts/estimate_train_time.py` を参照してください。

## 🔧 1st_commit 検証手順

詳細な検証手順は `scripts/VERIFICATION.md` を参照してください。

### 1st_commit前の最終チェック（コピペ用）

```bash
# 1. 回帰確認
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# 2. ベンチマーク
python scripts/bench.py

# 3. トレーニング実行（1ケースでOK）
# train.pyを一時的に修正して1ケースのみ実行
python train.py
```

### 検証の順番（重要）

1. **高速化の回帰確認**（最優先）✅
2. **ベンチマーク**（3倍以上を確認）✅
3. **タイムゾーン検証**（±30秒以内）⏳ 2nd_commit予定
4. **swap無害性確認**（Noneで無害、定数で平行移動）✅

## 📝 1st_commit 主要な変更点

### lib.py

- `USE_FAST`フラグを追加（デフォルト: `True`）
- `makeFactorReturn_fast`関数を追加
- `makeFactorReturnA/B/C`関数を修正して高速版を呼び出し可能に
- `swap_df`パラメータを追加（インターフェース定義）
- `DataFrame.append()`を`pd.concat()`に置換（pandas 2.0対応）
- `rolling().mean()`実行前に数値列のみを選択（datetime列除外）

### scripts/（新規ディレクトリ）

**1st_commitで実装**:
- `verify_regression.py`: 回帰確認
- `bench.py`: ベンチマーク
- `check_use_fast.py`: USE_FASTフラグ確認
- `verify_swap_none.py`: swap=None無害性確認
- `verify_swap_constant.py`: swap定数平行移動確認
- `estimate_train_time.py`: 計算時間推定
- 各種ドキュメント（VERIFICATION.md, QUICK_START.md, etc.）

**2nd_commit実装済み**:
- `import_histdata_sec1.py`: 秒足データ取り込みパイプライン
- `generate_daily_snapshots.py`: 日次スナップショット生成
- `validate_timezone_diff.py`: タイムゾーン検証

## ⚠️ 注意事項

1. **Parquetファイルの依存関係**
   - `pyarrow`パッケージが必要: `pip install pyarrow`

2. **タイムゾーン処理**
   - Python 3.9+の場合: `zoneinfo`モジュールが標準で利用可能（`tzdata`パッケージが必要な場合あり）
   - Python 3.8以前または`zoneinfo`が利用できない場合: `pytz`パッケージが必要
   - インストール: `pip install pytz` または `pip install tzdata`
   - DST（夏時間）は自動で処理されます

3. **既存データとの互換性**
   - 出力CSVの列名とフォーマットは既存仕様と完全互換
   - `picked_timestamp_utc`列が追加されますが、既存コードには影響しません

4. **性能改善**
   - `USE_FAST = True`で約7.5倍の高速化が確認されています
   - まずEURUSD単一ペア・単月で検証してから全展開することを推奨

## 🐛 トラブルシューティング

### Parquetファイルが読み込めない
- `pyarrow`がインストールされているか確認: `pip install pyarrow`

### タイムゾーンエラー
- Python 3.9以上を使用しているか確認
- `zoneinfo`モジュールが利用可能か確認

### 既存データとの差分が大きい
- `validate_timezone_diff.py`で検証を実行
- NG日付の原因を確認（データ欠損、DST切り替え日など）

### USE_FASTが効いていない
- `python scripts/check_use_fast.py`で確認
- `lib.py`の`USE_FAST`フラグが`True`になっているか確認

## 📚 詳細ドキュメント

- `scripts/README.md`: スクリプトの詳細説明
- `scripts/VERIFICATION.md`: 検証手順の詳細
- `scripts/QUICK_START.md`: クイックスタートガイド
- `scripts/REGRESSION_TEST_STEPS.md`: 回帰テスト手順
- `tools/REPRODUCTION_STEPS.md`: Ground Truth再現手順の詳細
- `プロジェクト構造説明.md`: プロジェクト構造の詳細

## 🎉 1st_commit サマリー

### ✅ 実装完了（1st_commit）

1. ✅ **lib.py高速化**: 約7.5倍の高速化を実現
   - `makeFactorReturn_fast`関数
   - `USE_FAST`フラグ
   - 回帰確認: USE_FAST=False と True で完全一致

2. ✅ **スワップ損益設計**: 後付け可能な設計（インターフェース定義）
   - `swap_df`パラメータを追加
   - 回帰保証（swap=Noneで既存結果と一致）

3. ✅ **検証スクリプト**: ベンチマーク・回帰確認ツール
   - `bench.py`: ベンチマーク実行
   - `verify_regression.py`: 回帰確認
   - `check_use_fast.py`: USE_FASTフラグ確認

### 📈 性能改善

- **makeFactorReturn_fast**: 約7.5倍高速化
- **回帰確認**: USE_FAST=False と True で完全一致
- **推定実行時間**: 約25-30分（全6ケース並列実行時）

### 🔄 次のコミット予定

**2nd_commit**: ✅ 完了（histdata pipeline: zip->parquet->snapshot + timezone validation）
- ✅ タスク2: 秒足データ取り込みパイプライン
- ✅ タスク3: 日次スナップショット生成
- ✅ タスク4: タイムゾーン差分検証

**3rd_commit**: entry scan (weekly horizon, time grid)

**4th_commit**: factor extensions (TS-MOM/vol filter, modular factors)

## 📄 ライセンス

（プロジェクトのライセンス情報を記載）

## 👥 貢献者

（貢献者情報を記載）

