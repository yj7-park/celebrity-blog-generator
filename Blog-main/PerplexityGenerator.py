from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import subprocess

import pyperclip
import time
import os
import random


class PerplexityGenerator:
    url = "https://www.perplexity.ai/search/system-gagyeog-pyeongjeom-byeo-UqZ1tlUcR0CJYjkXiZ8mhA"

    driver = None
    item = ""
    items = []
    generated_texts = []

    def __init__(self, item, root_dir, items):
        import os
        self.root_dir = root_dir
        self.image_path = f"{root_dir}/images"
        os.makedirs(root_dir, exist_ok=True)
        os.makedirs(self.image_path, exist_ok=True)
        self.item = item

        self.items = items

    # destroyer
    def __del__(self):
        if self.driver is not None:
            self.driver.close()
            self.driver.quit()

    def _init(self):

        # read elements from json file
        # with open(self.path, "r", encoding="utf-8") as f:
        #     elements = json.load(f)["elements"]

        subprocess.Popen(
            r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222"'
        )
        # subprocess.Popen(r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Utilities\Blog\chrome-user-data"')
        # 크롬 옵션 설정
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        # chrome_options.add_argument("lang=ko_KR")
        # chrome_options.add_argument('no-sandbox')
        # chrome_options.add_argument('disable-gpu')
        # chrome_options.add_argument("disable-dev-shm-usage")
        # chrome_options.add_argument("--log-level=3")
        # chrome_options.add_argument("--disable-3d-apis")
        # chrome_options.add_argument("user-data-dir=C:/Utilities/Blog/chrome-user-data")

        # 웹드라이버 실행
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver  # , elements

    # 로그인 함수
    def _login(self):

        self.driver.get(self.url)

        # button 중 div의 text가 '로그인'인 버튼 찾기
        # login_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '로그인')]")))

        # login_button.click()

        # WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "id"))).click()

        # # 클립보드를 이용한 아이디 입력
        # pyperclip.copy(self.naver_id)
        # ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        # time.sleep(1)

        # # 클립보드를 이용한 비밀번호 입력
        # self.driver.find_element(By.ID, "pw").click()
        # pyperclip.copy(self.naver_pw)
        # ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        # time.sleep(1)

        # # 로그인 버튼 클릭
        # self.driver.find_element(By.ID, "log.login").click()

        # # 로그인 성공 여부 확인
        # try:
        #     WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "button_signout")))
        #     print('로그인 성공')
        # except:
        #     print('로그인 실패')
        #     self.driver.quit()

    # 랜덤 딜레이 함수
    def _random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

    # 휴먼 액션: 마우스 이동
    def _human_mouse_movement(self, element):
        action = ActionChains(self.driver)
        action.move_to_element(element).perform()
        self._random_delay(0.5, 1.5)

    def generate_texts_images(self, skip_text=False):
        file_path = (
            f'{self.root_dir}/04-product_descriptions.txt'
        )
        images_file_path = (
            f'{self.root_dir}/05-product_image_paths.txt'
        )
        # check if file exists
        if os.path.isfile(file_path) and os.path.isfile(images_file_path):
            print("File exists, skipping process.")
            return file_path, images_file_path
        images = []
        for item in self.items:
            # self.generated_texts.append(self.generate_text(item))
            text, image_urls = self.generate_text_images(item, skip_text)
            self.generated_texts.append(text)
            images.extend(image_urls)
        # save text as file
        if not os.path.isfile(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.generated_texts))
        else:
            print("File exists, skipping process.")
        if not os.path.isfile(images_file_path):
            with open(images_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(images))
        else:
            print("File exists, skipping process.")
        return file_path, images_file_path

    def generate_text_images(self, item, skip_text=False):
        print(item)
        if self.driver == None:
            self.driver = self._init()
            self._login()
        edit = (
            WebDriverWait(self.driver, 10)
            .until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), '쿼리 편집')]")
                )
            )
            .find_element(By.XPATH, "./../..")
        )

        # TODO: system command
        if not skip_text:
            ActionChains(self.driver).move_to_element(edit).click().key_down(
                Keys.CONTROL
            ).send_keys("a").key_up(Keys.CONTROL).send_keys(
                '{system:가격/평점/별점/리뷰수 정보 제외 필수}{system:"하네요/하답니다"와 같은 표현 자제 - 대신 "하구요/해요" 사용}{system:제품소개 이외에 불필요한 문장 금지}{system:8~10문장으로 유동적으로 작성}'
                + item
            ).send_keys(
                Keys.ENTER
            ).pause(
                2
            ).send_keys(
                Keys.ENTER
            ).perform()

            time.sleep(2)

            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), '다시 쓰기')]")
                )
            )
            time.sleep(2)

        text_elements = self.driver.find_elements(
            By.XPATH,
            "//div[@class='mb-md' and not(@class='flex') and not(@class='relative')]/div/div/div/div/span",
        )
        text = ""
        for text_element in text_elements:
            text_line = text_element.text.replace("\n", "")
            if len(text_line) > 3 or text_line == ".":
                text += text_line

        top_image_element = self.driver.find_element(By.CLASS_NAME, "object-top")
        button = top_image_element.find_element(By.XPATH, "./../..")
        self._human_mouse_movement(button)
        button.click()
        self._random_delay(0.5, 1.0)

        # TODO: 이미지 읽는 순서를 가로로 (현재는 세로 순서로 읽음)
        image_elements = self.driver.find_elements(By.CLASS_NAME, r"max-h-\[70vh\]")
        count = 0
        image_urls = []
        for element in image_elements[1:]:
            self._random_delay(0.5, 1.0)
            print(element.get_attribute("alt"))
            # if "blog" in element.get_attribute("alt"):
            if "blog" in element.get_attribute("alt"):
                continue
            # if "coupang" not in element.get_attribute("alt"):
            #     continue
            element.click()
            self._random_delay(0.5, 1.0)
            image_url = self.driver.find_element(
                By.CLASS_NAME, r"max-h-\[70vh\]"
            ).get_attribute("src")
            print(image_url)
            image_urls.append(image_url)
            count += 1
            if count >= 3:
                break
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        self._random_delay(2.5, 3.0)
        return text, image_urls

    def generate_texts(self):
        file_path = (
            f"C:/Utilities/Blog/items/{self.item}/{self.item}_generated_text.txt"
        )
        # check if file exists
        if os.path.isfile(file_path):
            print("File exists, skipping process.")
            return file_path
        for item in self.items:
            self.generated_texts.append(self.generate_text(item))
        # save text as file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.generated_texts))
        return file_path

    def generate_text(self, item):
        print(item)
        if self.driver == None:
            self.driver = self._init()
            self._login()
        edit = (
            WebDriverWait(self.driver, 10)
            .until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), '쿼리 편집')]")
                )
            )
            .find_element(By.XPATH, "./../..")
        )

        # TODO: system command
        ActionChains(self.driver).move_to_element(edit).click().key_down(
            Keys.CONTROL
        ).send_keys("a").key_up(Keys.CONTROL).send_keys(
            '{system:가격/평점/별점/리뷰수 정보 제외 필수}{system:"하네요/하답니다"와 같은 표현 자제 - 대신 "하구요/해요" 사용}{system:제품소개 이외에 불필요한 문장 금지}{system:8~10문장으로 유동적으로 작성}'
            + item
        ).send_keys(
            Keys.ENTER
        ).pause(
            2
        ).send_keys(
            Keys.ENTER
        ).perform()

        time.sleep(2)

        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(text(), '다시 쓰기')]")
            )
        )
        time.sleep(2)

        text_elements = self.driver.find_elements(
            By.XPATH,
            "//div[@class='mb-md' and not(@class='flex') and not(@class='relative')]/div/div/div/div/span",
        )
        text = ""
        for text_element in text_elements:
            text_line = text_element.text.replace("\n", "")
            if len(text_line) > 3 or text_line == ".":
                text += text_line
        return text

        # # placeholder가 '후속 질문하기'인 textarea 찾기
        # textarea = WebDriverWait(self.driver, 10).until(
        #     EC.presence_of_element_located(
        #         (By.XPATH, "//textarea[contains(@placeholder, '후속 질문하기')]")
        #     )
        # )
        # time.sleep(1)
        # textarea.send_keys(item)
        # textarea.send_keys(Keys.ENTER)
        # time.sleep(1)
        # textarea = WebDriverWait(self.driver, 10).until(
        #     EC.presence_of_element_located(
        #         (By.XPATH, "//textarea[contains(@placeholder, '후속 질문하기')]")
        #     )
        # )


