from CoupangSearcher import CoupangSearcher
from CoupangCrawler import CoupangCrawler
from OpenAIDescGenerator import OpenAIDescGenerator
from PerplexityNameGenerator import PerplexityNameGenerator
# from PerplexityProductSelector import PerplexityProductSelector
from GeminiProductSelector import GeminiProductSelector
from GeminiDescGenerator import GeminiDescGenerator
from GeminiTagGenerator import GeminiTagGenerator
from NaverBlogWriter import NaverBlogWriter
from ImageGenerator import ImageGenerator
from VideoMaker import VideoMaker
from GeminiIntroOutroGenerator import GeminiIntroOutroGenerator

import os
import json


class BlogGenerator:
    def initialize(self, item):
        # create data directory {[yyyy-mm-dd] item}
        import os
        import datetime

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        root_dir = f"C:/Utilities/Blog/data/[{date_str}] {item}"
        if not os.path.exists(root_dir):
            os.makedirs(root_dir)
        return root_dir

    # 1. 목록 조회
    def search_product_list(self, item, root_dir):
        print("\n\n==========\n1. 제품 목록 조회 (CoupangAPI)")
        searcher = CoupangSearcher(item, root_dir)
        pre_name_file_path, image_file_path, url_file_path, price_file_path = (
            searcher.search_and_save(limit=10)
        )

        # TODO: 1-1. 품명 수정
        print("\n\n==========\n1-1. 제품명 수정")
        pre_names = []
        with open(pre_name_file_path, "r", encoding='utf8') as f:
            pre_names = f.read().splitlines()
        g = PerplexityNameGenerator(item, root_dir, pre_names)
        name_file_path = g.generate_names()

        return name_file_path, image_file_path, url_file_path, price_file_path

    # 2. 인트로/아웃트로 생성
    def generate_intro_outro(self, item, root_dir):
        print("\n\n==========\n2. 인트로/아웃트로 생성 (Gemini API)")
        generator = GeminiIntroOutroGenerator(item, root_dir)
        intro_file_path, outro_file_path = generator.generate_intro_outro()
        try:
            del generator
        except:
            pass
        # deprecated
        # intro=f"""안녕하세요. 극T아빠에요.✨
        # 이번 시간에는 어그 슬리퍼를 알아보려고 해요~

        # 요즘 날씨가 추운데 제가 신기한걸 발견했어요ㅋㅋ
        # 여자분들이 보통 어그부츠를 신는건 많이 봤었는데,
        # 요즘에는 어그로 된 슬리퍼 같은걸 신고 다니더라구요?

        # 신기해서 아내한테 물어봤더니 그게 요즘 유행이라네요!

        # 그래서 한번 찾아봤는데 이게 생각보다 전통이 있더라구요ㅋㅋ
        # 호주에서는 1970년대부터 서핑 후에 발을 따뜻하게 하려고 신고는 했대요 글쎄!

        # 아내도 관심이 있어보이길래 한번 조사해보려구요ㅋㅋ
        # 그럼 어떤 제품들이 있는지 알아볼까요~ㅎㅎ😊"""
        # outro="""여기까지 어그 슬리퍼에 대해 알아봤는데요~
        # 생각보다 디자인도 다양하고 활용도도 높아서 놀랐어요.

        # 전 개인적으로 실내외 겸용으로 신을 수 있는 제품을 추천드리고 싶네요.
        # 캐주얼한 옷차림에도 잘 어울리고, 포근해서 편하게 신기가 좋다는 평이 많아요.

        # 그럼 다음에 또 다른 리뷰로 찾아뵐게요~
        # 오늘도 따뜻하고 행복한 하루 보내세요😊"""
        return intro_file_path, outro_file_path

    # TODO: 3. 이미지 다운로드
    def download_product_images(self, item, root_dir, url_file_path):
        print("\n\n==========\n3. 제품 이미지 다운로드")
        image_urls = []
        with open(url_file_path, "r") as f:
            image_urls = f.read().splitlines()
        c = CoupangCrawler(item, root_dir, image_urls)
        score_file_path, review_file_path = c.download_images()
        try:
            del c
        except:
            pass
        return score_file_path, review_file_path

    # TODO: 4. 제품 선별
    def select_product(
        self, item, root_dir, name_file_path, price_file_path, review_file_path
    ):
        print("\n\n==========\n4. 제품 선별")
        with open(name_file_path, "r", encoding="utf-8") as f:
            names = f.read().splitlines()
        with open(price_file_path, "r", encoding="utf-8") as f:
            prices = f.read().splitlines()
        with open(review_file_path, "r", encoding="utf-8") as f:
            reviews = f.read().splitlines()
        # s = PerplexityProductSelector(item, root_dir, names, prices, reviews)
        s = GeminiProductSelector(item, root_dir, names, prices, reviews)
        select_file_path = s.select_product()
        try:
            del s
        except:
            pass
        return select_file_path

    # 4. 썸네일 생성
    def generate_thumbnail(self, item, root_dir, image_file_path, select_file_path):
        print("\n\n==========\n4. 썸네일 생성 (Briefnet)")
        image_urls = []
        with open(image_file_path, "r") as f:
            image_urls = f.read().splitlines()
        with open(select_file_path, "r", encoding='utf-8') as f:
            selections = f.read().splitlines()
        image_urls = [image_urls[int(s) - 1] for s in selections]
        extractor = ImageGenerator(item, root_dir, image_urls)
        thumbnail_path = extractor.download_and_combine_images()
        try:
            del extractor
        except:
            pass
        return thumbnail_path

    # 5. (제품별) 소개 생성
    def generate_descriptions(self, item, root_dir, name_file_path, select_file_path):
        print("\n\n==========\n5. 제품별 소개글 생성 (PerplexityAI)")
        name_list = []
        with open(name_file_path, "r", encoding="utf-8") as f:
            name_list = f.read().splitlines()
        with open(select_file_path, "r") as f:
            selections = f.read().splitlines()
        name_list = [name_list[int(s) - 1] for s in selections]
        generator = OpenAIDescGenerator(item, root_dir, name_list)
        # generator = GeminiDescGenerator(item, root_dir, name_list)
        desc_file_path = generator.generate_desc()
        try:
            del generator
        except:
            pass
        return desc_file_path

    # 6. 태그 생성
    def generate_tags(self, item, root_dir, name_file_path):
        print("\n\n==========\n6. 태그 생성 (GeminiAI)")
        with open(name_file_path, "r", encoding="utf-8") as f:
            name_list = f.read().splitlines()
        tag_generator = GeminiTagGenerator(item, root_dir, name_list)
        tag_file_path = tag_generator.generate_tag()
        try:
            del tag_generator
        except:
            pass
        return tag_file_path

    # 7. 비디오 생성
    def generate_video(self, item):
        print("\n\n==========\n7. 비디오 생성 (ffmpeg)")
        video_maker = VideoMaker(item)
        video_file_path = video_maker.make_video()
        try:
            del video_maker
        except:
            pass
        return video_file_path

    # 8. 글 작성
    def write(
        self,
        item,
        root_dir,
        intro_file_path,
        name_file_path,
        url_file_path,
        desc_file_path,
        outro_file_path,
        tag_file_path,
        thumbnail_path,
        select_file_path,
    ):
        print("\n\n==========\n8. 블로그 글 내용 작성 (Json)")
        elements = []

        # 대가성문구
        # elements.append({"image": "C:/Utilities/Blog/images/tail.png"})
        elements.append({"images": {"paths": ["C:/Utilities/Blog/images/tail.png"]}})

        # intro
        with open(intro_file_path, "r", encoding="utf-8") as f:
            intro = f.read()
            elements.append({"text": intro})

        # intro, outro, name, desc, link
        with open(select_file_path, "r") as f:
            selections = f.read().splitlines()

        name_list = []
        with open(name_file_path, "r", encoding="utf-8") as f:
            name_list = f.read().splitlines()
        name_list = [name_list[int(s) - 1] for s in selections]

        url_list = []
        with open(url_file_path, "r") as f:
            url_list = f.read().splitlines()
        url_list = [url_list[int(s) - 1] for s in selections]

        descriptions = []
        with open(desc_file_path, "r", encoding="utf-8") as f:
            descriptions = f.read().splitlines()

        for i, selected_index, name, url in zip(range(len(selections)), selections, name_list, url_list):
            # header
            elements.append({"header": f"{i+1}. {name}"})
            
            # image
            image_path = f"{root_dir}/images/{selected_index}"
            # images = []
            # images.append(f"\"{root_dir}/images/{index + 1}-product_image.png\"")
            # images = [f'"{image_path}/{i}"' for i in os.listdir(image_path)] + images
            images = [f'"{image_path}/{i}"' for i in os.listdir(image_path)]
            elements.append({"images": {"paths": images[:2]}})
            
            # desc
            elements.append({"text": descriptions[i]})
            
            # url
            elements.append({"url_text": url})

        # outro
        with open(outro_file_path, "r", encoding="utf-8") as f:
            outro = f.read()
            elements.append({"text": outro})

        tag = ""
        with open(tag_file_path, "r", encoding="utf-8") as f:
            tag = f.read()

        # video
        # video_tag = ''.join([tag_item + ' ' for tag_item in tag.replace('#','').split(' ')])
        # elements.append({"video":{"path":video_file_path, "tags":video_tag}})

        # tag
        elements.append({"text": tag})

        # Json 파일 생성
        file_path = f"{root_dir}/99-contents.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"elements": elements}, indent=4, ensure_ascii=False))

        # 9. 블로그 글 작성
        print("\n\n==========\n9. 블로그 글 작성 (NaverBlogWriter Script)")
        writer = NaverBlogWriter(item, root_dir, file_path, thumbnail_path)
        blog_url_file_path = writer.write_blog_post()
        try:
            del writer
        except:
            pass
        return blog_url_file_path


if __name__ == "__main__":
    item = "전자레인지"
    g = BlogGenerator()

    root_dir = g.initialize(item)
    name_file_path, image_file_path, url_file_path, price_file_path = (
        g.search_product_list(
            item,
            root_dir,
        )
    )
    intro_file_path, outro_file_path = g.generate_intro_outro(
        item,
        root_dir,
    )

    # input('Press any key to continue...')
    score_file_path, review_file_path = g.download_product_images(
        item,
        root_dir,
        url_file_path,
    )
    select_file_path = g.select_product(
        item,
        root_dir,
        name_file_path,
        price_file_path,
        review_file_path,
    )
    # input('Press any key to continue...')
    thumbnail_path = g.generate_thumbnail(
        item,
        root_dir,
        image_file_path,
        select_file_path,
    )
    desc_file_path = g.generate_descriptions(
        item,
        root_dir,
        name_file_path,
        select_file_path,
    )
    tag_file_path = g.generate_tags(
        item,
        root_dir,
        name_file_path,
    )
    blog_url_file_path = g.write(
        item,
        root_dir,
        intro_file_path,
        name_file_path,
        url_file_path,
        desc_file_path,
        outro_file_path,
        tag_file_path,
        thumbnail_path,
        select_file_path,
    )
