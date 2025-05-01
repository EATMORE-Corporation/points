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
        base_path = sys._MEIPASS
        path_parts = os.path.normpath(relative_path_from_script).split(os.path.sep)
        relevant_path_parts = [part for part in path_parts if part != '..']
        return os.path.join(base_path, *relevant_path_parts)
    except AttributeError:
        script_dir = os.path.abspath(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(script_dir, relative_path_from_script))

# --- 設定ファイル読み込みクラス (変更なし) ---
class SettingsLoader:
    """
    設定ファイル (.csv, .exe, .json) のパスを管理・取得するクラス。
    CSV読み込みは汎用的に全カラムを文字列として読み込む。
    """
    DEFAULT_SETTINGS_DIR = "../settings"

    def __init__(self, settings_dir=None):
        self.settings_dir_relative = settings_dir if settings_dir is not None else self.DEFAULT_SETTINGS_DIR

    def _get_resource_path(self, filename):
        """resource_path関数を使ってファイルへの絶対パスを取得する"""
        relative_path_from_script = os.path.join(self.settings_dir_relative, filename)
        full_path = resource_path(relative_path_from_script)
        return full_path

    def load_all_idpass(self, filename="idpass.csv"):
        """
        指定されたCSVファイル (デフォルト: idpass.csv) を読み込み、
        すべてのカラムを含むDataFrameとして返す。
        読み込み時、すべてのカラムを文字列(str)として扱う。
        """
        filepath = self._get_resource_path(filename)
        try:
            df = pd.read_csv(filepath, dtype=str)
            if df.empty:
                print(f"情報: ファイル '{filepath}' は空か、またはヘッダーのみです。")
                return df
            print(f"デバッグ: {filename} 読み込み成功 ({len(df)} 行, {len(df.columns)} カラム)")
            return df
        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません - {filepath}")
            return None
        except pd.errors.EmptyDataError:
             print(f"エラー: ファイル '{filepath}' は完全に空です。")
             return None
        except Exception as e:
            print(f"エラー: {filename} の読み込み中に予期せぬエラー - {e}")
            traceback.print_exc()
            return None

    def get_chromedriver_path(self, filename="chromedriver_134.0.6998.89.exe"):
        """ChromeDriverのパスを取得する"""
        filepath = self._get_resource_path(filename)
        if os.path.exists(filepath): return filepath
        else: print(f"エラー: ChromeDriverが見つかりません - {filepath}"); return None

    def get_gcp_key_path(self, filename="code2-455205-e4312a13bb37.json"):
        """GCPサービスアカウントキーのパスを取得する"""
        filepath = self._get_resource_path(filename)
        if os.path.exists(filepath): return filepath
        else: print(f"エラー: GCPキーファイルが見つかりません - {filepath}"); return None


