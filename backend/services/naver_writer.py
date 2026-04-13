"""
Naver Blog Writer using Selenium.
Adapted from Blog-main/NaverBlogWriter.py
Runs synchronously in a background thread.
"""
from __future__ import annotations
import io, json, os, random, time
from typing import List, Optional

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


class NaverBlogWriter:
    """Selenium-based Naver blog post writer."""

    def __init__(
        self,
        naver_id: str,
        naver_pw: str,
        chrome_user_data_dir: str = "C:/Utilities/Blog/chrome-user-data",
    ):
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.chrome_user_data_dir = chrome_user_data_dir
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
        opts = Options()
        opts.add_argument("lang=ko_KR")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        if self.chrome_user_data_dir:
            opts.add_argument(f"user-data-dir={self.chrome_user_data_dir}")
        self.driver = webdriver.Chrome(service=Service(), options=opts)

    # ── Human-like helpers ────────────────────────────────────────────────────

    def _delay(self, lo=1.0, hi=3.0):
        time.sleep(random.uniform(lo, hi))

    def _move(self, element):
        ActionChains(self.driver).move_to_element(element).perform()
        self._delay(0.3, 0.8)

    def _scroll(self, direction="down"):
        dy = 300 if direction == "down" else -300
        self.driver.execute_script(f"window.scrollBy(0, {dy});")
        self._delay(0.5, 1.0)

    # ── Login ─────────────────────────────────────────────────────────────────

    def _login(self):
        self.driver.get("https://nid.naver.com/nidlogin.login?mode=form&url=https://blog.naver.com/")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        ).click()
        pyperclip.copy(self.naver_id)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(0.8, 1.2)

        self.driver.find_element(By.ID, "pw").click()
        pyperclip.copy(self.naver_pw)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(0.8, 1.2)

        self.driver.find_element(By.ID, "log.login").click()
        try:
            WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CLASS_NAME, "button_signout"))
            )
        except Exception:
            raise RuntimeError("Naver 로그인 실패 — ID/PW 확인 또는 보안 인증 필요")

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
        """Insert text content (15px font, backtick toggles bold)."""
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-font-size-code-toolbar-button"))
        ).click()
        self._delay(0.3, 0.6)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-toolbar-option-font-size-code-fs15-button"))
        ).click()
        self._delay(0.3, 0.6)
        for char in content.replace("\\n", "\n"):
            if char == "`":
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("b").key_up(Keys.CONTROL).perform()
            else:
                ActionChains(self.driver).send_keys(char).perform()
        self._delay(0.1, 0.2)

    def _insert_header(self, content: str):
        """Insert header (Ctrl+Alt+Q shortcut)."""
        for _ in range(2):
            ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("q").key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
            self._delay(0.1, 0.2)
        ActionChains(self.driver).send_keys(content).perform()

    def _insert_image(self, image_path: str):
        """Paste image from clipboard."""
        self._copy_image_to_clipboard(image_path)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self._delay(3, 4)

    def _insert_url(self, url: str):
        """Insert OG link card."""
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
            # Fallback: close popup and type as text
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
        """Upload a local video file to Naver Blog using the video insert button."""
        if not HAS_PYAUTOGUI:
            raise RuntimeError("pyautogui 없음 (Windows 전용 기능)")
        try:
            # Click video insert toolbar button
            video_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "se-video-toolbar-button"))
            )
            self._move(video_btn)
            video_btn.click()
            self._delay(1.5, 2.0)

            # Click "내 PC에서 올리기" (local file upload)
            local_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "se-video-local-button"))
            )
            self._move(local_btn)
            local_btn.click()
            self._delay(2.0, 2.5)

            # Paste file path into the OS file-picker dialog
            pyperclip.copy(video_path.replace("/", "\\"))
            pyautogui.hotkey("ctrl", "v")
            self._delay(0.5, 1.0)
            pyautogui.press("enter")
            self._delay(5, 8)  # Wait for upload
        except Exception as e:
            # Fallback: skip video and continue
            try:
                close = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-close-button"))
                )
                close.click()
            except Exception:
                pass

    def _insert_url_text(self, url: str):
        """Insert large '최저가 구매하러 가기' bold link."""
        short_url = self.shorten_url(url)
        # Two enters then arrow up
        ActionChains(self.driver).send_keys(Keys.ENTER, Keys.ENTER, Keys.ARROW_UP, Keys.ARROW_UP).perform()
        self._delay(0.4, 0.6)
        # Bold on
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("B").key_up(Keys.CONTROL).perform()
        self._delay(0.3, 0.5)
        # Large font
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-font-size-code-toolbar-button"))
        ).click()
        self._delay(0.3, 0.5)
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "se-toolbar-option-font-size-code-fs38-button"))
        ).click()
        self._delay(0.3, 0.5)
        # Text
        ActionChains(self.driver).send_keys(" 최저가 구매하러 가기 ").perform()
        self._delay(0.4, 0.6)
        # Select text and add link
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
        # Move to next line
        ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).perform()
        self._delay(0.4, 0.6)

    # ── Main write method ─────────────────────────────────────────────────────

    def write(
        self,
        title: str,
        elements: list,       # list of {"type": ..., "content": ...}
        thumbnail_path: str = "",
    ) -> str:
        """Write and publish a Naver blog post. Returns the published blog URL."""
        try:
            self._init_driver()
            self._login()

            self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
            self.driver.switch_to.frame("mainFrame")
            self._delay(2, 3)

            # Dismiss modal if present
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "se-popup-button-cancel"))
                ).click()
            except Exception:
                pass

            # ── Title ──────────────────────────────────────────────────────────
            title_el = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"제목")]'))
            )
            self._move(title_el)
            title_el.click()
            ActionChains(self.driver).send_keys(title).perform()
            self._delay(0.3, 0.5)

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
            text_area = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"본문에")]'))
            )
            self._move(text_area)
            text_area.click()

            for el in elements:
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

                # Press Enter to move to next line
                ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("h").key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
                self._delay(0.1, 0.2)

            # ── Publish ────────────────────────────────────────────────────────
            publish_btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '/html/body/div[1]/div/div[1]/div/div[3]/div[2]/button')
                )
            )
            self._move(publish_btn)
            publish_btn.click()
            self._delay(2, 3)

            sympathy = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//label[contains(text(),"공감허용")]'))
            )
            self._move(sympathy)
            sympathy.click()
            self._delay(1, 1.5)

            confirm = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '/html/body/div[1]/div/div[1]/div/div[3]/div[2]/div/div/div/div[8]/div/button')
                )
            )
            self._move(confirm)
            confirm.click()
            self._delay(3, 4)

            blog_url = self.driver.current_url
            return blog_url
        finally:
            self._close()
