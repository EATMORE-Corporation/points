# your_project_root/points/template.py
import sys
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
import time

# --- リソースパス解決関数 (変更なし) ---
def resource_path(relative_path_from_script):
    """実行環境 (.py or .exe) に応じてリソースへのパスを解決する"""
    try:
        # PyInstallerで作成された一時フォルダ
        base_path = sys._MEIPASS
        # MEIPASS を基準に、元の相対パスの '../' を除いたパス部分を結合
        # 例: ../settings/file.csv -> os.path.join(MEIPASS, 'settings', 'file.csv')
        path_parts = os.path.normpath(relative_path_from_script).split(os.path.sep)
        relevant_path_parts = [part for part in path_parts if part != '..']
        return os.path.join(base_path, *relevant_path_parts)
    except AttributeError:
        # 通常のPythonスクリプトとして実行された場合
        # この template.py ファイルがあるディレクトリを基準にする
        script_dir = os.path.abspath(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(script_dir, relative_path_from_script))

# --- 設定ファイル読み込みクラス ---
class SettingsLoader:
    """
    設定ファイル (.csv, .exe, .json) のパスを管理・取得するクラス。
    CSV読み込みは汎用的に全カラムを文字列として読み込む。
    """
    DEFAULT_SETTINGS_DIR = "../settings"

    def __init__(self, settings_dir=None):
        self.settings_dir_relative = settings_dir if settings_dir is not None else self.DEFAULT_SETTINGS_DIR
        # print(f"デバッグ: SettingsLoader initialized. Relative settings dir: {self.settings_dir_relative}")

    def _get_resource_path(self, filename):
        """resource_path関数を使ってファイルへの絶対パスを取得する"""
        relative_path_from_script = os.path.join(self.settings_dir_relative, filename)
        full_path = resource_path(relative_path_from_script)
        # print(f"デバッグ: Resolving path for {filename} -> {full_path}")
        return full_path

    def load_all_idpass(self, filename="idpass.csv"):
        """
        指定されたCSVファイル (デフォルト: idpass.csv) を読み込み、
        すべてのカラムを含むDataFrameとして返す。
        読み込み時、すべてのカラムを文字列(str)として扱う。
        """
        filepath = self._get_resource_path(filename)

        try:
            # dtype=str を指定して、すべてのカラムを文字列として読み込む
            df = pd.read_csv(filepath, dtype=str)

            # ファイルが空かどうかのチェック
            if df.empty:
                print(f"情報: ファイル '{filepath}' は空か、またはヘッダーのみです。")
                # 空のDataFrameを返す (呼び出し側で .empty チェックが必要)
                return df

            # カラム名のチェックは行わない（汎用化のため）
            print(f"デバッグ: {filename} 読み込み成功 ({len(df)} 行, {len(df.columns)} カラム)")
            return df # 読み込んだDataFrameをそのまま返す

        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません - {filepath}")
            return None
        except pd.errors.EmptyDataError:
             print(f"エラー: ファイル '{filepath}' は完全に空です（ヘッダーもありません）。")
             return None # 空のファイルの場合はNoneを返す
        except Exception as e:
            print(f"エラー: {filename} の読み込み中に予期せぬエラーが発生しました - {e}")
            traceback.print_exc()
            return None

    def get_chromedriver_path(self, filename="chromedriver_134.0.6998.89.exe"):
        """ChromeDriverのパスを取得する"""
        filepath = self._get_resource_path(filename)
        if os.path.exists(filepath):
            # print(f"デバッグ: ChromeDriver確認: {filepath}")
            return filepath
        else:
            print(f"エラー: ChromeDriverが見つかりません - {filepath}")
            return None

    def get_gcp_key_path(self, filename="code2-455205-e4312a13bb37.json"):
        """GCPサービスアカウントキーのパスを取得する"""
        filepath = self._get_resource_path(filename)
        if os.path.exists(filepath):
            # print(f"デバッグ: GCPキーファイル確認: {filepath}")
            return filepath
        else:
            print(f"エラー: GCPキーファイルが見つかりません - {filepath}")
            return None


