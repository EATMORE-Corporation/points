# your_project_root/points/get_points.py
import time
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
import traceback
import pandas as pd # DataFrame操作のため

# template.py からクラスをインポート
from .template import SettingsLoader, TabelogLogin

def tabelog_point():
    """idpass.csvの各店舗情報でログインし、処理を実行する"""
    print("食べログポイント処理 [get_points.py] を開始します (idpass.csv基準)...")

    # --- 設定読み込み ---
    settings_loader = SettingsLoader(settings_dir="../settings")
    store_data_df = settings_loader.load_all_idpass() # DataFrameで全店舗情報取得

    # 読み込み結果のチェック
    if store_data_df is None:
        print("エラー: 店舗情報の読み込みに失敗。処理を中断します。")
        return
    if store_data_df.empty:
        print("情報: 処理対象の店舗がidpass.csvにありません。処理を終了します。")
        return

    # --- ★★★ 必要なカラムが存在するかチェック ★★★ ---
    # このスクリプトが依存するカラム名をリストで定義
    required_columns = ['店舗名', 't_id', 't_pass', 'ASPIT', '広告用']
    missing_columns = [col for col in required_columns if col not in store_data_df.columns]
    if missing_columns:
        print(f"エラー: 読み込んだデータに必要なカラム {missing_columns} が存在しません。idpass.csvを確認してください。処理を中断します。")
        return
    # --- カラムチェック終了 ---

    # --- WebDriver準備 ---
    login_manager = TabelogLogin(settings_dir="../settings")
    # ループ開始前に一度だけ初期化
    if not login_manager.initialize_driver():
        print("エラー: WebDriverの初期化に失敗。処理を中断します。")
        return
    driver = login_manager.get_driver() # driverインスタンスを取得しておく

    processed_count = 0
    error_count = 0
    total_stores = len(store_data_df)

    try:
        # --- DataFrameの各行（店舗）でループ ---
        # iterrows() を使うと、indexと行データ(Pandas Series)が取得できる
        for index, store_info in store_data_df.iterrows():
            # store_info は Pandas Series なので、列名でアクセスできる
            # 事前にカラムチェックしているので、KeyErrorは基本的に発生しないはず
            shop_name = store_info['店舗名']
            t_id = store_info['t_id']
            t_pass = store_info['t_pass']
            aspit_info = store_info['ASPIT']
            ad_info = store_info['広告用']

            print(f"\n[{index + 1}/{total_stores}] 処理開始 店舗: {shop_name} (ID: {t_id})")

            # IDまたはPassが空、あるいは NaN の場合はスキップ (dtype=strで読み込んでも空文字列になるはずだが念のため)
            if pd.isna(t_id) or not str(t_id).strip() or pd.isna(t_pass) or not str(t_pass).strip():
                print(f"  警告: IDまたはパスワードが空、または無効です。スキップします。")
                error_count += 1
                continue

            # 1. ログイン実行 (内部で前ユーザーからログアウトされる)
            if not login_manager.login(t_id, t_pass):
                print(f"  エラー: ログインに失敗しました。スキップします。")
                error_count += 1
                # ログイン失敗が続く場合の処理中断ロジックも検討可能
                # if error_count > 5: print("エラー: ログイン失敗が続いたため処理を中断"); break
                continue # 次の店舗へ

            # 2. ログイン後の処理実行
            try:
                print(f"  ログイン成功。店舗 '{shop_name}' の処理を実行します。")
                # ===== ここにログイン後の実際の処理を記述 =====
                # 取得した情報 (aspit_info, ad_info, shop_name) を利用可能
                print(f"    - 店舗名: {shop_name}")
                print(f"    - ASPIT情報: {aspit_info}")
                print(f"    - 広告用情報: {ad_info}")

                # 例: ダッシュボードに表示される店舗名を確認 (仮のXPath)
                try:
                    # WebDriverWait を使って要素が表示されるまで待つ
                    displayed_shop_name_element = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="js-header-shop-name"] | //h1[contains(@class, "shop-name")]')) # XPathは要調査・修正
                    )
                    displayed_name = displayed_shop_name_element.text
                    print(f"    - 画面上の店舗名: {displayed_name}")
                    # 必要なら shop_name と比較
                    # if shop_name not in displayed_name:
                    #     print(f"警告: CSVの店舗名と画面上の店舗名が一致しません ({shop_name} vs {displayed_name})")
                except (NoSuchElementException, TimeoutException):
                    print("    - 警告: 画面上の店舗名要素が見つかりませんでした。")

                # 例: 特定の情報を取得して表示 (仮のXPath)
                try:
                    some_info_element = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.XPATH, '//div[@class="important-info"]')) # XPathは要調査・修正
                    )
                    print(f"    - 重要情報(仮): {some_info_element.text[:100]}...")
                except (NoSuchElementException, TimeoutException):
                    print("    - 情報: 重要情報(仮)の要素は見つかりませんでした。")


                # 例: 念のため少し待機
                time.sleep(1)
                # ====(処理終了)====
                print(f"  店舗 '{shop_name}' の処理が完了しました。")
                processed_count += 1

            except WebDriverException as e:
                print(f"  エラー: ログイン後の操作中にWebDriverエラーが発生しました - {e}")
                error_count += 1
                # エラー発生時のスクリーンショットなど
                # filename = f"error_{shop_name.replace(' ', '_').replace('/', '-')}_{int(time.time())}.png"
                # try: driver.save_screenshot(filename); print(f"Screenshot saved: {filename}")
                # except Exception as ss_err: print(f"Failed to save screenshot: {ss_err}")
                continue # 次の店舗へ
            except Exception as e:
                print(f"  エラー: ログイン後の操作中に予期せぬエラーが発生しました - {e}")
                traceback.print_exc()
                error_count += 1
                continue # 次の店舗へ

        print(f"\n--- 処理結果 ---")
        print(f"総店舗数 (CSV行数): {total_stores}")
        print(f"正常処理店舗数: {processed_count}")
        print(f"エラースキップ店舗数: {error_count}")

    except Exception as e:
        print(f"\nエラー: ループ処理の途中で予期せぬエラーが発生し、中断しました - {e}")
        traceback.print_exc()

    finally:
        # --- 終了処理 ---
        print("\n最終的なWebDriverの終了処理を行います...")
        login_manager.close() # WebDriverを閉じる (初期化失敗時も呼ばれるが問題ない)

    print("食べログポイント処理 [get_points.py] を終了します。")