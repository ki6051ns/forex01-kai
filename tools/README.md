# tools/ ディレクトリ

再現性検証用のツールを提供します。

## ファイル一覧

### `compare_performance.py`

Performance CSV比較スクリプト。Ground Truth（参照CSV）と現repoで生成したCSVを比較します。

**使用方法**:
```powershell
python tools\compare_performance.py --ref <参照CSV> --new <比較CSV>
```

**例**:
```powershell
python tools\compare_performance.py --ref "D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv" --new "test\output\performance\performance_20250520.csv"
```

**PASS条件**: `max_abs_diff <= 1e-12`

### `reproduce_ground_truth.ps1`

Ground Truth再現スクリプト（PowerShell版）。自動的に入力データをコピーし、実行し、結果を比較します。

**使用方法**:
```powershell
# 18th_commit を再現
.\tools\reproduce_ground_truth.ps1 -GroundTruth "18th_commit" -Date "2025-05-20"

# all_spot_TK20 を再現
.\tools\reproduce_ground_truth.ps1 -GroundTruth "all_spot_TK20" -Date "2025-05-20"
```

**注意**: 
- `test\input\`を自動的にバックアップします（`test\input__backup\`）
- `test_prod.py`は火曜日のみ実行されます。日付を確認してください。

### `REPRODUCTION_STEPS.md`

Ground Truth再現手順の詳細ドキュメント。手動実行方法やトラブルシューティングを記載しています。

## 再現手順の概要

1. **バックアップ**: `test\input\`をバックアップ（自動）
2. **入力データコピー**: Ground Truthの入力データを現repoにコピー
3. **実行**: `test_prod.py`を実行
4. **比較**: `compare_performance.py`で結果を比較

詳細は `REPRODUCTION_STEPS.md` を参照してください。

## Ground Truthフォルダ

- **18th_commit**: `D:\forex\18th_commit\program6`
- **all_spot_TK20**: `D:\forex\all_spot_TK20\program6`