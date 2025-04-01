# your_project_root/points/main.py
import sys
import os

# --- 相対インポート ---
try:
    from .get_points import tabelog_point
except ImportError as e:
    print(f"エラー: from .get_points import tabelog_point で失敗。通常のインポート試行。 {e}")
    try:
        import get_points
        tabelog_point = get_points.tabelog_point
    except ImportError as e2:
        print(f"エラー: get_points モジュールのインポート失敗。 {e2}")
        sys.exit(1)

if __name__ == "__main__":
    print("処理を開始します [main.py] ...")

    # tabelog_point 関数を実行 (引数なし)
    tabelog_point()

    print("\n全ての処理が完了しました。プログラムを終了します [main.py] ...")