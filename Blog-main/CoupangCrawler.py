from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

import time
from PIL import Image
import io

import requests
import subprocess
import re

import os

class CoupangCrawler:
    driver = None

    urls = []

    def __init__(self, item, root_dir, urls):
        self.root_dir = root_dir
        self.image_path = f"{root_dir}/images"
        os.makedirs(root_dir, exist_ok=True)
        os.makedirs(self.image_path, exist_ok=True)

        self.urls = urls

    # destroyer
    def __del__(self):
        if self.driver is not None:
            self.driver.close()

    def _init(self):
        # 크롬 옵션 설정
        # chrome_options = Options()
        # chrome_options.add_argument("lang=ko_KR")
        # chrome_options.add_argument('no-sandbox')
        # chrome_options.add_argument('disable-gpu')
        # chrome_options.add_argument("disable-dev-shm-usage")
        # chrome_options.add_argument("--disable-3d-apis")
        # chrome_options.add_argument("user-data-dir=C:/Utilities/Blog/chrome-user-data")

        subprocess.Popen(
            r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222"'
        )
        # subprocess.Popen(r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Utilities\Blog\chrome-user-data"')
        # 크롬 옵션 설정
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        # 웹드라이버 실행
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver

    def _navigate_to_page(self, url):
        self.driver.get(url)

    def download_images(self):
        score_file_path = f'{self.root_dir}/031-product_scores.txt'
        review_file_path = f'{self.root_dir}/032-product_reviews.txt'
        if all(os.path.isfile(f) for f in [score_file_path, review_file_path]):
            print('File exists, skipping process.')
            return score_file_path, review_file_path
        
        self.driver = self._init()
        reviews = []
        scores = []
        for index, url in enumerate(self.urls):
            index = index + 1
            self._navigate_to_page(url)
            time.sleep(2)

            # try:
            #     elements = (
            #         WebDriverWait(self.driver, 5)
            #         .until(
            #             EC.presence_of_element_located(
            #                 (By.XPATH, '//img[@alt="thumb image"]')
            #             )
            #         )
            #     )
            # except:
            #     print(f"Failed to find images at {url}")
            #     raise
            
            # 별점, 리뷰수
            d = self.driver.find_element(By.NAME, 'description').get_attribute('content')
            print(d)

            try:
                score_pattern = r'별점 (\d+\.\d+)점'
                s = re.findall(score_pattern, d)
                # if s is empty list
                if len(s) == 0:
                    score_pattern = r'쿠팡에서 (\d+\.\d+) 구매하고'
                    s = re.findall(score_pattern, d)
                score = s[0]
                    

                review_pattern = r'리뷰 (\d+)개'
                r = re.findall(review_pattern, d)
                if len(r) == 0:
                    review_pattern = r'다른 (\d+) 제품도'
                    r = re.findall(review_pattern, d)
                review = r[0]
            except:
                score = '0'
                review = '0'

            print(score, review)
            scores.append(score)
            reviews.append(review)

            elements = self.driver.find_elements(By.XPATH, '//img[@alt="thumb image"]')

            product_image_path = f"{self.image_path}/{index}"
            os.makedirs(product_image_path, exist_ok=True)

            for i, element in enumerate(elements[:4]):
                i = i + 1
                print(element.get_attribute("src"))
                image_url = element.get_attribute("src").replace("48x48", "492x492")
                print(image_url)

                # url download
                try:
                    self._download_image(image_url, f"{product_image_path}/{i}.png")
                except:
                    pass
        
        with open(score_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(scores))
        with open(review_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(reviews))
        return score_file_path, review_file_path

    def _download_image(self, url, file_path):
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        
        # add watermark
        image = Image.blend(
            image.resize((400, 400)).convert("RGBA"),
            Image.open("C:/Utilities/Blog/images/watermark.png").resize((400, 400)),
            alpha=0.1,
        )
    
        # save image to file
        image.save(file_path)


# 실행 예제
if __name__ == "__main__":
    path = "./test.json"
    c = CoupangCrawler(
        "",
        "./test",
        [
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=8367621383&itemId=24177935579&vendorItemId=91626732076&traceid=V0-153-2a1efc354d05f2d6&requestid=20241228211540577068590657&token=31850C%7CMIXED",
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=8371451786&itemId=24191088021&vendorItemId=91209294130&traceid=V0-153-94fe647b27b8dff4&clickBeacon=742e9650-c515-11ef-9d5a-58c6d10d0882%7E3&requestid=20241228211540577068590657&token=31850C%7CMIXED",
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=8413633746&itemId=24328803831&vendorItemId=91348449290&traceid=V0-153-ebb8b501becef6e1&clickBeacon=742e9650-c515-11ef-bc06-55b102d8ff05%7E3&requestid=20241228211540577068590657&token=31850C%7CMIXED",
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=7744278977&itemId=20843401087&vendorItemId=87911033319&traceid=V0-153-590d7a519d153390&requestid=20241228211540577068590657&token=31850C%7CMIXED",
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=7703317571&itemId=20631007009&vendorItemId=87915310585&traceid=V0-153-3dca233e0f9566a1&requestid=20241228211540577068590657&token=31850C%7CMIXED",
            "https://link.coupang.com/re/AFFSDP?lptag=AF0616554&pageKey=8405058241&itemId=24298504172&vendorItemId=91316580125&traceid=V0-153-007cb03ffaf275a2&clickBeacon=742e9650-c515-11ef-b28c-acb2c14040c0%7E3&requestid=20241228211540577068590657&token=31850C%7CMIXED",
        ],
    )
    # write blog post with multiple elements
    c.download_images()
