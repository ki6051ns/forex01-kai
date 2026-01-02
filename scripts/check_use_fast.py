"""
USE_FASTフラグが正しく設定されているか確認するスクリプト
"""

import sys
from pathlib import Path

# lib.pyをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
import lib

print("=" * 60)
print("USE_FAST フラグの確認")
print("=" * 60)
print(f"USE_FAST = {lib.USE_FAST}")
print(f"型: {type(lib.USE_FAST)}")

if lib.USE_FAST:
    print("[OK] 高速化版が有効です")
    print("     makeFactorReturn_fast が使用されます")
else:
    print("[WARNING] 既存版が使用されています")
    print("          makeFactorReturn が使用されます")

print("\nmakeFactorReturn_fast 関数の存在確認:")
if hasattr(lib, 'makeFactorReturn_fast'):
    print("[OK] makeFactorReturn_fast 関数が存在します")
else:
    print("[ERROR] makeFactorReturn_fast 関数が見つかりません")

print("\nmakeFactorReturnA 関数の確認:")
import inspect
source = inspect.getsource(lib.makeFactorReturnA)
if 'USE_FAST' in source:
    print("[OK] USE_FAST フラグのチェックが実装されています")
    if 'makeFactorReturn_fast' in source:
        print("[OK] makeFactorReturn_fast の呼び出しが実装されています")
    else:
        print("[ERROR] makeFactorReturn_fast の呼び出しが見つかりません")
else:
    print("[ERROR] USE_FAST フラグのチェックが見つかりません")

