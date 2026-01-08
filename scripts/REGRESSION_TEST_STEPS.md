# 回帰テスト実行手順（詳細版）

## 前提条件

- `lib.py` に `USE_FAST` フラグが実装されていること
- `train.py` が正常に実行できること

## 手順（推奨：1ケースのみで検証）

### 方法1: train.pyを一時的に修正（推奨）

#### Step 1: USE_FAST=False で実行

```bash
# 1. lib.py を編集
# USE_FAST = False に設定

# 2. train.py を一時的に修正（1ケースのみ実行）
# train.py の if __name__ == "__main__": セクションを以下に変更:
# if __name__ == "__main__":
#     lib.train_NY17TK20_A(LASTSIMULATIONPERIOD)

# 3. 実行
python train.py

# 4. 結果を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
```

#### Step 2: USE_FAST=True で実行

```bash
# 1. lib.py を編集
# USE_FAST = True に設定

# 2. train.py はそのまま（1ケースのみ実行）

# 3. 実行
python train.py

# 4. 結果を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

#### Step 3: 比較実行

```bash
# Windows PowerShell
python scripts/verify_regression.py `
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv `
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# Linux/Mac
python scripts/verify_regression.py \
    --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \
    --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

### 方法2: 全ケース実行（時間がかかります）

```bash
# Step 1: USE_FAST=False
# lib.py で USE_FAST = False に設定
python train.py
# 全6ケースの結果を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
cp train/output/summary/train_result_NY17TK20_B.csv train/output/summary/train_result_NY17TK20_B_USE_FAST_FALSE.csv
# ... (他のケースも同様)

# Step 2: USE_FAST=True
# lib.py で USE_FAST = True に設定
python train.py
# 全6ケースの結果を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
# ... (他のケースも同様)

# Step 3: 各ケースを比較
python scripts/verify_regression.py --old ... --new ...
```

## ファイルパスの確認

実行前に、ファイルが存在するか確認:

```bash
# Windows PowerShell
Test-Path train/output/summary/train_result_NY17TK20_A.csv

# Linux/Mac
ls -la train/output/summary/train_result_NY17TK20_A.csv
```

## 期待される結果

```
============================================================
高速化の回帰確認
============================================================
Old file: train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
New file: train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
Tolerance: 1.00e-10

【トレーニング結果の比較】
比較列数: 8
比較行数: old=120, new=120
✅ ref_period_width: max_diff=0.00e+00
✅ trade_period_width: max_diff=0.00e+00
✅ number_of_parameters: max_diff=0.00e+00
✅ mean: max_diff=1.23e-15
✅ simulation_period_to: max_diff=0.00e+00
✅ position_id_1: max_diff=0.00e+00
✅ position_id_2: max_diff=0.00e+00

============================================================
✅ 回帰確認: PASSED
   USE_FAST=False と True で結果が一致しています。
```

## トラブルシューティング

### ファイルが見つからない

- `train.py` が正常に実行されたか確認
- 出力ディレクトリ `train/output/summary/` が存在するか確認
- ファイル名が正しいか確認（大文字小文字に注意）

### 結果が一致しない

- `makeFactorReturn_fast` の実装を確認
- 特に `reindex` 後のNaN処理、コスト計算、PL計算の順序を確認
- デバッグモードで詳細ログを出力

### train.pyの実行に時間がかかる

- 1ケースのみ実行する方法（方法1）を推奨
- または、`LASTSIMULATIONPERIOD` を小さく設定して期間を短縮

