from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pyperclip
import time
import json
import os

import random
import time
from selenium.webdriver.common.action_chains import ActionChains
        
import win32clipboard
from PIL import Image
import io

import pyautogui
            
import requests

import gdshortener

class NaverBlogWriter():
    # 네이버 로그인 정보
    naver_id = 'shaneangel'
    naver_pw = 'qkrdydwns1!'

    driver = None
    elements = None
    post_title = None
    thumbnail_path = ''
    
    def __init__(self, item, root_dir, path, thumbnail_path=''):
        self.root_dir = root_dir
        import os
        os.makedirs(root_dir, exist_ok=True)
        
        self.path = path
        self.thumbnail_path = thumbnail_path
        self.post_title = f"[오늘의아이템] 요즘 핫한 {item} 추천"

    # destroyer
    def __del__(self):
        if self.driver is not None:
            self.driver.quit()
    
    def _init(self):

        # read elements from json file
        with open(self.path, "r", encoding="utf-8") as f:
            elements = json.load(f)["elements"]

        # 크롬 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("lang=ko_KR")
        chrome_options.add_argument('no-sandbox')
        chrome_options.add_argument('disable-gpu')
        chrome_options.add_argument("disable-dev-shm-usage")
        chrome_options.add_argument("--disable-3d-apis")
        chrome_options.add_argument("user-data-dir=C:/Utilities/Blog/chrome-user-data")

        # 웹드라이버 실행
        driver = webdriver.Chrome(service=Service(), options=chrome_options)        
        return driver, elements


    # 네이버 로그인 함수
    def _naver_login(self):
        
        self.driver.get('https://nid.naver.com/nidlogin.login?mode=form&url=https://blog.naver.com/')
        
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "id"))).click()
        
        # 클립보드를 이용한 아이디 입력
        pyperclip.copy(self.naver_id)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(1)
        
        # 클립보드를 이용한 비밀번호 입력
        self.driver.find_element(By.ID, "pw").click()
        pyperclip.copy(self.naver_pw)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(1)
        
        # 로그인 버튼 클릭
        self.driver.find_element(By.ID, "log.login").click()
        
        # 로그인 성공 여부 확인
        try:
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "button_signout")))
            print('로그인 성공')
        except:
            print('로그인 실패')
            self.driver.quit()

    # 랜덤 딜레이 함수
    def _random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

    # 휴먼 액션: 마우스 이동
    def _human_mouse_movement(self, element):
        action = ActionChains(self.driver)
        action.move_to_element(element).perform()
        self._random_delay(0.5, 1.5)

    # 휴먼 액션: 페이지 스크롤
    def _human_scroll(self, direction="down"):
        if direction == "down":
            self.driver.execute_script("window.scrollBy(0, 300);")
        elif direction == "up":
            self.driver.execute_script("window.scrollBy(0, -300);")
        self._random_delay(1, 2)

    def _copy_image_to_clipboard(self, image_path):
        """
        주어진 이미지 파일을 클립보드에 복사하는 함수.
        
        :param image_path: 복사할 이미지 파일의 경로
        """
        # 이미지 열기
        image = Image.open(image_path)

        # 이미지를 RGB로 변환 (Pillow 기본은 RGBA일 수 있으므로)
        image = image.convert('RGB')

        # 이미지 데이터를 BytesIO로 저장
        output = io.BytesIO()
        image.save(output, format='BMP')  # 클립보드에는 BMP 포맷으로 저장해야 함
        data = output.getvalue()[14:]  # BMP 헤더 제거 (Clipboard BMP는 헤더 없이 복사)
        output.close()

        # 클립보드에 이미지 복사
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    # 블로그 글쓰기 함수
    def write_blog_post(self):
        blog_url_file_path = f"{self.root_dir}/90-blog-url.txt"
        if os.path.isfile(blog_url_file_path):
            print('File exists, skipping process.')
            return blog_url_file_path
        
        self.driver, self.elements = self._init()
        self._naver_login()
        self.driver.get('https://blog.naver.com/GoBlogWrite.naver')
        self.driver.switch_to.frame('mainFrame')
        self._random_delay(2, 3)
        
        try:
            WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "se-popup-button-cancel"))).click()        
        except:
            pass

        # 제목 입력
        title_input = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"제목")]')))
        self._human_mouse_movement(title_input)
        title_input.click()
        self._random_delay(0.1, 0.2)
        ActionChains(self.driver).send_keys(self.post_title).perform()
        self._random_delay(0.2, 0.4)
        
        # 썸네일 삽입
        if self.thumbnail_path != '':
            self.driver.find_element(By.CLASS_NAME, "se-cover-button-local-image-upload").click()
            
            pyperclip.copy(self.thumbnail_path.replace('/', '\\'))
            self._random_delay(2, 2.5)
            pyautogui.hotkey('ctrl', 'v')
            self._random_delay(2, 2.5)
            pyautogui.press('enter')    
            self._random_delay(2, 2.5)    
        
        # 텍스트 삽입
        text_area = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"본문에")]')))
        self._human_mouse_movement(text_area)
        text_area.click()
        
        # 본문에 요소 삽입
        for element in self.elements:
            element_type = list(element.keys())[0]
            content = list(element.values())[0]
            self._human_scroll("down")  # 스크롤 다운
            
            if element_type == 'image':
                # copy image file to clipboard in path 'C:\Users\LSH-DeskTop\Downloads\test.png'
                self._copy_image_to_clipboard(content)
                
                # 이미지 삽입 with Ctrl + v
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                self._random_delay(3, 4)  # 이미지 업로드 대기
                
            elif element_type == 'images':
                print('사진 모음 추가')
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-image-toolbar-button'))).click()
                self._random_delay(0.1, 0.3)
                pyperclip.copy(' '.join(content['paths']).replace('/', '\\'))
                pyautogui.sleep(2)
                pyautogui.hotkey('ctrl', 'v')
                pyautogui.sleep(2)
                pyautogui.press('enter')
                # WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, 'image-type-collage'))).click()
                try:
                    WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '//label[contains(text(),"콜라주")]'))).click()
                    self._random_delay(2, 3)  # 업로드 대기
                except:
                    pass

            elif element_type == 'text':         
                # 글씨크기
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-font-size-code-toolbar-button'))).click()
                self._random_delay(0.5, 1)          
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-toolbar-option-font-size-code-fs15-button'))).click()
                self._random_delay(0.5, 1)      
                content = content.replace('\\n', '\n')
                # ActionChains(self.driver).send_keys(content).perform()
                
                for char in content:  # 한 글자씩 입력
                    if char == '`':
                        # Ctrl + B
                        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL).perform()
                        # Ctrl + B + U
                        # ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('b').send_keys('u').key_up(Keys.CONTROL).perform()
                    else:
                        ActionChains(self.driver).send_keys(char).perform()
                self._random_delay(0.1, 0.2)

            elif element_type == 'header':
                print(content)
                ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys('q').key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
                self._random_delay(0.1, 0.3)
                ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys('q').key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
                self._random_delay(0.1, 0.3)
                ActionChains(self.driver).send_keys(content).perform()
                # for char in content:  # 한 글자씩 입력
                #     ActionChains(self.driver).send_keys(char).perform()
                #     random_delay(0.1, 0.3)
                self._random_delay(0.1, 0.2)
                
            elif element_type == 'video':
                print('비디오 추가')
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-video-toolbar-button'))).click()
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'nvu_local'))).click()
                self._random_delay(0.1, 0.3)
                pyperclip.copy(content['path'].replace('/', '\\'))
                pyautogui.sleep(2)
                pyautogui.hotkey('ctrl', 'v')
                pyautogui.sleep(2)
                pyautogui.press('enter')
                self._random_delay(3, 4)  # 비디오 업로드 대기
                
                # wait for 업로드 완료
                WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, '//em[contains(text(),"업로드 완료")]')))
                print('업로드 완료')
                self._random_delay(0.1, 0.3)
                
                # 제목
                input_box = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, 'nvu_inp_box_title')))
                input_box.send_keys(self.post_title)
                self._random_delay(0.1, 0.3)
                
                # 태그 추가
                tag_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, 'nvu_inp_box_tag')))
                self._human_mouse_movement(tag_button)
                tag_button.click()
                input_box = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'nvu_tag_inp')))
                input_box.send_keys(content['tags'])
                self._random_delay(0.1, 0.3)
                
                # 완료
                done_button = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.CLASS_NAME,'nvu_btn_submit')))
                self._human_mouse_movement(done_button)
                done_button.click()
                self._random_delay(1, 2)
                

            elif element_type == 'url_text':                
                # 빈칸
                ActionChains(self.driver).send_keys(Keys.ENTER).send_keys(Keys.ENTER).send_keys(Keys.ARROW_UP).send_keys(Keys.ARROW_UP).perform()
                self._random_delay(0.5, 1)
                
                # 굵게/밑줄
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("B").key_up(Keys.CONTROL).perform()
                self._random_delay(0.5, 1)                
                
                # 글씨크기
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-font-size-code-toolbar-button'))).click()
                self._random_delay(0.5, 1)          
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-toolbar-option-font-size-code-fs38-button'))).click()
                self._random_delay(0.5, 1)          
                      
                # 글씨색
                # WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-font-color-toolbar-button'))).click()
                # self._random_delay(0.5, 1)          
                # WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-is-selected'))).click()
                # self._random_delay(0.5, 1)          
                      
                # 배경색
                # WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-background-color-toolbar-button'))).click()
                # self._random_delay(0.5, 1)          
                # WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-is-selected'))).click()
                # self._random_delay(0.5, 1)                
                
                # 문구 입력
                ActionChains(self.driver).send_keys(" 최저가 구매하러 가기 ").perform()
                self._random_delay(0.5, 1)           
                
                # 링크      
                ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.HOME).key_up(Keys.SHIFT).perform()
                self._random_delay(0.5, 1) 
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-link-toolbar-button'))).click()
                self._random_delay(0.5, 1) 
                WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-custom-layer-link-input'))).click()
                self._random_delay(0.5, 1)      
                short_url = self._shorten_url(content)       
                ActionChains(self.driver).send_keys(short_url).send_keys(Keys.ENTER).perform()    
                
                # 다음줄로
                ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).perform()
                self._random_delay(0.5, 1)                
                
            elif element_type == 'url':
                # 링크 삽입
                link_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-oglink-toolbar-button')))
                self._human_mouse_movement(link_button)
                link_button.click()
                self._random_delay(1, 2)                
                
                # "링크 정보를 불러오는 데 실패했습니다. 링크를 다시 확인해주세요." 오류
                short_url = self._shorten_url(content)
                try:
                    ActionChains(self.driver).send_keys(short_url + '\n').perform()
                    self._random_delay(0.3, 0.5)      
                    done_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'se-popup-button-confirm')))
                    self._human_mouse_movement(done_button)
                    done_button.click()
                    self._random_delay(1, 2)
                except:
                    try:
                        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                        ActionChains(self.driver).send_keys(short_url.split("//")[1] + '\n').perform()
                        self._random_delay(0.3, 0.5)      
                        done_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'se-popup-button-confirm')))              
                        self._human_mouse_movement(done_button)
                        done_button.click()
                        self._random_delay(1, 2)  
                    except:
                        try:
                            short_url2 = self._shorten_url(content, short_url)
                            print(short_url2)
                            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                            ActionChains(self.driver).send_keys(short_url2 + '\n').perform()
                            self._random_delay(0.3, 0.5)      
                            done_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'se-popup-button-confirm')))
                            self._human_mouse_movement(done_button)
                            done_button.click()
                            self._random_delay(1, 2)
                        except:
                            try:
                                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                                ActionChains(self.driver).send_keys(short_url2.split("//")[1] + '\n').perform()
                                self._random_delay(0.3, 0.5)      
                                done_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'se-popup-button-confirm')))              
                                self._human_mouse_movement(done_button)
                                done_button.click()
                                self._random_delay(1, 2)  
                            except:
                                # ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                                # ActionChains(self.driver).send_keys(self._shorten_url("https://link.coupang.com/a/b15OBt") + '\n').perform()      
                                # try:
                                #     done_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'se-popup-button-confirm')))              
                                #     self._human_mouse_movement(done_button)
                                #     done_button.click()
                                #     self._random_delay(1, 2)   
                                # except:
                                # 닫기
                                done_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-popup-close-button')))
                                self._human_mouse_movement(done_button)
                                done_button.click()
                                self._random_delay(1, 2)
                                ActionChains(self.driver).send_keys(short_url + '\n').perform()
                                self._random_delay(3, 4)
                                print("Shortened URL register failed...")
                            
                    # done_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'se-popup-close-button')))
                    # human_mouse_movement(self.driver, done_button)
                    # done_button.click()

            ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys('h').key_up(Keys.CONTROL).key_up(Keys.ALT).perform()
            self._random_delay(0.1, 0.3)
            
        # input('Press any key to continue...')
        
        # 발행 버튼 클릭
        publish_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div/div[3]/div[2]/button')))
        self._human_mouse_movement(publish_button)
        publish_button.click()
        self._random_delay(2, 3)
        
        sympathy_checkbox = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '//label[contains(text(),"공감허용")]')))
        self._human_mouse_movement(sympathy_checkbox)
        sympathy_checkbox.click()
        self._random_delay(1, 1.5)
        
        confirm_button = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div/div[3]/div[2]/div/div/div/div[8]/div/button')))
        self._human_mouse_movement(confirm_button)
        confirm_button.click()
        self._random_delay(1, 1.5)
        
        # 발행 성공 여부 확인
        print('게시물 작성 성공')
        blog_url = self.driver.current_url
        print(blog_url)
        self._random_delay(3, 3.5)
        # write url after redirection
        with open(blog_url_file_path, 'w', encoding='utf-8') as f:
            f.write(blog_url)
        return blog_url_file_path
        # if title in self.driver.title:
        #     print('게시물 작성 성공')
        # else:
        #     print('게시물 작성 실패')

    def _shorten_url(self, long_url, short_url=None):
        """
        IS.GD API를 사용해 주어진 URL을 단축합니다.
        
        :param long_url: 단축하려는 원본 URL
        :return: 단축된 URL
        """
        # api_endpoint = "https://is.gd/create.php"
        # params = {
        #     "format": "json",  # 응답 형식: JSON
        #     "url": long_url,   # 단축할 URL
        # }
        
        # try:
        #     response = requests.get(api_endpoint, params=params)
        #     response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        #     data = response.json()
        #     if "shorturl" in data:
        #         return data["shorturl"]
        #     else:
        #         raise ValueError(f"URL 단축 실패: {data}")
        # except requests.exceptions.RequestException as e:
        #     raise RuntimeError(f"API 요청 중 오류 발생: {e}")

        if 'is.gd' in long_url:
            return long_url  # is.gd URL은 단축할 필요가 없음

        s = gdshortener.ISGDShortener()
        if short_url is None:
            try:
                result = s.shorten(url=long_url)[0]
            except Exception as e:
                print(f"Shorten failed... {str(e)}")
                result = long_url
        else:
            custom = short_url.rsplit('/', 1)[1]
            custom = custom[:-2]+str(random.randint(10, 99))
            result = s.shorten(url=long_url, custom_url=custom)[0]
        return result
    
# # 실행 예제
# if __name__ == "__main__":
#     original_url = "https://link.coupang.com/a/b1NBYX"
#     try:
#         short_url = shorten_url(original_url)
#         print(f"단축된 URL: {short_url}")
#     except Exception as e:
#         print(f"오류: {e}")

# 실행 예제
if __name__ == "__main__":
    path = "./test.json"
    naverBlogWriter = NaverBlogWriter(path)
    # write blog post with multiple elements
    naverBlogWriter.write_blog_post()