# --- 食べログログインクラス ---
class TabelogLogin:
    """
    食べログオーナーアカウントへのログイン/ログアウト処理を行うクラス。
    WebDriverの初期化/終了も管理する。
    """
    LOGIN_URL = "https://owner.tabelog.com/owner_account/login"
    LOGOUT_URL_FRAGMENT = "/owner_account/logout" # ログアウトURLの一部（確認用）
    LOGOUT_BUTTON_XPATH = '//a[contains(@href, "logout")] | //button[contains(text(), "ログアウト")] | //*[@data-testid="logout-button"] | //*[@id="js-logout-btn"]' # ログアウトボタンXPath候補

    ID_XPATH = '//*[@id="login_id"]'
    PASS_XPATH = '//*[@id="password"]'
    LOGIN_BUTTON_XPATH = '//button[@type="submit"]'

    def __init__(self, settings_dir="../settings"):
        self.settings_loader = SettingsLoader(settings_dir=settings_dir)
        self._driver = None
        self.wait = None
        self._logged_in_user = None # 現在ログイン中のユーザーIDを保持

    def initialize_driver(self):
        """WebDriverを初期化する。成功ならTrue、失敗ならFalse"""
        if self._driver:
             # print("デバッグ: WebDriverは既に初期化されています。")
             return True # 既に初期化済み

        chromedriver_path = self.settings_loader.get_chromedriver_path()
        if not chromedriver_path:
            print("エラー: ChromeDriverのパスが取得できませんでした。")
            return False

        # GCPキーパス取得 (ここでは存在確認のみ)
        self.settings_loader.get_gcp_key_path()

        chrome_service = Service(chromedriver_path)
        chrome_options = webdriver.ChromeOptions()
        # --- WebDriverオプション ---
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"]) # DevToolsメッセージ抑制
        # chrome_options.add_argument("--headless") # 必要に応じて有効化
        # chrome_options.add_argument("--disable-gpu") # headless時に推奨される場合あり
        # -------------------------

        try:
            self._driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            self.wait = WebDriverWait(self._driver, 15) # タイムアウト15秒
            print("WebDriverの初期化に成功しました。")
            return True
        except Exception as e:
            print(f"エラー: WebDriverの初期化に失敗しました - {e}")
            if "session not created" in str(e).lower() or "version" in str(e).lower():
                 print("ヒント: ChromeDriverのバージョンとChromeブラウザのバージョンが一致しているか確認してください。")
            self._driver = None
            return False

    def login(self, username, password):
        """指定されたIDとパスワードでログインする。成功ならTrue、失敗ならFalse"""
        if not self._driver:
            print("エラー: WebDriverが初期化されていません。login()の前にinitialize_driver()を呼び出してください。")
            return False

        # 既に同じユーザーでログイン済みならスキップ
        if self._logged_in_user == username:
             print(f"デバッグ: 既にユーザー '{username}' としてログイン済みです。")
             return True

        # 違うユーザーなら、まずログアウト試行
        if self._logged_in_user:
            print(f"デバッグ: 現在のユーザー '{self._logged_in_user}' からログアウトします...")
            if not self.logout():
                print("警告: ログアウトに失敗しましたが、ログイン処理を続行します。")

        try:
            print(f"ログイン試行中: {username}")
            self._driver.get(self.LOGIN_URL) # 常にログインページから開始

            # ID入力
            id_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, self.ID_XPATH)))
            id_field.clear()
            id_field.send_keys(username)

            # パスワード入力
            pass_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, self.PASS_XPATH)))
            pass_field.clear()
            pass_field.send_keys(password)

            # ログインボタンクリック
            login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.LOGIN_BUTTON_XPATH)))
            # JavaScriptクリックの方が安定する場合あり
            # self._driver.execute_script("arguments[0].click();", login_button)
            login_button.click()
            print("ログインボタンクリック")

            # ログイン成功確認 (URLがログインページでなくなることを期待)
            try:
                # より確実なのは、ログイン後の特定の要素を待つこと
                # 例: self.wait.until(EC.presence_of_element_located((By.ID, "dashboard_element_id")))
                self.wait.until(EC.not_(EC.url_to_be(self.LOGIN_URL))) # URLが変わるのを待つ
                current_url = self._driver.current_url
                print(f"ログイン成功: {username}, 現在のURL: {current_url}")
                self._logged_in_user = username # ログインユーザーを記録
                return True
            except Exception:
                # タイムアウトした場合 = ログインページから遷移しなかった可能性
                current_url = self._driver.current_url
                print(f"エラー: ログイン後のページ遷移確認に失敗。ユーザー: {username}, URL: {current_url}")
                error_messages = self._check_login_error_messages()
                if error_messages:
                    print(f"ログインページのエラーメッセージ: {error_messages}")
                self._logged_in_user = None # 失敗したのでクリア
                return False

        except Exception as e:
            print(f"エラー: ログイン処理 ({username}) 中に予期せぬエラー - {e}")
            traceback.print_exc()
            self._logged_in_user = None # 失敗したのでクリア
            return False

    def logout(self):
        """現在ログイン中のユーザーをログアウトする。成功ならTrue、失敗ならFalse"""
        if not self._driver:
            print("警告: WebDriverが存在しないためログアウトできません。")
            return True # ドライバなければログアウト済みとみなす

        if not self._logged_in_user:
            print("デバッグ: 既にログアウトしているか、ログインしていません。")
            # 念のためログインページにいるか確認し、違うなら遷移しておく
            try:
                if self.LOGIN_URL not in self._driver.current_url:
                    self._driver.get(self.LOGIN_URL)
            except Exception as e:
                 print(f"警告: ログアウト済み確認のためのログインページ移動中にエラー: {e}")
            return True

        print(f"ログアウト試行中: {self._logged_in_user}")
        try:
            # ログアウトボタンを探してクリック (XPathは要調整)
            try:
                logout_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.LOGOUT_BUTTON_XPATH)))
                # ボタンが見えなくなる場合があるのでJavaScriptでクリック
                self._driver.execute_script("arguments[0].click();", logout_button)
                print("ログアウトボタンをクリックしました。")
            except Exception as button_error:
                 print(f"警告: ログアウトボタンが見つからないかクリックできませんでした ({button_error})。URL遷移や他の方法を試みます。")
                 # 代替案: ログアウト用URLに直接アクセス (URLが固定で分かっている場合)
                 # logout_fixed_url = "https://owner.tabelog.com/owner_account/logout" # 仮
                 # self._driver.get(logout_fixed_url)
                 # または、ログアウト機能のあるページ(設定画面など)に遷移してからボタンを探すなど

            # ログアウト確認 (ログインページに遷移するか、URLにloginが含まれるか)
            self.wait.until(EC.url_contains("login"))
            print(f"ログアウト成功: {self._logged_in_user}")
            self._logged_in_user = None # ログアウトユーザー情報をクリア
            return True

        except Exception as e:
            print(f"エラー: ログアウト処理中にエラーが発生しました - {e}")
            # 失敗しても、次のログインに備えてログインページに移動しておく試み
            try:
                if self.LOGIN_URL not in self._driver.current_url:
                   self._driver.get(self.LOGIN_URL)
            except Exception as nav_err:
                 print(f"警告: ログアウト失敗後、ログインページへの移動も失敗: {nav_err}")
            self._logged_in_user = None # ログアウト失敗でも状態はクリアしておく
            return False

    def get_driver(self):
        """現在のWebDriverインスタンスを返す"""
        return self._driver

    def close(self):
        """WebDriverインスタンスを安全に閉じる"""
        if self._driver:
            try:
                self._driver.quit()
                print("WebDriverを正常に終了しました。")
            except Exception as e:
                # quit() が失敗しても無視する（プロセスが既に終了している場合など）
                print(f"WebDriver終了時にエラーが発生しましたが、無視します: {e}")
            finally:
                self._driver = None
                self.wait = None
                self._logged_in_user = None

    def _check_login_error_messages(self):
        """ログインページのエラーメッセージを取得試行 (内部メソッド)"""
        error_texts = []
        # エラーメッセージが表示されそうな要素のセレクタ (サイトによって異なるので調整が必要)
        possible_error_selectors = [
            ".c-form__error", # 食べログで使われていそうなクラス
            ".error_message",
            ".alert-danger",
            'div[class*="error"]', # class属性にerrorを含むdiv要素
            'p[class*="error"]'   # class属性にerrorを含むp要素
        ]
        if not self._driver:
            return []
        time.sleep(0.5) # エラーメッセージが表示されるのを少し待つ
        for selector in possible_error_selectors:
            try:
                # XPathかCSSセレクタかを判断
                find_method = By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR
                elements = self._driver.find_elements(find_method, selector)
                for element in elements:
                    # is_displayed() でチェックすることが重要
                    if element.is_displayed() and element.text.strip():
                        error_texts.append(element.text.strip())
            except Exception as find_err:
                # 要素が見つからないエラーは無視してよい場合が多い
                # print(f"Debug: Error finding element with selector {selector}: {find_err}")
                pass
        return list(set(error_texts)) # 重複を除去して返す