# verify_regression.py 使用例

## エラー: Permission denied または ファイルが見つからない

`--old ... --new ...` というプレースホルダーをそのまま使うとエラーになります。
**実際のファイルパスを指定してください。**

## 正しい使用手順

### Step 1: USE_FAST=False で実行

```bash
# lib.py を編集して USE_FAST = False に設定
# または、一時的に変更:
# sed -i 's/USE_FAST = True/USE_FAST = False/' lib.py

# 1ケースのみ実行（例：NY17→TK20 の Aのみ）
python train.py

# 出力を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
```

### Step 2: USE_FAST=True で実行

```bash
# lib.py を編集して USE_FAST = True に設定
# または、一時的に変更:
# sed -i 's/USE_FAST = False/USE_FAST = True/' lib.py

# 同じケースを実行
python train.py

# 出力を保存
cp train/output/summary/train_result_NY17TK20_A.csv train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

### Step 3: 比較実行

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

## ファイルパスの確認

ファイルが存在するか確認:

```bash
# Windows PowerShell
Test-Path train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
Test-Path train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv

# Linux/Mac
ls -la train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv
ls -la train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
```

## ヘルプの表示

```bash
python scripts/verify_regression.py --help
```

## よくあるエラーと対処法

### 1. Permission denied

**原因**: ファイルが他のプログラムで開かれている

**対処法**:
- Excelやエディタでファイルを閉じる
- ファイルの読み取り権限を確認

### 2. File not found

**原因**: ファイルパスが間違っている、またはファイルが存在しない

**対処法**:
- ファイルパスを確認（相対パスまたは絶対パス）
- ファイルが実際に存在するか確認
- `train.py`が正常に実行されたか確認

### 3. プレースホルダーエラー

**原因**: `--old ... --new ...` をそのまま使用

**対処法**:
- 実際のファイルパスを指定
- 上記の使用例を参照

