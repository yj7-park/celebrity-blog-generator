import requests
import os
import re

class PerplexityNameGenerator:
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
    }
    url = "https://api.perplexity.ai/chat/completions"

    def __init__(self, item, root_dir, pre_names):            
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)
        self.item = item        
        self.names = pre_names
        
    def generate_names(self):
        # check if file exists
        name_file_path = f"{self.root_dir}/01-product_names.txt"
        if os.path.isfile(name_file_path):
            print('File exists, skipping process.')
            return name_file_path
        with open(name_file_path, 'w', encoding='utf-8') as f:
            for name in self.names:
                p, b, m = self.generate_response(name)
                print(f"{name}:\n  {p} | {b} | {m}")
                f.write(f"{p}, {b}")
                if m == 'NA':
                    f.write('\n')
                else:
                    f.write(f" ({m})\n")
        return name_file_path            

    def generate_response(self, name):
        messages = [
            {
                "role": "system",
                "content": "주어진 문구로부터 검색을 통해 제품명, 브랜드명, 모델명을 각각 도출해줘. 도출할 수 없으면 NA로 작성하도록 해. 제품명은 부가 설명이나 문구들을 최소화하고 제품을 구분할 수 있는 제품의 이름으로 작성하도록 해. 반복되는 표현이나 중복되는 표현등은 최소화하여 한가지로만 표현하도록 해. 색상 옵션은 제거하도록 해. 제품명과 브랜드명, 모델명을 작성하는 과정을 설명하고 마지막 출력은 '!!!{{제품명}}!!! @@@{{브랜드명}}@@@ ###{{모델명}}###' 으로만 출력하도록 해. {{Question}} 홈플래닛 초음파 가습기 4L, H1001D11 {{Answer}} 홈플래닛 초음파 가습기 4L, 홈플래닛, H1001D11",
            },
            {
                "role": "user",
                "content": "홈플래닛 초음파 가습기 4L, H1001D11",
            },
            {
                "role": "assistant",
                "content": "!!!홈플래닛 초음파 가습기 4L!!! @@@홈플래닛@@@ ###H1001D11###",
            },
            {
                "role": "user",
                "content": "LG전자 스마트 인버터 전자레인지 터치식 23L 방문설치",
            },
            {
                "role": "assistant",
                "content": "!!!LG전자 스마트 인버터 전자레인지 23L!!! @@@LG전자@@@ ###MW23BD###",
            },
            {
                "role": "user",
                "content": "헤지스 퍼피로고 블랙 카드홀더",
            },
            {
                "role": "assistant",
                "content": "!!!해지스 퍼피로고 블랙 카드홀더!!! @@@해지스@@@ ###NA###",
            },
            {
                "role": "user",
                "content": "FONOW 어그부츠 겨울 여성 따뜻한 미니 털부츠 방한화 스노우 부츠",
            },
            {
                "role": "assistant",
                "content": "어그부츠, 겨울 여성 따뜻한 미니 털부츠, 방한화, 스노우 부츠는 비슷한 표현이 반복되므로 제품명에는 어그부츠만 사용하곘습니다. !!!FONOW 어그부츠!!! @@@FONOW@@@ ###NA###",
            },
            {
                "role": "user",
                "content": name,
            },
        ]

        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": messages,
            "return_images": False,
            "return_related_questions": False,
            "search_recency_filter": "",
            "search_domain_filter": [],
        }
        response = requests.request(
            "POST", self.url, json=payload, headers=self.headers
        )
        r = response.json()["choices"][0]["message"]["content"].replace("\n", " ")
        res = re.findall(r'!!!(.+?)!!!', r)
        product_name = res[-1] if len(res) > 0 else name
        res = re.findall(r'@@@(.+?)@@@', r)
        brand_name = res[-1] if len(res) > 0 else "NA"
        res = re.findall(r'###(.+?)###', r)
        model_name = res[-1] if len(res) > 0 else "NA"
        return product_name, brand_name, model_name

if __name__ == "__main__":
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
    

    p = PerplexityNameGenerator()
    response = p.generate_response(messages)
    print(response)
    # 스키피 수퍼크런치 땅콩버터 1.13kg는 정말 풍부한 맛과 식감을 자랑하는 제품이에요.\n땅콩의 고소함이 가득하고, 바삭한 크런치한 식감이 매력적이랍니다 🥜\n\n대용량 1.13kg으로 가족이나 친구들과 함께 나누기 좋은 사이즈라고 해요!\n아침 식사로 토스트에 발라 먹거나, 간식으로 과일과 함께 즐기면 완벽하답니다 🍞\n\n이 제품은 인공 첨가물이 없어서 건강하게 즐길 수 있어요.\n또한, 단백질이 풍부해 운동 후 간식으로도 안성맞춤이에요 💪\n\n스키피 땅콩버터는 다양한 요리에 활용할 수 있어 요리하는 재미도 느낄 수 있답니다.\n크래커에 발라서 간단한 스낵으로 즐기거나, 스무디에 넣어도 맛있어요! 🍹\n\n가격도 합리적이라 많은 사람들이 찾는 인기 제품이라고 하네요.\n고소하고 바삭한 땅콩버터를 찾고 계신다면 이 제품을 추천해드려요!
