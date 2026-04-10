from TagGenerator import TagGenerator


class PerplexityTagGenerator(TagGenerator):
    url = "https://www.perplexity.ai/search/jemog-seubsig-ceongsogi-jepumm-lh4s8BFEQGCCtCn06l8YzA"

    # 로그인 정보
    # driver = None
    item = ''
    items = []

    def __init__(self, item, items):
        super().__init__(item, items)

    def _generate_tag(self):
        items_text = '\n'.join(self.items)
        prompt = f"""제목 : {self.item}

제품목록 :
{items_text}

위 내용에 대한 블로그 글을 작성하고 태그를 추가하려고 해. 30개의 적절한 태그를 나열해줘
태그는 띄어쓰기가 없어야 하고, 각 제품 이름이나 모델명, 브랜드 이름을 먼저 태그로 추가해줘.
출력에는 30개의 태그만 나열해줘.
출력 예시) 
#3698V #비쎌습식청소기 #비쎌스팟클린프로히트 #습식청소기 
"""
        from PerplexityAPI import PerplexityAPI 
        api = PerplexityAPI()
        messages = [{"role":"user","content":prompt}]
        return api.generate_response(messages)
        


# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.common.keys import Keys

# import subprocess

# import pyperclip
# import time
# import os
    # # destroyer
    # def __del__(self):
    #     if self.driver is not None:
    #         self.driver.close()
    #         self.driver.quit()

    # def _init(self):
    #     subprocess.Popen(
    #         r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9225"'
    #     )
    #     # 크롬 옵션 설정
    #     chrome_options = Options()
    #     chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9225")
    #     # 웹드라이버 실행
    #     driver = webdriver.Chrome(service=Service(), options=chrome_options)
    #     return driver  # , elements

    # def _login(self):
    #     self.driver.get(self.url)
    
#     def _generate_tag(self):
#         if self.driver == None:
#             self.driver = self._init()
#             self._login()
#         edit = (
#             WebDriverWait(self.driver, 10)
#             .until(
#                 EC.presence_of_element_located(
#                     (By.XPATH, "//div[contains(text(), '쿼리 편집')]")
#                 )
#             )
#             .find_element(By.XPATH, "./../..")
#         )
        
#         # TODO: system command
#         items_text = '\n'.join(self.items)
#         prompt = f"""제목 : {self.item}

# 제품목록 :
# {items_text}

# 위 내용에 대한 블로그 글을 작성하고 태그를 추가하려고 해. 30개의 적절한 태그를 나열해줘
# 태그는 띄어쓰기가 없어야 하고, 각 제품 이름도 각각의 태그로 추가되면 좋아.
# 출력에는 30개의 태그만 나열해줘.
# 출력 예시)
# #습식청소기 #비쎌습식청소기 #비쎌스팟클린프로히트 #3698V
# """
#         pyperclip.copy(prompt)
#         ActionChains(self.driver).move_to_element(edit).click().key_down(
#             Keys.CONTROL
#         ).send_keys("a").send_keys("v").key_up(Keys.CONTROL).send_keys(
#             Keys.ENTER
#         ).perform()
        
#         time.sleep(2)
        
#         WebDriverWait(self.driver, 30).until(
#             EC.presence_of_element_located(
#                 (By.XPATH, "//div[contains(text(), '다시 쓰기')]")
#             )
#         )
#         time.sleep(2)
        
#         text_elements = self.driver.find_elements(By.XPATH, "//div[@class='mb-md' and not(@class='flex') and not(@class='relative')]/div/div/div/div/span")
#         text = ''
#         for text_element in text_elements:
#             text_line = text_element.text.replace('\n', '')
#             if len(text_line) > 2:
#                 text += text_line
#         print(text)
#         return text

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
    item = '습식 청소기'
    items = [
"비쎌 다용도 습식청소기 스팟클린 프로히트 3698V",
"[클렌하임 KLENHEIM 이너청소기] 패브릭 청소기 가정용 습식 패브릭 소파 매트리스 카페트 청소",
"엔플로 침구 습식 청소기 패브릭 소파 카페트 쇼파 침대 호환, 단일색상",
"포쉬 워시젯 유선습식청소기 카페트러그청소기, 워시젯 All-in One Package(포뮬라 증정)",
"비쎌 스팟클린 하이드로스팀 청소기 3791S",
    ]
    ai = PerplexityTagGenerator(item, items)
    # ai.test()
    # ai.generate_tag()
    ai.generate_tag(overwrite=True)
    
    # write blog post with multiple elements
    # ai.write_blog_post()
