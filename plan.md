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

### 1. 전체 발행 테스트 (49개 elements)
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

### 5. 이미지 선택 품질 개선 ✅ 완료
- OpenAI Vision `analyze_item` pipeline Phase 4로 연결됨 (pipeline.py)
- best_url 자동 선정 후 image_urls 앞에 정렬

### 6. 태그 자동 입력 ✅ 완료
- `write()` 메서드에 `tags: list` 파라미터 추가
- 발행 다이얼로그에서 5개 CSS 셀렉터 탐색 후 태그 순서대로 입력 + Enter 확인
- `generator.py` → `tags` 리스트 반환, pipeline `done` 이벤트에 포함
- DashboardPage: `blogTags` 상태로 수신, 발행 시 전달

### 7. 썸네일 설정 ✅ 완료 (Selenium 방식)
- pyautogui 제거 → `input[type=file]` 직접 `send_keys()` 방식
- 4개 셀렉터 순서 시도 → 실패 시 버튼 클릭 후 동적 input 찾기
- 발견 실패 시 경고 로그 출력 후 계속 진행

### 8. 자동 로그인 세션 팝업 처리 ✅ 완료
- `write()` 진입 직후 popup 3라운드 × 5개 셀렉터 순환 dismiss
- Escape → `.se-popup-button-cancel` 등 복수 셀렉터 대응

---

## 현재 파일 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `backend/services/naver_writer.py` | SE One 디자인 요소 전면 구현, 버그 수정 |
| `backend/services/generator.py` | BlogElement 리스트 생성 로직 (divider/callout/header) |
| `backend/models/schemas.py` | BlogElement.style 필드 추가 |
| `backend/settings.json` | chrome_user_data_dir 임시 변경 (테스트용) |
