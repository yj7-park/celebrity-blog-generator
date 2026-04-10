import requests

import os
import re

class PerplexityProductSelector:
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
    }
    url = "https://api.perplexity.ai/chat/completions"

    def __init__(self, item, root_dir, names, prices, reviews):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)
            
        self.item = item        
        self.names = names
        self.prices = prices
        self.reviews = reviews

    def select_product(self):   
        select_file_name = f'{self.root_dir}/041-product_selection.txt'
        if os.path.isfile(select_file_name):
            print("File exists, skipping process.")
            return select_file_name
        list_string = ''
        for i, name, price, review in zip(range(1, len(self.names)+1), self.names, self.prices, self.reviews):
            list_string += f"{i} | {name} | {price} | {review}\n"
        print(list_string)
        messages = [
            {
                "role": "system",
                "content": """
{{제품 목록}}에 포함된 각 제품에 대한 정보를 인터넷 검색을 통해 확인한 후 (반드시 제품 목록에 포함된 제품만 사용), 주어진 평가 기준에 따라 최종 제품 후보를 3개 선별하도록 해. 제품 평가 기준은 아래와 같아.

--아래--
1. {{제품 카테고리}}의 제품이어야 함
2. 리뷰 수가 높은 제품이어야 함 (최소 200개 이상)
3. 브랜드명, 모델명이 명확한 제품이어야 함
4. 최종 제품 후보들은 가격이 비슷하여야 함 (상대적으로 가격이 너무 낮은 제품만 제외, 높은 제품은 상관없음)
5. 중복된 제품으로 판단될 경우, 하나만 선별하여야 함
6. 최대한 다양한 브랜드의 제품을 선별하여야 함 (중복된 브랜드는 최대한 제외 - 3개 미만일 경우 제외하지 않음)

각 평가 기준에 의거하여 모든 후보 제품에 대해 선별과정과 선별근거, 선별되지 않은 이유를 상세히 작성하며, 최종 제품 후보를 아래와 같은 포맷으로 작성하도록 해.
{{최종 제품 후보}}
@@@{{NO}}@@@ {{A제품명}}
@@@{{NO}}@@@ {{A제품명}}
@@@{{NO}}@@@ {{A제품명}}
...
와같은 포맷으로 출력하도록 해.
""",
            },
            {
                "role": "user",
                "content": """
{{제품 카테고리}}
전자레인지

{{제품 목록}}
NO | 제품명, 브랜드명 (모델명) | 가격 | 리뷰수
1 | 무회전 스텐 전자레인지 25리터, NA | 196900 | 327
2 | 쿠쿠 전자레인지 20L, 쿠쿠 (CMW-A201DW) | 58800 | 29941
3 | 삼성전자 세라믹 전자레인지 23L, 삼성전자 (MS23C3513AW) | 113770 | 4742
4 | 미디어 광파오븐 에어프라이어 23L, 미디어 (MTO2300BL) | 134900 | 310
5 | LG전자 스마트 인버터 전자레인지 23L, LG전자 (MW23BD) | 122590 | 3088
6 | 윌즈 전자레인지 터치식 20L, 윌즈 (P70J20AP-VB) | 62900 | 765
7 | 홈플래닛 전자레인지 다이얼식 20L, 홈플래닛 (MWO-M1) | 50290 | 22157
8 | 매직쉐프 무회전 전자레인지 25L, 매직쉐프 (MMW-WC25TES) | 198000 | 16
9 | 쿠쿠 전자레인지 다이얼식 20L, 쿠쿠 (CMW-A201DB) | 60330 | 29941
10 | 쿠잉전자 프리즘 플랫 전자레인지 20L, 쿠잉전자 (MC-P20PF) | 109000 | 491
""",
            },
            {
                "role": "assistant",
                "content": """
평가 기준에 따라 선별된 전자레인지 제품 후보입니다.

### 평가 기준 설명
- **제품 카테고리**: 전자레인지여야 함
- **리뷰 수**: 높은 리뷰 수를 가진 제품을 우선함
- **브랜드명, 모델명**: 명확한 브랜드명과 모델명이 있어야 함
- **가격**: 가격이 비슷하거나, 너무 낮지 않은 제품을 우선함
- **중복**: 중복된 제품은 하나만 선발함
- **다양성**: 다양한 브랜드의 제품을 선별함

### 선별 과정과 선별근거

1. **무회전 스텐 전자레인지 25리터, NA**
   - 제외
   - 리뷰 수: 327개, 비교적 낮은 리뷰 수
   - 가격: 196,900원, 높은 가격
   - 브랜드명, 모델명: 불명확 (제외)

2. **쿠쿠 전자레인지 20L, 쿠쿠 (CMW-A201DW)**
   - 선별
   - 리뷰 수: 29,941개, 매우 높은 리뷰 수
   - 가격: 58,800원, 적절한 가격대
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 매우 높은 리뷰 수와 명확한 브랜드명, 모델명으로 선별

3. **삼성전자 세라믹 전자레인지 23L, 삼성전자 (MS23C3513AW)**
   - 선별
   - 리뷰 수: 4,742개, 높은 리뷰 수
   - 가격: 113,770원, 비교적 높은 가격但 합리적
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 높은 리뷰 수와 명확한 브랜드명, 모델명으로 선별

4. **미디어 광파오븐 에어프라이어 23L, 미디어 (MTO2300BL)**
   - 제외
   - 리뷰 수: 310개, 비교적 낮은 리뷰 수
   - 가격: 134,900원, 높은 가격
   - 브랜드명, 모델명: 명확하지만 제품 카테고리가 전자레인지가 아닌 광파오븐 에어프라이어로 판단 (제외)

5. **LG전자 스마트 인버터 전자레인지 터치식 23L, LG전자 (MW23BD)**
   - 선별
   - 리뷰 수: 3,088개, 높은 리뷰 수
   - 가격: 122,590원, 비교적 높은 가격但 합리적
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 높은 리뷰 수와 명확한 브랜드명, 모델명으로 선별

6. **윌즈 전자레인지 터치식 20L, 윌즈 (P70J20AP-VB)**
   - 제외
   - 리뷰 수: 765개, 비교적 낮은 리뷰 수
   - 가격: 62,900원, 적절한 가격대但 리뷰 수가 낮음

7. **홈플래닛 전자레인지 다이얼식 20L, 홈플래닛 (MWO-M1)**
   - 제외
   - 리뷰 수: 22,157개, 높은 리뷰 수
   - 가격: 50,290원, 비교적 낮은 가격
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 가격이 너무 낮아 제외 (다른 제품과 가격 차이大き므로)

8. **매직쉐프 무회전 전자레인지 25L, 매직쉐프 (MMW-WC25TES)**
   - 제외
   - 리뷰 수: 16개, 매우 낮은 리뷰 수
   - 가격: 198,000원, 높은 가격
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 매우 낮은 리뷰 수로 제외

9. **쿠쿠 전자레인지 다이얼식 20L, 쿠쿠 (CMW-A201DB)**
   - 제외 (중복)
   - 리뷰 수: 29,941개, 매우 높은 리뷰 수지만 중복된 제품
   - 가격: 60,330원, 적절한 가격대
   - 브랜드명, 모델명: 명확함
   - 선별 근거: 중복된 제품으로 이전에 이미 선별된 제품과 동일하므로 제외

10. **쿠잉전자 프리즘 플랫 전자레인지 20L, 쿠잉전자 (MC-P20PF)**
    - 제외
    - 리뷰 수: 491개, 비교적 낮은 리뷰 수
    - 가격: 109,000원, 비교적 높은 가격
    - 브랜드명, 모델명: 명확함
    - 선별 근거: 비교적 낮은 리뷰 수로 제외

### 최종 제품 후보

@@@2@@@ **쿠쿠 전자레인지 20L, 쿠쿠 (CMW-A201DW)**
@@@3@@@ **삼성전자 세라믹 전자레인지 23L, 삼성전자 (MS23C3513AW)**
@@@5@@@ **LG전자 스마트 인버터 전자레인지 터치식 23L, LG전자 (MW23BD)**""",
            },
            {
                "role": "user",
                "content": f"""
{{제품 카테고리}}
{self.item}

{{제품 목록}}
NO | 제품명 | 가격 | 리뷰수
{list_string}
""",
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
        r = response.json()["choices"][0]["message"]["content"]
        print(r)
        res = re.findall(r'@@@(.+?)@@@', r)
        
        with open(select_file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(res))
        return select_file_name


# if __name__ == "__main__":

#     s = PerplexityProductSelector(
#         "전자레인지",
#         "test",
#         "test/01-product_names.txt",
#         "test/011-product_price.txt",
#         "test/032-product_reviews.txt",
#     )
#     response = s.select_product()