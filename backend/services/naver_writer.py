"""
Naver Blog Writer using Selenium.
Adapted from Blog-main/NaverBlogWriter.py
Runs synchronously in a background thread.

Session strategy
----------------
Chrome user data dir (chrome-user-data/ inside the project root) persists
cookies across runs. On the first launch, or whenever the Naver session
expires, the login form is filled automatically.

If Naver shows a security/CAPTCHA page instead of logging in directly,
the browser stays open and a status callback is fired so the caller
can notify the user. The code then waits up to 5 minutes for the user
to complete manual verification in the browser window.
"""
from __future__ import annotations
import io, os, random, time
from pathlib import Path
from typing import Callable, Optional

from services.cancel_token import naver as _naver_cancel

# Debug screenshots directory
_DEBUG_DIR = Path(__file__).resolve().parents[2] / "debug-screenshots"

import pyperclip

# Optional Windows-only imports
try:
    import win32clipboard
    from PIL import Image
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Default: chrome-user-data/ at project root (two levels above this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_USER_DATA = str(_PROJECT_ROOT / "chrome-user-data")

StatusCallback = Callable[[str, str], None]   # (phase, message) → None


def _screenshot(driver, name: str):
    """Save a debug screenshot + page HTML to debug-screenshots/."""
    try:
        os.makedirs(_DEBUG_DIR, exist_ok=True)
        # Screenshot
        png_path = str(_DEBUG_DIR / f"{name}.png")
        driver.save_screenshot(png_path)
        # HTML
        html_path = str(_DEBUG_DIR / f"{name}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- url: {driver.current_url} -->\n")
            f.write(driver.page_source)
        print(f"[DEBUG] {name}  url={driver.current_url}")
    except Exception as e:
        print(f"[DEBUG] screenshot failed ({name}): {e}")


class NaverBlogWriter:
    """Selenium-based Naver blog post writer."""

    def __init__(
        self,
        naver_id: str,
        naver_pw: str,
        chrome_user_data_dir: str = "",
    ):
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        # Empty string → use project-local default
        self.chrome_user_data_dir = chrome_user_data_dir or _DEFAULT_USER_DATA
        self.driver: Optional[webdriver.Chrome] = None

    def __del__(self):
        self._close()

    def _close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _init_driver(self):
        os.makedirs(self.chrome_user_data_dir, exist_ok=True)
        opts = Options()
        opts.add_argument("--lang=ko-KR")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"--user-data-dir={self.chrome_user_data_dir}")
        self.driver = webdriver.Chrome(service=Service(), options=opts)

    # ── Human-like helpers ────────────────────────────────────────────────────

    def _delay(self, lo=1.0, hi=3.0):
        """Human-like delay that wakes immediately if cancel is requested."""
        _naver_cancel.interruptible_sleep(random.uniform(lo, hi))

    def _move(self, element):
        ActionChains(self.driver).move_to_element(element).perform()
        self._delay(0.3, 0.8)

    def _scroll(self, direction="down"):
        dy = 300 if direction == "down" else -300
        self.driver.execute_script(f"window.scrollBy(0, {dy});")
        self._delay(0.5, 1.0)

    # ── Login ─────────────────────────────────────────────────────────────────

    def _do_login_form(self, status_cb: Optional[StatusCallback] = None):
        """Fill and submit the Naver login form.

        After submitting:
        - If redirected away from nidlogin quickly → success.
        - If Naver shows a security/CAPTCHA page (still on nid.naver.com
          but not nidlogin.login) → fire status_cb and wait up to 5 min
          for the user to complete verification in the open browser window.
        """
        _screenshot(self.driver, "02_login_page")
        id_el = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        )
        id_el.click()
        self._delay(0.3, 0.5)
        pyperclip.copy(self.naver_id)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(0.5, 0.8)

        pw_el = self.driver.find_element(By.ID, "pw")
        pw_el.click()
        self._delay(0.3, 0.5)
        pyperclip.copy(self.naver_pw)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(0.5, 0.8)

        _screenshot(self.driver, "03_before_submit")
        self.driver.find_element(By.ID, "log.login").click()

        # ── Phase 1: wait for redirect away from the login form (30 s) ──────
        try:
            WebDriverWait(self.driver, 30).until(
                lambda d: "nidlogin" not in d.current_url
            )
            _screenshot(self.driver, "04_after_submit")
        except Exception:
            _screenshot(self.driver, "04_timeout")
            raise RuntimeError(
                "Naver 로그인 실패 (30초 초과). ID/PW를 확인하거나 "
                f"chrome.exe --user-data-dir=\"{self.chrome_user_data_dir}\" 로 "
                "Chrome을 직접 열어 Naver에 로그인한 뒤 다시 시도하세요."
            )

        # ── Phase 2: if Naver showed a security page, wait for manual auth ──
        if "nid.naver.com" in self.driver.current_url:
            msg = (
                "Naver 보안 인증이 필요합니다. "
                "열려 있는 Chrome 창에서 인증을 완료해주세요. (최대 5분 대기)"
            )
            if status_cb:
                status_cb("verification_needed", msg)

            # Wait up to 5 minutes for the user to complete verification
            try:
                WebDriverWait(self.driver, 300).until(
                    lambda d: "nid.naver.com" not in d.current_url
                )
            except Exception:
                raise RuntimeError(
                    "Naver 보안 인증 시간 초과 (5분). "
                    "Chrome 창에서 인증을 완료한 뒤 다시 시도하세요."
                )

            if status_cb:
                status_cb("logging_in", "인증 완료. 블로그 작성 중...")

    def _login(self, status_cb: Optional[StatusCallback] = None):
        """Ensure the driver is logged into Naver.

        1. Navigate to the blog write page.
        2. If NOT redirected → session alive, skip login.
        3. If redirected to nid.naver.com → fill login form.
        4. Navigate back to the write page.
        """
        self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
        self._delay(2, 3)
        _screenshot(self.driver, "01_after_goblogwrite")

        if "nid.naver.com" not in self.driver.current_url:
            print(f"[DEBUG] session valid, url={self.driver.current_url}")
            return  # session still valid

        print(f"[DEBUG] redirected to login, url={self.driver.current_url}")
        self._do_login_form(status_cb)

        self._delay(1, 2)
        self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
        self._delay(2, 3)
        _screenshot(self.driver, "05_after_login_goblogwrite")

    # ── Image clipboard helper (Windows only) ─────────────────────────────────

    def _copy_image_to_clipboard(self, image_path: str):
        if not HAS_WIN32:
            raise RuntimeError("win32clipboard 없음 (Windows 전용 기능)")
        img = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="BMP")
        data = buf.getvalue()[14:]
        buf.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    # ── URL shortener ─────────────────────────────────────────────────────────

    @staticmethod
    def shorten_url(long_url: str) -> str:
        if "is.gd" in long_url:
            return long_url
        import requests
        try:
            r = requests.get(
                "https://is.gd/create.php",
                params={"format": "json", "url": long_url},
                timeout=6,
            )
            return r.json().get("shorturl", long_url)
        except Exception:
            return long_url

    # ── Element inserters ─────────────────────────────────────────────────────

    def _insert_text(self, content: str):
        # Set font size to 15 via the toolbar dropdown
        fs_btn = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-font-size-code-toolbar-button"))
        )
        self.driver.execute_script("arguments[0].click();", fs_btn)
        self._delay(0.3, 0.6)
        fs15_btn = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-toolbar-option-font-size-code-fs15-button"))
        )
        self.driver.execute_script("arguments[0].click();", fs15_btn)
        self._delay(0.3, 0.6)
        for char in content.replace("\\n", "\n"):
            if char == "`":
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("b").key_up(Keys.CONTROL).perform()
            else:
                ActionChains(self.driver).send_keys(char).perform()
        self._delay(0.1, 0.2)

    def _insert_header(self, content: str):
        for _ in range(2):
            ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("q").key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
            self._delay(0.1, 0.2)
        ActionChains(self.driver).send_keys(content).perform()

    def _insert_image(self, image_path: str):
        self._copy_image_to_clipboard(image_path)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(3, 4)

    def _insert_url(self, url: str):
        short_url = self.shorten_url(url)
        link_btn = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-oglink-toolbar-button"))
        )
        self._move(link_btn)
        link_btn.click()
        self._delay(1, 1.5)
        try:
            ActionChains(self.driver).send_keys(short_url + "\n").perform()
            self._delay(0.3, 0.5)
            confirm = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "se-popup-button-confirm"))
            )
            self._move(confirm)
            confirm.click()
            self._delay(1, 2)
        except Exception:
            try:
                close = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-close-button"))
                )
                self._move(close)
                close.click()
            except Exception:
                pass
            ActionChains(self.driver).send_keys(short_url + "\n").perform()
            self._delay(2, 3)

    def _insert_video(self, video_path: str):
        if not HAS_PYAUTOGUI:
            raise RuntimeError("pyautogui 없음 (Windows 전용 기능)")
        try:
            video_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "se-video-toolbar-button"))
            )
            self._move(video_btn)
            video_btn.click()
            self._delay(1.5, 2.0)
            local_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "se-video-local-button"))
            )
            self._move(local_btn)
            local_btn.click()
            self._delay(2.0, 2.5)
            pyperclip.copy(video_path.replace("/", "\\"))
            pyautogui.hotkey("ctrl", "v")
            self._delay(0.5, 1.0)
            pyautogui.press("enter")
            self._delay(5, 8)
        except Exception:
            try:
                close = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-close-button"))
                )
                close.click()
            except Exception:
                pass

    def _insert_url_text(self, url: str):
        short_url = self.shorten_url(url)
        ActionChains(self.driver).send_keys(Keys.ENTER, Keys.ENTER, Keys.ARROW_UP, Keys.ARROW_UP).perform()
        self._delay(0.4, 0.6)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("B").key_up(Keys.CONTROL).perform()
        self._delay(0.3, 0.5)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-font-size-code-toolbar-button"))
        ).click()
        self._delay(0.3, 0.5)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-toolbar-option-font-size-code-fs38-button"))
        ).click()
        self._delay(0.3, 0.5)
        ActionChains(self.driver).send_keys(" 최저가 구매하러 가기 ").perform()
        self._delay(0.4, 0.6)
        ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.HOME).key_up(Keys.SHIFT).perform()
        self._delay(0.3, 0.5)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-link-toolbar-button"))
        ).click()
        self._delay(0.3, 0.5)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-custom-layer-link-input"))
        ).click()
        self._delay(0.3, 0.5)
        ActionChains(self.driver).send_keys(short_url, Keys.ENTER).perform()
        ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).perform()
        self._delay(0.4, 0.6)

    # ── Main write method ─────────────────────────────────────────────────────

    def write(
        self,
        title: str,
        elements: list,
        thumbnail_path: str = "",
        status_cb: Optional[StatusCallback] = None,
    ) -> str:
        """Write and publish a Naver blog post. Returns the published blog URL."""
        try:
            self._init_driver()
            self._login(status_cb)

            self.driver.switch_to.frame("mainFrame")
            self._delay(2, 3)
            _screenshot(self.driver, "06_in_mainframe")

            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-button-cancel"))
                ).click()
                _screenshot(self.driver, "07_popup_dismissed")
            except Exception:
                pass

            # ── Title ──────────────────────────────────────────────────────────
            _screenshot(self.driver, "08_before_title")
            title_el = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".se-title-text .se-text-paragraph")
                )
            )
            ActionChains(self.driver).move_to_element(title_el).click().perform()
            self._delay(0.3, 0.5)
            ActionChains(self.driver).send_keys(title).perform()
            self._delay(0.3, 0.5)
            _screenshot(self.driver, "09_after_title")

            # ── Thumbnail ──────────────────────────────────────────────────────
            if thumbnail_path and HAS_PYAUTOGUI:
                self.driver.find_element(By.CLASS_NAME, "se-cover-button-local-image-upload").click()
                pyperclip.copy(thumbnail_path.replace("/", "\\"))
                self._delay(2, 2.5)
                pyautogui.hotkey("ctrl", "v")
                self._delay(2, 2.5)
                pyautogui.press("enter")
                self._delay(2, 2.5)

            # ── Body ───────────────────────────────────────────────────────────
            _screenshot(self.driver, "10_before_body")
            body_el = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".se-section-text .se-text-paragraph")
                )
            )
            ActionChains(self.driver).move_to_element(body_el).click().perform()
            _screenshot(self.driver, "11_after_body_click")

            for el in elements:
                _naver_cancel.check("Naver 글쓰기가 취소되었습니다.")
                el_type = el.get("type", "")
                content = el.get("content", "")
                self._scroll("down")

                if el_type == "text":
                    self._insert_text(str(content))
                elif el_type == "header":
                    self._insert_header(str(content))
                elif el_type == "image":
                    self._insert_image(str(content))
                elif el_type == "url":
                    self._insert_url(str(content))
                elif el_type == "url_text":
                    self._insert_url_text(str(content))
                elif el_type == "video":
                    self._insert_video(str(content))

                ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("h").key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
                self._delay(0.1, 0.2)

            # ── Publish ────────────────────────────────────────────────────────
            # Stay inside mainFrame — the entire editor page is inside it
            self._delay(1, 1.5)
            _screenshot(self.driver, "20_before_publish")

            publish_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-click-area='tpb.publish']")
                )
            )
            self._move(publish_btn)
            publish_btn.click()
            self._delay(2, 3)
            _screenshot(self.driver, "21_publish_dialog")

            # 공감허용 toggle (optional — ignore if not found)
            try:
                sympathy = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//label[contains(text(),"공감허용") or contains(text(),"공감 허용")]')
                    )
                )
                self._move(sympathy)
                sympathy.click()
                self._delay(1, 1.5)
            except Exception:
                pass

            _screenshot(self.driver, "22_before_confirm")
            # 발행 확인 버튼 (data-click-area="tpb*i.publish" or data-testid="seOnePublishBtn")
            confirm = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button[data-click-area='tpb*i.publish'], button[data-testid='seOnePublishBtn']")
                )
            )
            self._move(confirm)
            confirm.click()

            # Wait for the page to redirect to the published post
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: "Redirect=Write" not in d.current_url
                    and "blog.naver.com" in d.current_url
                )
            except Exception:
                pass  # URL might not change — return what we have

            _screenshot(self.driver, "99_before_return")
            return self.driver.current_url
        except Exception as e:
            if self.driver:
                _screenshot(self.driver, "99_error")
            raise
        finally:
            self._close()
