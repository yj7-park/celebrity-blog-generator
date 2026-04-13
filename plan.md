# Celebrity Blog Generator — 작업 현황 및 다음 단계

> 마지막 업데이트: 2026-04-13

---

## ✅ 완료된 작업

### SE One 에디터 디자인 요소 구현 (`backend/services/naver_writer.py`)
- **구분선(divider)**: 툴바 버튼(기본 스타일만) 대신 인라인 `+` 버튼 메뉴 → hover → 서브패널 스타일 클릭으로 교체. `line2` 스타일 지정 가능
- **인용구 callout**: 같은 방식으로 `quotation_postit` 스타일 삽입 + Enter×2 후 Escape로 블록 탈출
- **헤더**: `_apply_text_color("E8531A")` 오렌지 색상 후 텍스트 입력, 이후 `"333333"` 복원
- **이미지**: 클립보드 붙여넣기 후 `Ctrl+E` 중앙 정렬
- **구매 버튼(`url_text`)**: 22pt 굵게, 중앙 정렬, `🛒 최저가 구매하러 가기` 텍스트 + SE One 링크 적용
- **대가성 문구**: 최상단에 이미지(`affiliate_disclosure.png`)로 삽입

### 버그 수정
- `Ctrl+Alt+H` 매 element 후 실행 → 단락 스타일 오염 가능성 있어 **제거**
- `_open_insert_menu()` 강화: Escape → `.se-main-section` 마우스 이동 → timeout 5s→8s
- `_insert_callout()` 탈출 강화: Enter×2 후 `Keys.ESCAPE` 추가
- 이미지 삽입 후 `window.focus()`로 포커스 복원 (`switch_to.window()` 제거)
- `url_text` 내 모든 `.click()` → `execute_script("arguments[0].click()")` 변경
- Chrome `--start-maximized` + `driver.maximize_window()` 병행으로 56px 창 문제 해결

### 블로그 생성(`backend/services/generator.py`)
- LLM 구조화 출력 → `BlogElement` 리스트 변환
- 아이템별: divider → header → 이미지 → 본문 → callout → url_text
- 두괄식/미괄식 모드 지원

---

## 🔴 당장 해결 필요 — 테스트 차단 중

### 1. Chrome 로그인 세션 문제
**상황**: `chrome-user-data/lockfile`이 다른 프로세스에 잠겨 있어 Chrome이 기존 프로파일로 시작 불가  
**현재 설정**: `settings.json`에 `chrome_user_data_dir: "C:/Utilities/Blog/chrome-user-data"` 변경  
**해결 방법** (둘 중 하나):
- **방법 A (권장)**: PC 재시작 → 기존 `chrome-user-data` lockfile 자동 해제 → `settings.json`을 `""` (빈 값, 기본 경로)로 되돌림
- **방법 B**: `! chrome.exe --user-data-dir="C:/Utilities/Blog/chrome-user-data"` 실행 후 Naver 수동 로그인 → Chrome 종료 → 이후 write 요청은 자동 로그인

### 2. 전체 발행 테스트 (49개 elements)
위 로그인 문제 해결 후:
- run ID `61789b32b8d1` (아이유, 49 elements) write 재시도
- element 7, 18, 22, 28, 34, 40, 46 (두 번째 이후 divider들) 모두 OK 확인
- 실제 발행된 블로그 포스트에서 구분선·callout·오렌지 헤더·구매버튼이 시각적으로 보이는지 확인

---

## 🟡 검증 필요 — 코드는 있지만 실제 동작 미확인

### 3. `_apply_text_color` 헥스 입력 CSS selector 검증
```python
# 시도 순서로 아래 셀렉터를 탐색함 — 실제 SE One HTML에서 확인 필요
"input.se-colorpicker-custom-hex"
".se-colorpicker-custom-hex"
"input[maxlength='6']"
".se-colorpicker input[type='text']"
```
발행 후 헤더 색상이 오렌지(#E8531A)로 나오지 않는다면 디버그 스크린샷으로 컬러피커 HTML 확인 필요

### 4. `_insert_header` Ctrl+Alt+Q 효과 확인
현재 헤더 삽입 전 `Ctrl+Alt+Q` (SE One 인용구 단락 스타일)를 적용 중인데,
실제로 스타일이 바뀌는지 또는 SE One에서 다른 단축키를 써야 하는지 확인 필요

---

## 🟢 다음 기능 개선 (테스트 통과 후)

### 5. 이미지 선택 품질 개선
- 현재 `processed_image_path` 없으면 `image_urls[0]` 사용 (원본 URL, 워터마크 있을 수 있음)
- OpenAI Vision으로 워터마크 분석 후 최적 이미지 선택하는 `analyze-images` 엔드포인트 이미 구현됨 → 파이프라인에 연결

### 6. 태그 자동 입력
`NaverWriteRequest.tags` 필드는 있으나 현재 write()에서 실제 태그 입력 미구현  
SE One 발행 다이얼로그의 태그 입력란에 tags 삽입 로직 추가 필요

### 7. 썸네일 설정
`thumbnail_path` 파라미터 있으나 `HAS_PYAUTOGUI` 의존 → 안정적인 Selenium 방식으로 교체 고려

---

## 현재 파일 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `backend/services/naver_writer.py` | SE One 디자인 요소 전면 구현, 버그 수정 |
| `backend/services/generator.py` | BlogElement 리스트 생성 로직 (divider/callout/header) |
| `backend/models/schemas.py` | BlogElement.style 필드 추가 |
| `backend/settings.json` | chrome_user_data_dir 임시 변경 (테스트용) |
