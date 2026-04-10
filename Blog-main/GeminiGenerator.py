from TagGenerator import TagGenerator
import google.generativeai as genai
import json

class GeminiTagGenerator(TagGenerator):
    # API key 정보
    api_key = 'AIzaSyDGxhUUAwg74F_LhnEOUU5o8mCcevBm7sE'

    item = ''
    items = []

    def __init__(self, item, items):
        super().__init__(item, items)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        genai.configure(api_key=self.api_key)
    
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
        response = self.model.generate_content(prompt)
        tags = response.text
        print(tags)
        return tags


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
    ai = GeminiTagGenerator(item, items)
    # ai.test()
    # ai.generate_tag()
    ai.generate_tag(overwrite=True)
    
    # write blog post with multiple elements
    # ai.write_blog_post()
