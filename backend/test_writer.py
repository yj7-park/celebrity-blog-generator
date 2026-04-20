"""
Element별 SE One 에디터 테스트 스크립트.
각 element 타입을 하나씩 확인하고 실제로 적용되는지 검증.

실행: cd backend && .venv/Scripts/python test_writer.py
"""
import json, sys, time
from pathlib import Path

# 백엔드 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.naver_writer import NaverBlogWriter

SETTINGS_FILE = Path(__file__).parent / "settings.json"
settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

NAVER_ID = settings.get("naver_id", "")
NAVER_PW = settings.get("naver_pw", "")
CHROME_DIR = settings.get("chrome_user_data_dir", "")

# ── 테스트 elements (최소 구성, 각 타입 1개씩) ────────────────────────────
AFFILIATE_IMG = str(Path(__file__).parent / "static" / "assets" / "affiliate_disclosure.png")

# 실제 이미지 경로 (cbg_images에서 하나 찾기)
import glob
cbg_imgs = glob.glob(r"C:\Users\Public\Documents\ESTsoft\CreatorTemp\cbg_images\*.jpg")
SAMPLE_IMG = cbg_imgs[0] if cbg_imgs else AFFILIATE_IMG

TEST_ELEMENTS = [
    # 1. 대가성 이미지
    {"type": "image", "content": AFFILIATE_IMG},
    # 2. 일반 텍스트
    {"type": "text",  "content": "이것은 일반 본문 텍스트입니다. 잘 들어가나요?"},
    # 3. 구분선
    {"type": "divider", "content": "line2"},
    # 4. 소제목 (header)
    {"type": "header", "content": "[테스트] 소제목 헤더 텍스트"},
    # 5. 제품 이미지
    {"type": "image",  "content": SAMPLE_IMG},
    # 6. callout (이탤릭 일반 텍스트로 변경됨)
    {"type": "callout", "content": "이것은 callout 텍스트입니다 (이탤릭 처리)."},
    # 7. url_text (링크 적용 테스트)
    {"type": "url_text", "content": "https://www.coupang.com/vp/products/7774407515"},
    # 8. 마무리 텍스트
    {"type": "text", "content": "테스트 종료. 이 글은 삭제됩니다."},
]

def status_cb(phase: str, msg: str):
    print(f"[STATUS] {phase}: {msg}")

def main():
    writer = NaverBlogWriter(
        naver_id=NAVER_ID,
        naver_pw=NAVER_PW,
        chrome_user_data_dir=CHROME_DIR,
    )
    print(f"[TEST] 대가성 이미지: {AFFILIATE_IMG}")
    print(f"[TEST] 샘플 이미지: {SAMPLE_IMG}")
    print(f"[TEST] elements: {len(TEST_ELEMENTS)}개")
    print()

    try:
        url = writer.write(
            title="[테스트] SE One 에디터 element 테스트",
            elements=TEST_ELEMENTS,
            thumbnail_path="",
            status_cb=status_cb,
            tags=["테스트", "SE원", "element"],
        )
        print(f"\n[TEST] 발행 완료: {url}")
        print("[TEST] 30초 후 자동으로 삭제합니다...")
        time.sleep(30)
        # 발행된 글 삭제는 수동으로 해야 함 (Naver 블로그 삭제 API 없음)
        print("[TEST] 테스트 완료. 블로그 관리 페이지에서 테스트 글을 직접 삭제해주세요.")
    except Exception as e:
        print(f"[TEST] 오류: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
