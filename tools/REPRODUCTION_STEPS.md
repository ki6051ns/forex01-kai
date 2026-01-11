# 再現手順（Windowsパス版）

## 目的

D:\forex\18th_commit\program6 と D:\forex\all_spot_TK20\program6 を Ground Truth として、現在のrepoから同一結果を再現する。

## 前提条件

- Ground Truthフォルダが存在すること
  - `D:\forex\18th_commit\program6\test\input\`
  - `D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv`
  - `D:\forex\all_spot_TK20\program6\test\input\`
  - `D:\forex\all_spot_TK20\program6\test\output\performance\performance_20250520.csv`

- 現在のrepoに以下が存在すること
  - `lib.py`
  - `test_prod.py`
  - `test\input\`
  - `test\output\performance\`

## 実行手順

### Step 0: バックアップ（重要）

```powershell
# 既存のバックアップがあれば削除
if (Test-Path "test\input__backup") { Remove-Item -Recurse -Force "test\input__backup" }

# 現repoのtest\input\をバックアップ
Copy-Item -Recurse "test\input" "test\input__backup"
```

### Step 1: 18th_commit 再現

#### 1-1. 入力データをコピー

```powershell
# 参照フォルダの入力データを現repoにコピー
Remove-Item -Recurse -Force "test\input\*"
Copy-Item -Recurse "D:\forex\18th_commit\program6\test\input\*" "test\input\" -Force
```

#### 1-2. 実行

```powershell
python test_prod.py 2025-05-20
```

**注意**: `test_prod.py`は火曜日のみ実行されるため、2025-05-20が火曜日であることを確認してください。

#### 1-3. 結果を比較

```powershell
python tools\compare_performance.py --ref "D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"
```

**期待結果**: `✅ PASSED (max_abs_diff <= 1e-12)`

### Step 2: all_spot_TK20 再現

#### 2-1. 入力データをコピー

```powershell
# 参照フォルダの入力データを現repoにコピー
Remove-Item -Recurse -Force "test\input\*"
Copy-Item -Recurse "D:\forex\all_spot_TK20\program6\test\input\*" "test\input\" -Force
```

#### 2-2. 実行

```powershell
python test_prod.py 2025-05-20
```

#### 2-3. 結果を比較

```powershell
python tools\compare_performance.py --ref "D:\forex\all_spot_TK20\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"
```

**期待結果**: `✅ PASSED (max_abs_diff <= 1e-12)`

### Step 3: バックアップ復元（必要に応じて）

```powershell
# 現repoの元の入力データに戻す
Remove-Item -Recurse -Force "test\input\*"
Copy-Item -Recurse "test\input__backup\*" "test\input\" -Force
```

## 比較ルール

- `date = start_time` の先頭10文字（YYYY-MM-DD）で揃える
- `date`で inner join（intersection）
- `total`列の差分をチェック（`max_abs_diff`）
- **PASS条件**: `max_abs_diff <= 1e-12`

## トラブルシューティング

### test_prod.pyの実行エラーについて

`test_prod.py`の実行時にエラー（`Traceback`、`KeyError`、`TypeError`など）が表示されることがあります。これは以下の理由で発生する可能性があります：

1. **コードの問題**: データ構造やロジックの変更により、エラーが発生している
2. **データの問題**: 入力データが期待する形式と異なる

**対処方法**:
- エラーが発生しても、スクリプトは結果CSVの存在を確認し、比較を実行します
- 結果CSVが存在する場合、比較を実行して再現性を確認できます
- 結果CSVが存在しない場合は、コードやデータの問題を解決する必要があります

### 一致しない場合の確認順序

1. **`lib.py`の`INPUTPATH`確認**
   - `lib.py`の`INPUTPATH`が`test\input\`を指しているか確認
   - `test_prod.py`実行時は自動的に`test/input/`になるはずです

2. **入力データの完全一致確認**
   ```powershell
   # 行数確認
   (Get-Content "test\input\market\spot_rates_ny17.csv" | Measure-Object -Line).Lines
   (Get-Content "D:\forex\18th_commit\program6\test\input\market\spot_rates_ny17.csv" | Measure-Object -Line).Lines
   
   # ハッシュ値確認（要: Get-FileHash）
   Get-FileHash "test\input\market\spot_rates_ny17.csv"
   Get-FileHash "D:\forex\18th_commit\program6\test\input\market\spot_rates_ny17.csv"
   ```

3. **時刻基準の確認**
   - `test_prod.py`が参照系と同じ「時刻基準（NY17/TK20）」を呼んでいるか確認
   - `lib.py`の`testForProd_*`関数を確認

4. **依存パッケージのバージョン差**
   - pandas/numpyのバージョン差が結果に影響していないか確認

5. **並列処理やソート順の違い**
   - rank tieの扱い等が異なっていないか確認

6. **結果CSVが生成されない場合**
   - `test_prod.py`のエラーメッセージを確認
   - マルチプロセス処理でのエラー（`Process Process-3:`など）は、子プロセスでのエラーを示しています
   - `lib.py`の`testForProd_*`関数を直接実行してデバッグ

## 注意事項

- **必ず`test\input\`をバックアップしてから実行すること**
- **Ground Truthフォルダを上書きしないこと**
- **実行前にGround Truthフォルダの存在を確認すること**