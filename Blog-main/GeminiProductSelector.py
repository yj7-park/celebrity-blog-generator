import google.generativeai as genai

import os
import re


class GeminiProductSelector:
    # API key 정보
    api_key = "AIzaSyDGxhUUAwg74F_LhnEOUU5o8mCcevBm7sE"

    def __init__(self, item, root_dir, names, prices, reviews):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)

        self.item = item
        self.names = names
        self.prices = prices
        self.reviews = reviews

        self.model = genai.GenerativeModel("gemini-1.5-flash")
        genai.configure(api_key=self.api_key)

    def select_product(self):
        select_file_name = f"{self.root_dir}/041-product_selection.txt"
        if os.path.isfile(select_file_name):
            print("File exists, skipping process.")
            return select_file_name
        product_list = []
        for i, name, price, review in zip(
            range(1, len(self.names) + 1), self.names, self.prices, self.reviews
        ):
            product_list.append((i, name, price, review))
        # sort by review count
        product_list.sort(key=lambda x: int(x[3]), reverse=True)
        list_string = ""
        for i, name, price, review in product_list[:6]:
            list_string += f"{i} | {name} | {price} | {review}\n"
        
        print(list_string)
        prompt = f"""
"제품 카테고리"와 제품명, 브랜드명 (없을 경우 NA), 모델명 (없을 경우 빈칸)이 포함된 "제품 목록"이 주어지면, 주어진 정보를 토대로 추천하기 적절한 제품을 3개 선별할거야.
기준에 의거하여 모든 후보 제품에 대해 선별과정과 선별근거, 선별되지 않은 이유를 상세히 작성하며, 최종 제품 후보를 아래와 같은 포맷으로 작성하도록 해.
선별 과정은 추가 정보를 활용하여 3개의 최종 제품 후보를 선별하도록 해.

평가 기준 설명
- 제품 카테고리: 주어진 제품 카테고리와 동일한 제품이어야 함
- 리뷰 수: 높은 리뷰 수를 가진 제품을 우선함
- 브랜드명: 브랜드 명이 명확하지 않은 제품은 제외함
- 모델명: 모델명이 명확한 제품을 우선함
- 가격: 가격이 비슷하거나, 너무 낮지 않은 제품을 우선함
- 중복: 중복된 제품은 다른 정보를 기준으로 하나만 선발함 (둘다 제외하면 안됨)
- 다양성: 다양한 브랜드의 제품을 선별함

{{Question}}
"제품 카테고리"
전자레인지

"제품 목록"
제품 번호 | 제품명, 브랜드명 (모델명) | 가격 | 리뷰 수
7 | DIBEA 올인원 무선청소기, DIBEA | 39900 | 19901
9 | 클래파 DC 모터 다용도 미니 핸디형 무선청소기 BVC-H10, 클래파 (BVC-H10) | 39900 | 19901
3 | 홈플래닛 무선 핸디 청소기, 홈플래닛 | 39100 | 4925
2 | FONOW 미니청소기, FONOW | 25800 | 1078
5 | KORELAN 무선 다용도 차량용청소기, KORELAN | 16300 | 786
6 | 에어르 M3 무선 미니 청소기, 에어르 (M3) | 44900 | 485

{{Answer}}
## 선별 과정과 선별근거

### 추가 정보 분석

7. DIBEA 올인원 무선청소기, DIBEA
   - 가격: 39,900원, 적당한 가격대
   - 브랜드명: DIBEA, 명확함
   - 모델명: 없음
   - 추가 정보: 9번 제품과 동일한 리뷰 수와 가격으로 중복 제품으로 판단
   
9. 클래파 DC 모터 다용도 미니 핸디형 무선청소기 BVC-H10, 클래파 (BVC-H10)
   - 가격: 39,900원, 적당한 가격대
   - 브랜드명: 클래파, 명확함
   - 모델명: BVC-H10, 명확함
   - 추가 정보: 7번 제품과 동일한 리뷰 수와 가격으로 중복 제품으로 판단
   
3. 홈플래닛 무선 핸디 청소기, 홈플래닛
   - 가격: 39,100원, 적당한 가격대
   - 브랜드명: 홈플래닛, 명확함
   - 모델명: 없음

2. FONOW 미니청소기, FONOW
   - 가격: 25,800원, 적당한 가격대
   - 브랜드명: FONOW, 명확함
   - 모델명: 없음

5. KORELAN 무선 다용도 차량용청소기, KORELAN
   - 가격: 16,300원, 낮은 가격
   - 브랜드명: KORELAN, 명확함
   - 모델명: 없음
   
6. 에어르 M3 무선 미니 청소기, 에어르 (M3)
   - 가격: 44,900원, 적당한 가격대
   - 브랜드명: 에어르, 명확함
   - 모델명: M3, 명확함
   
### 추가 정보 기준 3개 제품 제외

7. DIBEA 올인원 무선청소기, DIBEA
   - 9번 제품과 동일한 리뷰 수와 가격으로 중복 제품으로 판단되고 9번 제품에 비해 모델명이 불명확하여 제외

5. KORELAN 무선 다용도 차량용청소기, KORELAN
   - 타 제품에 비해 리뷰 수가 매우 낮음
   
6. 에어르 M3 무선 미니 청소기, 에어르 (M3)
   - 타 제품에 비해 리뷰가 적음

## 최종 제품 후보

@@@2@@@ FONOW 미니청소기, FONOW
@@@3@@@ 홈플래닛 무선 핸디 청소기, 홈플래닛
@@@9@@@ 클래파 DC 모터 다용도 미니 핸디형 무선청소기 BVC-H10, 클래파 (BVC-H10)

{{Question}}
"제품 카테고리"
{self.item}

"제품 목록"
제품 번호 | 제품명, 브랜드명 (모델명) | 가격 | 리뷰 수
{list_string}
"""

        r = self.model.generate_content(prompt).text
        print(r)
        res = re.findall(r"@@@(.+?)@@@", r)
        # remove not integer changeable strings
        res = [x for x in res if x.isdigit()]

        with open(select_file_name, "w", encoding="utf-8") as f:
            f.write("\n".join(res))
        return select_file_name


if __name__ == "__main__":
    item = "안마의자"
    names = [
        "파나소닉 안마의자, 파나소닉 (EP-MAJ7)",
        "브람스 올인 안마의자, 브람스",
        "쿠쿠 리네이처 안마의자, 쿠쿠 (CMS-E410CP)",
        "파나소닉 안마의자 Real Pro, 파나소닉 (EP-MAJ7)",
        "브람스 올인 UP 안마의자, 브람스 (BRAMS-K7G778IBC)",
        "제스파 컴포르테 안마의자, 제스파 (ZPC2034)",
        "제스파 컴포르테 안마의자, 제스파 (ZPC2034)",
        "파우제 M6 안마의자, 세라젬 (파우제 M6)",
        "바디프랜드 레그넘 안마의자, 바디프랜드",
        "제스파 컴포르테 안마의자, 제스파 (ZPC2035)",
    ]
    prices = [
        "7190000",
        "974000",
        "1168800",
        "7190000",
        "1289000",
        "1690000",
        "1690000",
        "3800000",
        "1990000",
        "1590000",
    ]
    reviews = [
        "2",
        "91",
        "628",
        "2",
        "99",
        "4012",
        "4012",
        "3",
        "1276",
        "4012",
    ]
    s = GeminiProductSelector(
        item,
        "test",
        names,
        prices,
        reviews,
    )
    response = s.select_product()