# --- 食べログログインクラス ---
class TabelogLogin:
    """
    食べログオーナーアカウントへのログイン/ログアウト処理を行うクラス。
    WebDriverの初期化/終了も管理する。
    """
    LOGIN_URL = "https://owner.tabelog.com/owner_account/login"
    LOGOUT_URL_FRAGMENT = "/owner_account/logout"
    LOGOUT_BUTTON_XPATH = '//a[contains(@href, "logout")] | //button[contains(text(), "ログアウト")] | //*[@data-testid="logout-button"] | //*[@id="js-logout-btn"]'

    ID_XPATH = '//*[@id="login_id"]'
    PASS_XPATH = '//*[@id="password"]'
    LOGIN_BUTTON_XPATH = '//button[@type="submit"]'

    # --- ★★★ ログイン成功確認用の要素XPath (手順1で特定したものに書き換えてください) ★★★ ---
    # 例: LOGIN_SUCCESS_CHECK_XPATH = '//*[@id="js-header-shop-name"]' # ヘッダー店舗名
    # 例: LOGIN_SUCCESS_CHECK_XPATH = '//nav[contains(@class,"navigation")]' # サイドメニュー
    LOGIN_SUCCESS_CHECK_XPATH = '//*[@id="js-header-shop-name"]' # 仮のXPath, 必ず書き換えてください
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★ ---

    def __init__(self, settings_dir="../settings"):
        self.settings_loader = SettingsLoader(settings_dir=settings_dir)
        self._driver = None
        self.wait = None
        self._logged_in_user = None

    def initialize_driver(self):
        """WebDriverを初期化する。成功ならTrue、失敗ならFalse"""
        if self._driver: return True
        chromedriver_path = self.settings_loader.get_chromedriver_path()
        if not chromedriver_path: print("エラー: ChromeDriverパス取得失敗"); return False
        self.settings_loader.get_gcp_key_path() # 存在確認
        chrome_service = Service(chromedriver_path)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--window-size=1920,1080"); chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        try:
            self._driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            self.wait = WebDriverWait(self._driver, 15) # タイムアウト15秒
            print("WebDriverの初期化成功")
            return True
        except Exception as e:
            print(f"エラー: WebDriver初期化失敗 - {e}"); self._driver = None; return False

    def login(self, username, password):
        """指定されたIDとパスワードでログインする。成功ならTrue、失敗ならFalse"""
        if not self._driver: print("エラー: WebDriver未初期化"); return False
        if self._logged_in_user == username: print(f"デバッグ: 既に {username} でログイン済み"); return True
        if self._logged_in_user:
            if not self.logout(): print("警告: ログアウト失敗。ログイン続行")

        try:
            print(f"ログイン試行: {username}")
            self._driver.get(self.LOGIN_URL)
            id_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, self.ID_XPATH)))
            id_field.clear(); id_field.send_keys(username)
            pass_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, self.PASS_XPATH)))
            pass_field.clear(); pass_field.send_keys(password)
            login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.LOGIN_BUTTON_XPATH)))
            login_button.click()
            print("ログインボタンクリック")

            # --- ★★★ ログイン成功確認 (要素待機に変更) ★★★ ---
            try:
                print(f"  ログイン成功確認中 (要素が表示されるまで待機: {self.LOGIN_SUCCESS_CHECK_XPATH})")
                # visibility_of_element_located を使う (要素が表示状態になるまで待つ)
                self.wait.until(EC.visibility_of_element_located((By.XPATH, self.LOGIN_SUCCESS_CHECK_XPATH)))
                current_url = self._driver.current_url # 成功後にURL取得
                print(f"ログイン成功: {username}, 要素確認OK, URL: {current_url}")
                self._logged_in_user = username
                return True
            except TimeoutException:
                # タイムアウトした場合 = 要素が見つからなかった
                current_url = self._driver.current_url
                print(f"エラー: ログイン後の成功確認要素({self.LOGIN_SUCCESS_CHECK_XPATH})が見つかりませんでした (タイムアウト)。ユーザー: {username}, URL: {current_url}")
                error_messages = self._check_login_error_messages()
                if error_messages:
                    print(f"ログインページのエラーメッセージ: {error_messages}")
                else:
                    # スクリーンショットを保存して状況を確認
                    try:
                        ts = int(time.time())
                        filename = f"login_fail_{username}_{ts}.png"
                        self._driver.save_screenshot(filename)
                        print(f"スクリーンショットを保存しました: {filename}")
                    except Exception as ss_err:
                        print(f"スクリーンショット保存失敗: {ss_err}")
                self._logged_in_user = None
                return False
            # --- ★★★ 修正終了 ★★★ ---

        except Exception as e:
            print(f"エラー: ログイン処理 ({username}) 中に予期せぬエラー - {e}")
            traceback.print_exc()
            self._logged_in_user = None
            return False

    def logout(self):
        """現在ログイン中のユーザーをログアウトする。成功ならTrue、失敗ならFalse"""
        # (変更なし)
        if not self._driver: print("警告: WebDriver無し。ログアウト不可"); return True
        if not self._logged_in_user: print("デバッグ: ログアウト済み"); return True
        print(f"ログアウト試行: {self._logged_in_user}")
        try:
            try:
                 logout_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, self.LOGOUT_BUTTON_XPATH)))
                 self._driver.execute_script("arguments[0].click();", logout_button)
                 print("ログアウトボタンクリック")
            except Exception as button_error:
                 print(f"警告: ログアウトボタン失敗({button_error})。URL遷移試行")
                 # 代替案を試す...

            self.wait.until(EC.url_contains("login")) # ログインページに戻るのを待つ
            print(f"ログアウト成功: {self._logged_in_user}")
            self._logged_in_user = None
            return True
        except Exception as e:
            print(f"エラー: ログアウト処理中 - {e}")
            try: self._driver.get(self.LOGIN_URL) # ログインページに戻しておく
            except: pass
            self._logged_in_user = None; return False


    def get_driver(self):
        """現在のWebDriverインスタンスを返す"""
        # (変更なし)
        return self._driver

    def close(self):
        """WebDriverインスタンスを安全に閉じる"""
        # (変更なし)
        if self._driver:
            try: self._driver.quit(); print("WebDriver終了")
            except Exception as e: print(f"WebDriver終了エラー: {e}")
            finally: self._driver = None; self.wait = None; self._logged_in_user = None

    def _check_login_error_messages(self):
        """ログインページのエラーメッセージを取得試行 (内部メソッド)"""
        # (変更なし)
        error_texts = []
        possible_error_selectors = [".c-form__error", ".error_message", ".alert-danger", 'div[class*="error"]', 'p[class*="error"]']
        if not self._driver: return []
        time.sleep(0.5)
        for selector in possible_error_selectors:
            try:
                find_method = By.XPATH if selector.startswith('/') or selector.startswith('(') else By.CSS_SELECTOR
                elements = self._driver.find_elements(find_method, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip(): error_texts.append(element.text.strip())
            except: pass
        return list(set(error_texts))