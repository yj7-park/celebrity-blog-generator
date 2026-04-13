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
        opts.add_argument("--start-maximized")
        opts.add_argument(f"--user-data-dir={self.chrome_user_data_dir}")
        self.driver = webdriver.Chrome(service=Service(), options=opts)
        # --start-maximized is unreliable on some Windows setups;
        # maximize_window() uses the OS API and is always reliable.
        try:
            self.driver.maximize_window()
        except Exception:
            pass

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
        2. Wait until URL settles to either nid.naver.com (login needed)
           or back to blog.naver.com (session alive).
        3. If session alive → skip login, notify caller via status_cb.
        4. If redirected to nid.naver.com → fill login form.
        5. Navigate back to the write page.
        """
        if status_cb:
            status_cb("logging_in", "블로그 에디터 로드 중...")

        self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
        _screenshot(self.driver, "01_after_goblogwrite")

        # Wait until the URL settles (login redirect or editor page), up to 8 s
        try:
            WebDriverWait(self.driver, 8).until(
                lambda d: "nid.naver.com" in d.current_url
                          or "PostWrite" in d.current_url
                          or "blog.naver.com" in d.current_url
            )
        except Exception:
            pass  # continue with whatever URL we have

        _screenshot(self.driver, "01b_settled")

        if "nid.naver.com" not in self.driver.current_url:
            print(f"[DEBUG] session valid (auto-login), url={self.driver.current_url}")
            if status_cb:
                status_cb("logging_in", "자동 로그인 세션 확인됨. 에디터 준비 중...")
            return  # session still valid — already on write page

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
        """카테고리 헤더 삽입 — SE One 인용구 스타일 + 오렌지 강조색."""
        # SE One 인용구 단락 스타일 적용 (Ctrl+Alt+Q)
        ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("q").key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
        self._delay(0.2, 0.3)
        # 헤더 텍스트를 오렌지 색상으로
        self._apply_text_color("E8531A")
        # 헤더 내용 입력
        ActionChains(self.driver).send_keys(content).perform()
        self._delay(0.1, 0.2)
        # 색상을 검정으로 리셋 후 단락 탈출
        self._apply_text_color("333333")
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
        self._delay(0.1, 0.2)

    def _insert_image(self, image_path: str):
        self._copy_image_to_clipboard(image_path)
        # win32clipboard can steal window focus — refocus via JS (do NOT call
        # switch_to.window() here as it would reset the mainFrame context)
        try:
            self.driver.execute_script("window.focus();")
        except Exception:
            pass
        self._delay(0.3, 0.5)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(3, 4)
        # 이미지 삽입 후 중앙 정렬
        self._apply_text_align("center")

    def _insert_url(self, url: str):
        short_url = self.shorten_url(url)
        link_btn = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-oglink-toolbar-button"))
        )
        self._move(link_btn)
        self.driver.execute_script("arguments[0].click();", link_btn)
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

    def _apply_text_color(self, hex_color: str):
        """글자색 적용 (커서 위치 또는 선택 텍스트에 적용).
        hex_color: 'FF6B35' 형식 (# 없이).
        실패 시 조용히 무시.
        """
        try:
            btn = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "se-font-color-toolbar-button"))
            )
            self.driver.execute_script("arguments[0].click();", btn)
            self._delay(0.4, 0.7)
            # SE One 컬러피커 hex 입력란 탐색
            for sel in [
                "input.se-colorpicker-custom-hex",
                ".se-colorpicker-custom-hex",
                "input[maxlength='6']",
                ".se-colorpicker input[type='text']",
            ]:
                try:
                    inp = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(hex_color.upper())
                        inp.send_keys(Keys.ENTER)
                        self._delay(0.3, 0.4)
                        return
                except Exception:
                    continue
            # fallback: Escape 닫기
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass

    def _apply_text_align(self, align: str = "center"):
        """단락 정렬 변경. align: 'left'|'center'|'right'"""
        shortcuts = {"left": "l", "center": "e", "right": "r"}
        key = shortcuts.get(align, "e")
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(key).key_up(Keys.CONTROL).perform()
        self._delay(0.1, 0.2)

    def _open_insert_menu(self):
        """빈 줄의 + 버튼(se-insert-point-marker-button)을 클릭해 삽입 메뉴 열기.

        The + button is hover-triggered: move the mouse near the editor body
        first so SE One renders it, then click via JS.
        """
        # Escape any open panel before opening the insert menu
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        self._delay(0.2, 0.3)
        # Move mouse to the editor area to trigger + button appearance
        try:
            editor_area = self.driver.find_element(
                By.CSS_SELECTOR, ".se-main-section"
            )
            ActionChains(self.driver).move_to_element(editor_area).perform()
            self._delay(0.3, 0.5)
        except Exception:
            pass
        marker = WebDriverWait(self.driver, 8).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".se-insert-point-marker-button")
            )
        )
        self.driver.execute_script("arguments[0].click();", marker)
        self._delay(0.5, 0.8)

    def _insert_divider(self, style: str = "line2"):
        """구분선 삽입. style: default|line1|line2|line3|line4

        빈 줄 + 버튼 → se-insert-menu-button-horizontalLine hover →
        서브패널 스타일 클릭.
        """
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
        self._delay(0.4, 0.6)
        self._open_insert_menu()

        hl_btn = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".se-insert-menu-button-horizontalLine")
            )
        )
        ActionChains(self.driver).move_to_element(hl_btn).perform()
        self._delay(0.5, 0.7)

        cls = f"se-insert-menu-sub-panel-button-horizontalLine-{style}"
        sub = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f".{cls}"))
        )
        self.driver.execute_script("arguments[0].click();", sub)
        self._delay(0.5, 0.8)

    def _insert_callout(self, content: str, style: str = "quotation_postit"):
        """callout 텍스트를 일반 본문 단락으로 삽입 (이탤릭체)."""
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
        self._delay(0.3, 0.5)
        # 이탤릭 on
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("I").key_up(Keys.CONTROL).perform()
        self._delay(0.15, 0.25)
        ActionChains(self.driver).send_keys(content).perform()
        self._delay(0.3, 0.4)
        # 이탤릭 off
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("I").key_up(Keys.CONTROL).perform()
        self._delay(0.15, 0.25)

    def _insert_url_text(self, url: str):
        """구매 링크 버튼 삽입 — 일반 본문에 중앙 정렬 굵은 텍스트 + 링크."""
        short_url = self.shorten_url(url)

        # 새 단락 시작
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
        self._delay(0.3, 0.5)

        # 중앙 정렬
        self._apply_text_align("center")
        self._delay(0.2, 0.3)

        # 굵게
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("B").key_up(Keys.CONTROL).perform()
        self._delay(0.15, 0.25)

        # 버튼 텍스트 입력
        ActionChains(self.driver).send_keys("🛒 최저가 구매하러 가기").perform()
        self._delay(0.4, 0.6)

        # 텍스트 전체 선택 (Home → Shift+End)
        ActionChains(self.driver).send_keys(Keys.HOME).perform()
        self._delay(0.15, 0.25)
        ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.END).key_up(Keys.SHIFT).perform()
        self._delay(0.4, 0.6)

        # 링크 적용 — Ctrl+K 단축키 우선 시도, 실패 시 툴바 버튼
        _link_ok = False
        try:
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("k").key_up(Keys.CONTROL).perform()
            self._delay(0.6, 0.9)
            link_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "se-custom-layer-link-input"))
            )
            link_input.click()
            self._delay(0.2, 0.3)
            ActionChains(self.driver).send_keys(short_url, Keys.ENTER).perform()
            self._delay(0.6, 0.9)
            _link_ok = True
            print(f"[WRITER] url_text link applied via Ctrl+K")
        except Exception as _ke:
            print(f"[WRITER] url_text Ctrl+K failed: {_ke!r}, trying toolbar button")
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            self._delay(0.3, 0.5)
            # 텍스트 다시 선택
            ActionChains(self.driver).send_keys(Keys.HOME).perform()
            self._delay(0.15, 0.25)
            ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.END).key_up(Keys.SHIFT).perform()
            self._delay(0.3, 0.5)
            try:
                link_btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "se-link-toolbar-button"))
                )
                self.driver.execute_script("arguments[0].click();", link_btn)
                self._delay(0.5, 0.8)
                link_input = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-custom-layer-link-input"))
                )
                link_input.click()
                self._delay(0.2, 0.3)
                ActionChains(self.driver).send_keys(short_url, Keys.ENTER).perform()
                self._delay(0.6, 0.9)
                _link_ok = True
                print(f"[WRITER] url_text link applied via toolbar")
            except Exception as _le:
                print(f"[WRITER] url_text link apply failed: {_le!r}")
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                self._delay(0.3, 0.5)

        # 왼쪽 정렬 복원, 굵기 해제
        ActionChains(self.driver).send_keys(Keys.END).perform()
        self._delay(0.15, 0.25)
        self._apply_text_align("left")
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("B").key_up(Keys.CONTROL).perform()
        self._delay(0.2, 0.3)

    # ── Main write method ─────────────────────────────────────────────────────

    def write(
        self,
        title: str,
        elements: list,
        thumbnail_path: str = "",
        status_cb: Optional[StatusCallback] = None,
        tags: list | None = None,
    ) -> str:
        """Write and publish a Naver blog post. Returns the published blog URL."""
        try:
            self._init_driver()
            self._login(status_cb)

            self.driver.switch_to.frame("mainFrame")
            # Wait for SE One toolbar to be visible — confirms editor is ready
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".se-toolbar-button-publish")
                    )
                )
            except Exception:
                pass  # toolbar selector may differ; fall through with delay
            self._delay(2, 3)
            _screenshot(self.driver, "06_in_mainframe")

            # Dismiss any popups (draft recovery, announcements, etc.) — up to 3 rounds
            _POPUP_SELECTORS = (
                ".se-popup-button-cancel",
                ".se-popup-button-close",
                "button[data-action='cancel']",
                ".popup_close",
                ".se-popup-close-button",
            )
            for _round in range(3):
                _dismissed = False
                for _sel in _POPUP_SELECTORS:
                    try:
                        _btn = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, _sel))
                        )
                        self.driver.execute_script("arguments[0].click();", _btn)
                        self._delay(0.5, 1.0)
                        _dismissed = True
                        break
                    except Exception:
                        continue
                if not _dismissed:
                    break  # no popup found this round → done
            _screenshot(self.driver, "07_after_popup_handling")

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
            if thumbnail_path:
                abs_thumb = os.path.abspath(thumbnail_path)
                _thumb_done = False
                # Try Selenium file-input injection first (no pyautogui needed)
                _THUMB_INPUT_SELECTORS = [
                    "input.se-cover-image-upload-input",
                    ".se-cover-button-area input[type='file']",
                    ".se-cover-image-wrap input[type='file']",
                    "input[type='file'][accept*='image']",
                ]
                for _sel in _THUMB_INPUT_SELECTORS:
                    try:
                        _finput = self.driver.find_element(By.CSS_SELECTOR, _sel)
                        self.driver.execute_script("arguments[0].style.display='block';", _finput)
                        _finput.send_keys(abs_thumb)
                        self._delay(2, 3)
                        _thumb_done = True
                        _screenshot(self.driver, "10a_thumbnail_selenium")
                        break
                    except Exception:
                        continue
                # Fallback: click the button, then inject via the newly-created input
                if not _thumb_done:
                    try:
                        _cover_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, ".se-cover-button-local-image-upload, .se-cover-button-area button")
                            )
                        )
                        self.driver.execute_script("arguments[0].click();", _cover_btn)
                        self._delay(1, 1.5)
                        # After the click, the file-input should become findable
                        _finput = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                        )
                        self.driver.execute_script("arguments[0].style.display='block';", _finput)
                        _finput.send_keys(abs_thumb)
                        self._delay(2, 3)
                        _screenshot(self.driver, "10a_thumbnail_fallback")
                    except Exception as _thumb_err:
                        print(f"[WRITER] thumbnail upload skipped: {_thumb_err!r}")

            # ── Body ───────────────────────────────────────────────────────────
            _screenshot(self.driver, "10_before_body")
            body_el = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".se-section-text .se-text-paragraph")
                )
            )
            ActionChains(self.driver).move_to_element(body_el).click().perform()
            _screenshot(self.driver, "11_after_body_click")

            for idx, el in enumerate(elements):
                _naver_cancel.check("Naver 글쓰기가 취소되었습니다.")
                el_type = el.get("type", "")
                content = el.get("content", "")
                preview = str(content)[:40] if content else ""
                print(f"[WRITER] element {idx}: type={el_type!r} content={preview!r}")
                self._scroll("down")

                try:
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
                    elif el_type == "divider":
                        self._insert_divider(str(content) if content else "line2")
                    elif el_type == "callout":
                        style = el.get("style", "quotation_postit")
                        self._insert_callout(str(content), style)
                    print(f"[WRITER] element {idx} OK")
                except Exception as _elem_err:
                    print(f"[WRITER] element {idx} FAILED: {_elem_err!r}")
                    _screenshot(self.driver, f"err_{idx:02d}_{el_type}")
                    raise

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

            # ── Tags ───────────────────────────────────────────────────────────
            _tags = [t.strip() for t in (tags or []) if t.strip()]
            if _tags:
                _TAG_SELECTORS = [
                    ".se-tag-form input",
                    "input.tag_input",
                    ".tag_area input[type='text']",
                    "[placeholder*='태그']",
                    ".publishLayer_tag_area input",
                ]
                _tag_input = None
                for _sel in _TAG_SELECTORS:
                    try:
                        _tag_input = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, _sel))
                        )
                        break
                    except Exception:
                        continue
                if _tag_input:
                    for _tag in _tags:
                        try:
                            self.driver.execute_script("arguments[0].click();", _tag_input)
                            self._delay(0.2, 0.3)
                            _tag_input.send_keys(_tag)
                            self._delay(0.2, 0.3)
                            # SE One accepts Enter or comma to confirm a tag
                            _tag_input.send_keys(Keys.RETURN)
                            self._delay(0.3, 0.5)
                        except Exception as _te:
                            print(f"[WRITER] tag '{_tag}' input failed: {_te!r}")
                    _screenshot(self.driver, "22a_after_tags")
                else:
                    print("[WRITER] tag input field not found — skipping tags")

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
