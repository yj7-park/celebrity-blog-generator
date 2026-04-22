"""
Watermark removal test script.
Usage (inside container):  python test_watermark.py
"""
from __future__ import annotations
import base64, io, os, sys, json
from pathlib import Path
from PIL import Image

SRC_DIR  = Path("/tmp/cbg_images")
OUT_DIR  = Path("/tmp/cbg_wm_test")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. 테스트 이미지 목록 ────────────────────────────────────────────────────

images = sorted(SRC_DIR.glob("*.jpg"))
print(f"\n[1] 저장된 이미지 {len(images)}개:")
for p in images:
    img = Image.open(p)
    print(f"    {p.name}  {img.size[0]}x{img.size[1]}")

if not images:
    print("이미지 없음. 파이프라인을 먼저 실행하세요.")
    sys.exit(1)

# ── 2. 시각 확인용 — 첫 3장 크기 정보 출력 ──────────────────────────────────

test_files = images[:3]
print(f"\n[2] 테스트 대상: {[p.name for p in test_files]}")

# ── 3. 워터마크 좌표 — 육안으로 측정한 수동 좌표 ─────────────────────────
# "궁금e장9포켓" 텍스트 위치 (이미지별 픽셀 확인 후 계산)
MANUAL_REGIONS: dict[str, list[dict]] = {
    "SE-00a3c34b": [{"x": 0.52, "y": 0.42, "w": 0.42, "h": 0.09}],   # 라벤더 가디건
    "SE-5074054f": [                                                     # 시계 (위/아래 두 개)
        {"x": 0.18, "y": 0.17, "w": 0.48, "h": 0.08},
        {"x": 0.18, "y": 0.55, "w": 0.48, "h": 0.08},
    ],
    "SE-b5424b4b": [{"x": 0.38, "y": 0.14, "w": 0.48, "h": 0.09}],   # 핑크 가디건
    "default":     [{"x": 0.40, "y": 0.38, "w": 0.42, "h": 0.09}],
}

# ── 4. GPT로 자동 감지 (settings에 API key가 있으면) ─────────────────────────

def detect_with_gpt(image_path: Path) -> list[dict] | None:
    try:
        from services.settings_service import load_settings
        from openai import OpenAI
        import base64, io

        settings = load_settings()
        if not settings.openai_api_key:
            return None

        client = OpenAI(api_key=settings.openai_api_key)
        img = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        from services.image_analyzer import _WATERMARK_LOCALIZE_PROMPT
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                    {"type": "text", "text": _WATERMARK_LOCALIZE_PROMPT},
                ],
            }],
            max_tokens=400,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return data.get("watermarks", [])
    except Exception as e:
        print(f"    GPT 감지 실패: {e}")
        return None


# ── 5. OpenCV 인페인팅 적용 ───────────────────────────────────────────────────

def remove_with_opencv(img: Image.Image, region: dict) -> Image.Image | None:
    """Use the updated production logic from image_processor."""
    from services.image_processor import _remove_watermark_opencv as _prod
    return _prod(img, region)


# ── 6. 각 이미지 처리 ─────────────────────────────────────────────────────────

print("\n[3-A] 수동 좌표 + 개선된 OpenCV (배경 보존)")
print("-" * 60)

for path in test_files:
    img_orig = Image.open(path).convert("RGB")
    key = next((k for k in MANUAL_REGIONS if k in path.name), "default")
    regions = MANUAL_REGIONS[key]
    print(f"\n▶ {path.name}  좌표: {regions}")
    img_result = img_orig.copy()
    for region in regions:
        res = remove_with_opencv(img_result, region)
        if res:
            img_result = res
    out_path = OUT_DIR / f"manual_v2_{path.name}"
    img_result.save(str(out_path), "JPEG", quality=90)
    print(f"  저장 → {out_path.name}")

print("\n[3-B] GPT 크롭 정제 감지 + 개선된 OpenCV")
print("-" * 60)

def detect_with_gpt_refined(image_path: Path) -> list[dict] | None:
    """Use the new 3-pass localization from image_analyzer."""
    try:
        from services.settings_service import load_settings
        from openai import OpenAI
        from services.image_analyzer import _localize_watermarks

        settings = load_settings()
        if not settings.openai_api_key:
            return None

        client = OpenAI(api_key=settings.openai_api_key)
        img = Image.open(image_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        regions = _localize_watermarks(b64, "image/jpeg", client)
        return [r.model_dump() for r in regions]
    except Exception as e:
        print(f"    GPT 정제 감지 실패: {e}")
        return None

for path in test_files:
    print(f"\n▶ {path.name}")
    img_orig = Image.open(path).convert("RGB")

    gpt_regions = detect_with_gpt_refined(path)
    if not gpt_regions:
        print("  GPT 미사용 (API 키 없음 또는 실패)")
        continue

    print(f"  GPT 정제 감지 결과 {len(gpt_regions)}개:")
    for r in gpt_regions:
        print(f"    x={r.get('x', 0):.3f} y={r.get('y', 0):.3f} "
              f"w={r.get('w', 0):.3f} h={r.get('h', 0):.3f}  '{r.get('description', '')}'")

    img_result = img_orig.copy()
    ok = 0
    for region in gpt_regions:
        if region.get("w", 0) < 0.005:
            continue
        res = remove_with_opencv(img_result, region)
        if res:
            img_result = res
            ok += 1

    out_path = OUT_DIR / f"gpt_v2_{path.name}"
    img_result.save(str(out_path), "JPEG", quality=90)
    print(f"  인페인팅 {ok}개 → {out_path.name}")

print(f"\n[4] 완료. 결과 파일: {OUT_DIR}")
print("    docker cp celebrity-blog-generator-backend-1:/tmp/cbg_wm_test/ /tmp/cbg_wm_test_host/")