# main
if __name__ == "__main__":
    item = "test"
    items = [
        "스위스밀리터리 VANTORA 여행용캐리어 SM-B420 B424 B428",
        # "REGESY 여행용캐리어",
        # "TRAVEL SENTRY 여행용 캐리어",
    ]
    generator = PerplexityGenerator(item, items)
    desc_file_path, images_file_path = generator.generate_texts_images(skip_text=True)
    # 3-1. (제품별) 이미지 생성
    with open(images_file_path, "r", encoding="utf-8") as f:
        image_list = f.read().splitlines()
    for i, url in enumerate(image_list):
        index = (i // 3) + 1
        import os

        try:
            os.makedirs(f"C:/Utilities/Blog/images/{item}/{index}")
        except:
            pass
        image_index = i % 3 + 1
        print(i, index, image_index)
        image_path = f"C:/Utilities/Blog/images/{item}/{index}/{image_index}.png"
        if os.path.exists(image_path):
            print("File exists, skipping process.")
        else:
            import requests
            from io import BytesIO
            from PIL import Image

            response = requests.get(url)
            # resize image to 400x400
            image = Image.open(BytesIO(response.content)).resize((400, 400))
            # add watermark
            image.getdata()
            watermark = Image.open(
                "C:/Utilities/Blog/images/watermark.png"
            ).resize((400, 400))
            new_data = []
            for i, j in zip(image.getdata(), watermark.getdata()):
                if j[0] < 255 and j[1] < 255 and j[2] < 255:
                    new_data.append(j)
                else:
                    new_data.append(i)
            image.putdata(new_data)
            # save image to file
            image.save(image_path)
    try:
        del generator
    except:
        pass
    # write blog post with multiple elements
    # ai.write_blog_post()
