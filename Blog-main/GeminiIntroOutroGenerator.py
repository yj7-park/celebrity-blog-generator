import google.generativeai as genai
import os


class GeminiIntroOutroGenerator:
    # API key 정보
    api_key = "AIzaSyDGxhUUAwg74F_LhnEOUU5o8mCcevBm7sE"

    item = ""
    generated_texts = []

    def __init__(self, item, root_dir):
        self.root_dir = root_dir
        self.item = item
        try:
            os.makedirs(root_dir)
        except:
            pass
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        genai.configure(api_key=self.api_key)

    def shuffle(self, texts):
        import random

        random.shuffle(texts)
        return texts

    def generate_intro_outro(self, overwrite=False):
        intro_file_path = self.generate_intro(overwrite)
        outro_file_path = self.generate_outro(overwrite)
        print(intro_file_path)
        print(outro_file_path)
        return intro_file_path, outro_file_path

    def generate_intro(self, overwrite=False):
        file_path = (
            f"{self.root_dir}/00-intro.txt"
        )
        texts = [
            """{{Question}}
놀이매트

{{Answer}}
안녕하세요. 극T아빠에요.✨
이번 시간에는 놀이매트를 알아보려고 해요~

아이들이 이젠 뛰어다니니까 세상 정신이 없어요.
아파트 사는 사람들은 제일 큰 걱정이 바로 우리가 층간소음을 일으킬까 걱정.. 인데요ㅠ

다행이도 우리 아랫집 분들은 아주 마음이 너그러우신 중년부부 두분이신데,
우리 아이들을 너무 예뻐해주셔서 층간소음은 신경쓰지말라고 해주시네요😍

하지만 그럼에도 우리는 우리의 의무에 따라.. 매트를 깔아보려고 해요
그럼 어떤 제품들이 있는지 알아볼까요~ㅎㅎ😊""",
            """{{Question}}
전기히터

{{Answer}}
안녕하세요. 극T아빠에요.✨
이번 시간에는 전기히터을 알아보려고 해요~

요즘 날씨가 참 애매한 것 같아요..
뭔가 날씨가 춥긴 하지만 그렇다고 막 보일러를 빵빵하게 틀기엔 좀 아깝고ㅠ
그러다보니 공기는 조금 쌀쌀한 것 같은데 뭔가 대놓고 난방 틀기엔 하긴 아쉬운..?
(저만 그런가요;;)

저는 사실 책상 앞에 앉아 있는 시간이 대부분이어서
방 전체나 거실 전체를 따뜻하게 하기 보다는 그냥 제 발만 안시리면 좋겠거든요🌈
그러다 문득 든 생각이 그러면 히터를 하나 사보는게 어떨까 하는거였어요!

그럼 어떤 제품들이 있는지 알아볼까요~ㅎㅎ😊""",
            """{{Question}}
경량패딩

{{Answer}}
안녕하세요. 극T아빠에요.✨
이번 시간에는 경량패딩을 알아보려고 해요~

요즘은 겨울에도 밖을 걸어다닐 일이 많지는 않은 것 같아요.
특히 아이가 있는 집은 어차피 차로 이동하고 외출을 해도 실내에서 할 수 있는 것들을 주로 하다보니,
엄청 두꺼운 패딩이나 코트를 입을 일이 많지 않은 것 같구요🌈

그래서 저희 부부도 경량패딩을 한번 사보고 싶어졌어요.
경량패딩도 브랜드별로 많이 나오지만,
가격 대비 소재나 원단, 충전재가 다 달라서 한번 조사를 해봐야겠다 싶었어요.

그럼 어떤 제품들이 있는지 알아볼까요~ㅎㅎ😊""",
            """{{Question}}
카시트

{{Answer}}
안녕하세요. 극T아빠에요.✨
이번 시간에는 카시트를 알아보려고 해요~

저희 집에는 아이가 두명인데,
첫째 아이의 등하원 용도로 세컨카를 사게 되면서
카시트가 하나 더 필요하게 되었어요.🌈

그럼 어떤 제품들이 있는지 알아볼까요~ㅎㅎ😊""",
        ]
        texts = self.shuffle(texts)[:-1]
        prompt = f"""블로그의 인트로 글을 생성해볼거야.
주제어에 맞추어 글을 작성하도록 해. 글 생성에 필요한 정보들은 알아서 정한 다음, 인터넷 검색을 통해 최신 정보를 얻도록 해. 작성자는 극T아빠야.
내용에는 제품이 생소하다면 간단한 소개, 이 아이템을 선택하게된 일화 또는 배경, 능청스러운 말투, 적절한 길이 (너무 길필요 없음)
문장이 너무 길지 않게 하고, 문장마다 줄을 바꾸도록 해.
그리고 문단이 나눠지면 한줄을 띄우도록 해. 그리고 불필요하게 두칸을 띄우지 않도록 주의해.
첫 인사나 알아볼까요~와 같은 반복되는 패턴의 문장들은 그대로 유지하도록 해.

아래 예시들을 참고하도록해.


{"\n\n".join(texts)}


{{Question}}
{self.item}"""
        return self.generate(file_path, prompt, overwrite=overwrite)

    def generate_outro(self, overwrite=False):
        file_path = (
            f"{self.root_dir}/50-outro.txt"
        )
        texts = [
            """{{Question}}
어그 슬리퍼

{{Answer}}
여기까지 어그 슬리퍼에 대해 알아봤는데요~
생각보다 디자인도 다양하고 활용도도 높아서 놀랐어요.

전 개인적으로 실내외 겸용으로 신을 수 있는 제품을 추천드리고 싶네요.
캐주얼한 옷차림에도 잘 어울리고, 포근해서 편하게 신기가 좋다는 평이 많아요.

그럼 다음에 또 다른 리뷰로 찾아뵐게요~
오늘도 행복한 하루 보내세요😊""",
            """{{Question}}
전기히터

{{Answer}}
요즘 히터들은 가격도 많이 비싸지 않고, 가볍고 간단한 제품들이 많이 있어서 부담이 적은 것 같아요~🎁
그래도 기본적으로 다들 안전에 관해서는 잘 신경쓰고 있는 것 같아서 걱정이 많이 되지는 않았어요.

빨간 히터는 뭔가 레트로한 느낌이 나면서도 제일 금방 따뜻해지는 매력이 있는 것 같아요ㅎㅎ
디자인도 에쁜 것들이 많아서 하나 사놓으면 연말 분위기 내기에도 좋을 것 같구요!

겸사겸사 난방비도 아끼기 위해 전기히터 하나 사용해보시는건 어떨까요?ㅎㅎ🥂

그럼 다음에 또 다른 리뷰로 찾아뵐게요~
오늘도 행복한 하루 보내세요😊""",
            """{{Question}}
경량패딩

{{Answer}}
요즘에는 꼭 유명한 브랜드가 아니어도 좋은 품질의 제품들이 많이 있는 것 같아요~🎁
(결국 저희는 매장에서 입어보고.. 뉴밸런스 제품이 그냥 이뻐서 그걸 사기로 했네요;;ㅋㅋ 조사는 왜한거..?)

여러분들은 저희처럼 충동구매하지 마시고! 잘 알아보시고 가성비 좋은 제품으로 잘 구매하시기 바랍니다~

그럼 다음에 또 다른 리뷰로 찾아뵐게요~
오늘도 행복한 하루 보내세요😊""",
            """{{Question}}
전자레인지

{{Answer}}
확실히 전보다 디자인이 예뻐진 것 같아요~

그리고 전보다 다양한 기능들이 추가로 들어가서 뭔가 신기하네요!
저는 아무래도.. 어르신들은 대기업 제품을 좋아할 것 같아서 결국 삼성 제품으로 사드렸어요~🎁

전자레인지 사실때 글이 참고가 되시면 좋겠네요~

그럼 다음에 또 다른 리뷰로 찾아뵐게요~
오늘도 행복한 하루 보내세요😊""",
        ]
        texts = self.shuffle(texts)[:-1]
        prompt = f"""블로그의 맺음말을 생성해볼거야.
주제어에 맞추어 글을 작성하도록 해. 글 생성에 필요한 정보들은 알아서 정한 다음, 인터넷 검색을 통해 최신 정보를 얻도록 해.
문장이 너무 길지 않게 하고, 문장마다 줄을 바꾸도록 해.
그리고 문단이 나눠지면 한줄을 띄우도록 해. 그리고 불필요하게 두칸을 띄우지 않도록 주의해.
첫 인사나 알아볼까요~와 같은 반복되는 패턴의 문장들은 그대로 유지하도록 해.

아래 예시들을 참고하도록해.


{"\n\n".join(texts)}


{{Question}}
{self.item}"""
        return self.generate(file_path, prompt, overwrite=overwrite)

    def generate(self, file_path, prompt, overwrite=False):
        # check if file exists
        if not overwrite:
            if os.path.isfile(file_path):
                print("File exists, skipping process.")
                return file_path
        generated_text = self._generate(prompt)
        
        # TODO: 수동 조절
        generated_text = generated_text.replace("\n\n", "\n")
        generated_text = generated_text.replace("  ", " ")
        generated_text = generated_text.replace("…", "...")

        print(generated_text)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(generated_text)
        return file_path

    def _generate(self, prompt):
        response = self.model.generate_content(prompt)
        generated_text = response.text
        return generated_text


# main
if __name__ == "__main__":
    item = "습식 청소기"
    ai = GeminiIntroOutroGenerator(item)
    # ai.test()
    # ai.generate_tag()
    ai.generate_intro_outro(overwrite=True)

    # write blog post with multiple elements
    # ai.write_blog_post()
