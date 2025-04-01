# your_project_root/points/main.py
import sys
import os

# --- 相対インポート ---
# -m オプションで実行されることを前提とするため、
# 相対インポートが成功するはず。
try:
    from .get_points import tabelog_point
except ImportError as e:
    # -m オプションを使わずに実行した場合などにここに来る可能性がある
    print(f"エラー: tabelog_point 関数のインポートに失敗しました。")
    print(f"詳細: {e}")
    print(f"\nヒント: このスクリプトはパッケージの親ディレクトリから")
    print(f"      'python -m points.main' のように実行する必要があります。")
    # 実行を中断
    sys.exit(1)

if __name__ == "__main__":
    # この __name__ == "__main__" ブロックは、
    # python -m points.main で実行した場合にも実行されます。
    print("処理を開始します [main.py] ...")

    # tabelog_point 関数を実行
    tabelog_point()

    print("\n全ての処理が完了しました。プログラムを終了します [main.py] ...")