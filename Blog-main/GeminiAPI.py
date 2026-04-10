import requests
import google.generativeai as genai

class GeminiAPI:
    api_key = 'AIzaSyDGxhUUAwg74F_LhnEOUU5o8mCcevBm7sE'
    # headers = {
    #     "Content-Type": "application/json",
    # }
    # url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        genai.configure(api_key=self.api_key)
        # url = url + '?key=' + self.api_key

    def generate_response(self, message):
        response = self.model.generate_content(message)
        # payload = {
        #     "model": "llama-3.1-sonar-large-128k-online",
        #     "messages": messages,
        #     "return_images": False,
        #     "return_related_questions": False,
        #     "search_recency_filter": "",
        #     "search_domain_filter": [],
        # }
        # response = requests.request(
        #     "POST", self.url, json=payload, headers=self.headers
        # )
        import json
        tags = json.load(response.candidates[0]['content']['parts'][0])['text']
        print(tags)
        return tags


if __name__ == "__main__":
    item = '습식 청소기'
    items = [
"비쎌 다용도 습식청소기 스팟클린 프로히트 3698V",
"[클렌하임 KLENHEIM 이너청소기] 패브릭 청소기 가정용 습식 패브릭 소파 매트리스 카페트 청소",
"엔플로 침구 습식 청소기 패브릭 소파 카페트 쇼파 침대 호환, 단일색상",
"포쉬 워시젯 유선습식청소기 카페트러그청소기, 워시젯 All-in One Package(포뮬라 증정)",
"비쎌 스팟클린 하이드로스팀 청소기 3791S",
    ]
    
    items_text = '\n'.join(items)
    prompt = f"""제목 : {item}

    제품목록 :
    {items_text}

    위 내용에 대한 블로그 글을 작성하고 태그를 추가하려고 해. 30개의 적절한 태그를 나열해줘
    태그는 띄어쓰기가 없어야 하고, 각 제품 이름도 각각의 태그로 추가되면 좋아.
    출력에는 30개의 태그만 나열해줘.
    출력 예시)
    #습식청소기 #비쎌습식청소기 #비쎌스팟클린프로히트 #3698V
    """
    api = GeminiAPI()
    response = api.generate_response(prompt)
    print(response)
    # messages = [
    #     {
    #         "role": "system",
    #         "content": "너는 제품에 대한 리뷰를 작성하는 리뷰 블로거야. 제품 이름이 주어지면 이를 인터넷에서 검색하고 제품에 대한 설명을 10문장으로 작성해야해. 글은 해요체의 친근한 어투로 작성하되, 이모티콘을 2~3문장 당 한번씩 문장마침부호 대신에 사용하고, 말 끝은 '~라고 하네요', '~에요', '~ 것 같네요', '~해보여요' 와 같은 표현을 자주 사용하고, !,?,~,ㅎㅎ 와 같은 부호도 적절히 사용하도록 해. 글은 10문장으로 이루어진 글로 작성하고, 각 문장은 '\n'로, 문단이 바뀔때는 '\n\n'를 이용해서 문장을 나누도록 해. 그리고 한자 용어가 사용되지 않도록 주의해.",
    #     },
    #     {"content": "홈플래닛 초음파 가습기 4L, H1001D11", "role": "user"},
    #     {
    #         "content": "홈플래닛 초음파 가습기 4L는 먼저 넉넉한 용량이 특징이에요.\n소형 가습기 치고는 꽤 용량이 커서 비교적 장시간 가습이 가능해요 🕒\n\n간편한 상부 급수 방식으로 물 보충이 편리하며, 투명한 수위창으로 물의 양을 쉽게 확인할 수 있어요 👀\n3단계 분무량 조절 기능으로 원하는 습도를 조절할 수 있으며, 저소음 설계로 수면 중에도 방해 없이 사용할 수 있답니다 😴\n\n또한, 자동 전원 차단 기능이 있어 물이 부족할 때 안전하게 전원이 꺼져요 🔌\n정신없이 살다보면 물이 떨어지는지도 모를때가 많은데 걱정이 없겠어요!\n\n심플한 디자인으로 어느 공간에나 잘 어울리며, 분리형 물탱크로 세척이 용이해 위생적으로 관리할 수 있어요 🧼\n가성비 좋은 가격으로 많은 사랑을 받고 있는 제품이라고 하네요! 💖",
    #         "role": "assistant",
    #     },
    #     {"content": "이플린 미니트리 풀세트 + 크리스마스 선물상자", "role": "user"},
    #     {
    #         "content": "이플린 미니트리 풀세트는 60cm의 아담한 트리로, 큰 공간 차지가 부담스러운 상황에서 사용하기 좋은 제품이에요.\n공간을 많이 차지하지 않아 어디에나 쉽게 배치할 수 있어요 🏠\nLED 조명과 다양한 오너먼트가 포함되어 있어, 별도의 추가 구매 없이도 완벽한 크리스마스 분위기를 연출할 수 있을 것 같아요 ✨\n\n또 선물상자가 함께 제공되기 때문에, 소중한 분께 특별한 선물로도 제격이에요! 🎁\n설치와 해체가 간편하여, 누구나 손쉽게 꾸밀 수 있고, 내구성이 뛰어난 소재로 제작되어 매년 재사용이 가능해 경제적이라고 해요 💰\n\n다양한 색상과 디자인의 오너먼트로 나만의 개성 있는 트리를 꾸밀 수 있으며, 안전한 LED 전구로 발열이 적어 안심하고 사용할 수 있다네요 🔋\n책상이나 테이블에 간단하지만 분위기를 살릴 수 있는 킥 아이템으로 어떠신가요?",
    #         "role": "assistant",
    #     },
    #     {"content": "스키피 수퍼크런치 땅콩버터, 1.13kg, 1개", "role": "user"},
    # ]

    # gemini_api = GeminiAPI()
    # response = gemini_api.generate_response(messages)
    # print(response)
    # # 스키피 수퍼크런치 땅콩버터 1.13kg는 정말 풍부한 맛과 식감을 자랑하는 제품이에요.\n땅콩의 고소함이 가득하고, 바삭한 크런치한 식감이 매력적이랍니다 🥜\n\n대용량 1.13kg으로 가족이나 친구들과 함께 나누기 좋은 사이즈라고 해요!\n아침 식사로 토스트에 발라 먹거나, 간식으로 과일과 함께 즐기면 완벽하답니다 🍞\n\n이 제품은 인공 첨가물이 없어서 건강하게 즐길 수 있어요.\n또한, 단백질이 풍부해 운동 후 간식으로도 안성맞춤이에요 💪\n\n스키피 땅콩버터는 다양한 요리에 활용할 수 있어 요리하는 재미도 느낄 수 있답니다.\n크래커에 발라서 간단한 스낵으로 즐기거나, 스무디에 넣어도 맛있어요! 🍹\n\n가격도 합리적이라 많은 사람들이 찾는 인기 제품이라고 하네요.\n고소하고 바삭한 땅콩버터를 찾고 계신다면 이 제품을 추천해드려요!
