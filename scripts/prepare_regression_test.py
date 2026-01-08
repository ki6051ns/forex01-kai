"""
回帰テストの準備スクリプト

USE_FAST=False と True で train.py を実行し、結果ファイルを準備する
"""

import sys
import subprocess
import shutil
from pathlib import Path
import argparse


def run_train_with_flag(use_fast: bool, test_case: str = "NY17TK20_A"):
    """
    USE_FASTフラグを設定してtrain.pyを実行
    
    Args:
        use_fast: USE_FASTフラグの値
        test_case: テストケース（例: "NY17TK20_A"）
    """
    lib_path = Path("lib.py")
    
    if not lib_path.exists():
        print(f"❌ lib.py が見つかりません: {lib_path}")
        return False
    
    # lib.pyを読み込み
    with open(lib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # USE_FASTフラグを更新
    if 'USE_FAST = True' in content:
        content = content.replace('USE_FAST = True', f'USE_FAST = {use_fast}')
    elif 'USE_FAST = False' in content:
        content = content.replace('USE_FAST = False', f'USE_FAST = {use_fast}')
    else:
        print("❌ lib.py に USE_FAST フラグが見つかりません")
        return False
    
    # バックアップを作成
    backup_path = Path("lib.py.backup")
    if not backup_path.exists():
        shutil.copy2(lib_path, backup_path)
        print(f"✅ lib.py のバックアップを作成: {backup_path}")
    
    # lib.pyを更新
    with open(lib_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ USE_FAST = {use_fast} に設定しました")
    
    # train.pyを実行（1ケースのみ）
    # 注意: train.pyを一時的に修正する必要があるかもしれません
    print(f"📝 train.py を実行中...")
    print(f"   注意: 全ケースを実行すると時間がかかります。")
    print(f"   1ケースのみ実行する場合は、train.pyを一時的に修正してください。")
    
    try:
        result = subprocess.run(
            [sys.executable, "train.py"],
            capture_output=True,
            text=True,
            timeout=3600  # 1時間のタイムアウト
        )
        
        if result.returncode == 0:
            print("✅ train.py の実行が完了しました")
            return True
        else:
            print(f"❌ train.py の実行でエラーが発生しました:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ train.py の実行がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ train.py の実行でエラーが発生しました: {e}")
        return False


def prepare_regression_files(test_case: str = "NY17TK20_A"):
    """
    回帰テスト用のファイルを準備
    
    Args:
        test_case: テストケース（例: "NY17TK20_A"）
    """
    output_dir = Path("train/output/summary")
    source_file = output_dir / f"train_result_{test_case}.csv"
    
    if not source_file.exists():
        print(f"❌ ソースファイルが見つかりません: {source_file}")
        print(f"   まず train.py を実行してください。")
        return False
    
    # USE_FAST=False の結果を保存
    false_file = output_dir / f"train_result_{test_case}_USE_FAST_FALSE.csv"
    if false_file.exists():
        print(f"⚠️  既に存在します: {false_file}")
        response = input("上書きしますか？ (y/n): ")
        if response.lower() != 'y':
            print("スキップしました")
            return False
    
    shutil.copy2(source_file, false_file)
    print(f"✅ USE_FAST=False の結果を保存: {false_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='回帰テストの準備',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # Step 1: USE_FAST=False で実行
  python scripts/prepare_regression_test.py --use-fast False --test-case NY17TK20_A
  
  # Step 2: USE_FAST=True で実行
  python scripts/prepare_regression_test.py --use-fast True --test-case NY17TK20_A
  
  # Step 3: 比較
  python scripts/verify_regression.py \\
      --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \\
      --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv
        """
    )
    parser.add_argument('--use-fast', type=str, choices=['True', 'False', 'true', 'false'],
                       help='USE_FASTフラグの値 (True/False)')
    parser.add_argument('--test-case', type=str, default='NY17TK20_A',
                       help='テストケース（例: NY17TK20_A）')
    parser.add_argument('--prepare-only', action='store_true',
                       help='train.pyを実行せず、既存ファイルを準備するだけ')
    
    args = parser.parse_args()
    
    if args.use_fast:
        # USE_FASTフラグを設定
        use_fast = args.use_fast.lower() == 'true'
        
        if not args.prepare_only:
            # train.pyを実行
            success = run_train_with_flag(use_fast, args.test_case)
            if not success:
                sys.exit(1)
        
        # 結果ファイルを準備
        prepare_regression_files(args.test_case)
        
    else:
        print("=" * 60)
        print("回帰テストの準備")
        print("=" * 60)
        print("\n使用方法:")
        print("  Step 1: USE_FAST=False で実行")
        print("    python scripts/prepare_regression_test.py --use-fast False --test-case NY17TK20_A")
        print("\n  Step 2: USE_FAST=True で実行")
        print("    python scripts/prepare_regression_test.py --use-fast True --test-case NY17TK20_A")
        print("\n  Step 3: 比較")
        print("    python scripts/verify_regression.py \\")
        print("        --old train/output/summary/train_result_NY17TK20_A_USE_FAST_FALSE.csv \\")
        print("        --new train/output/summary/train_result_NY17TK20_A_USE_FAST_TRUE.csv")
        print("\n注意:")
        print("  - train.py は全ケースを実行します。時間がかかる場合は、")
        print("    train.py を一時的に修正して1ケースのみ実行してください。")
        sys.exit(0)


if __name__ == "__main__":
    main()

