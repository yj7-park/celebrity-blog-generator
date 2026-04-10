# WS2 Project — Agent Context

> Last updated: 2026-04-10 (v2)
> Purpose: Quick-start reference for any agent continuing this project.

---

## 1. 최종 목표

한국 연예인 아이템 자동 블로그 수익화 시스템:
1. 네이버 블로거 RSS에서 연예인 착용 아이템 자동 수집
2. GPT-4o-mini로 구조화 데이터 추출 (연예인 × 카테고리 × 제품명 × 이미지 × 키워드)
3. 쿠팡 파트너스 어필리에이트 링크 자동 생성
4. SEO 블로그 포스트 자동 생성
5. Selenium으로 네이버 블로그 자동 발행
6. APScheduler로 전체 파이프라인 자동 스케줄링

---

## 2. 프로젝트 구조

```
ws2/
├── AGENT_CONTEXT.md
├── .env                         # gh_token, openai_token, hf_token
├── .github/workflows/deploy.yml # standalone → web branch (GitHub Pages)
│
├── backend/                     # FastAPI 서버 (포트 8000)
│   ├── main.py                  # APScheduler + 라우터 등록 + SPA 서빙
│   ├── requirements.txt
│   ├── settings.json            # 런타임 설정 (API 키, Naver 계정 등)
│   ├── models/schemas.py        # 모든 Pydantic 모델
│   ├── services/
│   │   ├── settings_service.py  # settings.json 로드/저장
│   │   ├── collector.py         # RSS 수집 + HTML 스크래핑 (ordered_blocks)
│   │   ├── extractor.py         # LLM 구조화 추출 → CelebItem[]
│   │   ├── analyzer.py          # 연예인 트렌딩 분석
│   │   ├── generator.py         # 블로그 포스트 생성
│   │   ├── coupang.py           # 쿠팡 파트너스 API (HMAC 인증)
│   │   └── naver_writer.py      # Selenium 네이버 블로그 작성
│   ├── routers/
│   │   ├── pipeline.py          # /api/pipeline/* (SSE + REST)
│   │   ├── coupang.py           # /api/coupang/*
│   │   ├── naver.py             # /api/naver/*
│   │   ├── scheduler.py         # /api/scheduler/*
│   │   └── settings.py          # /api/settings
│   └── scheduler/
│       └── tasks.py             # APScheduler 작업 정의
│
├── frontend/                    # Vite + React + TypeScript (포트 5173 dev)
│   ├── src/
│   │   ├── App.tsx              # BrowserRouter + Routes
│   │   ├── main.tsx
│   │   ├── lib/
│   │   │   ├── types.ts         # 공유 타입 (CelebItem, CoupangProduct, ScheduleJob 등)
│   │   │   └── api.ts           # API 클라이언트 (BASE_URL=http://localhost:8000)
│   │   ├── components/
│   │   │   ├── Layout.tsx       # 사이드바 + 헤더 레이아웃
│   │   │   ├── Card.tsx
│   │   │   ├── ItemsPanel.tsx   # CelebItem[] 리치 테이블
│   │   │   ├── BlogPostPanel.tsx
│   │   │   ├── PostsPanel.tsx
│   │   │   ├── TrendingPanel.tsx
│   │   │   └── ProgressBar.tsx
│   │   └── pages/
│   │       ├── DashboardPage.tsx  # SSE 전체 파이프라인 + 결과 요약
│   │       ├── PipelinePage.tsx   # 4단계 수동 실행
│   │       ├── CoupangPage.tsx    # 상품 검색 + 어필리에이트 링크
│   │       ├── BlogWriterPage.tsx # 요소 편집기 + 네이버 발행
│   │       ├── SchedulerPage.tsx  # 스케줄 CRUD + cron 설정
│   │       └── SettingsPage.tsx   # API 키 / Naver 계정 설정
│   └── vite.config.ts
│
├── standalone/                  # GitHub Pages 배포용 (순수 클라이언트)
│   └── src/lib/                 # collector, extractor, generator, analyzer, types
│
└── pipeline/                    # Python 오프라인 스크립트
    ├── collect_fixtures.py      # 네이버 HTML 수집 → fixtures/
    └── extract_items.py         # LLM 추출 → extracted/celeb_items.json
```

---

## 3. API 엔드포인트 전체 목록

### Pipeline (`/api/pipeline/`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/run?days&max_posts&top_celebs&openai_api_key` | SSE 전체 파이프라인 |
| POST | `/collect` | RSS 수집 → PostItem[] |
| POST | `/analyze` | 연예인 분석 → string[] |
| POST | `/scrape` | 스크랩+LLM 추출 → CelebItem[] |
| POST | `/generate` | 블로그 포스트 생성 |

### Coupang (`/api/coupang/`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/search` | 키워드 상품 검색 |
| GET | `/affiliate?product_url=` | 어필리에이트 URL + 단축 URL |
| POST | `/shorten` | IS.GD URL 단축 |

### Naver (`/api/naver/`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/write` | Selenium 블로그 발행 |
| GET | `/status` | 현재 발행 상태 |

### Scheduler (`/api/scheduler/`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/jobs` | 스케줄 목록 |
| POST | `/jobs` | 스케줄 생성 |
| PUT | `/jobs/{id}` | 스케줄 수정 |
| DELETE | `/jobs/{id}` | 스케줄 삭제 |
| POST | `/jobs/{id}/run` | 즉시 실행 |

### Settings (`/api/settings`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `` | 설정 조회 (마스킹) |
| GET | `/raw` | 설정 조회 (원본) |
| POST | `` | 설정 저장 |

---

## 4. 핵심 기술 상세

### 네이버 블로그 스크래핑
- PostView URL: `https://blog.naver.com/PostView.naver?blogId={id}&logNo={no}&redirect=Dlog&widgetTypeCall=true&directAccess=false`
- Smart Editor 4 선택자: `p.se-text-paragraph` (텍스트), `img.se-image-resource` (이미지), `a.se-link` (링크)
- `ordered_blocks`: DOM 순서 보존 text+image 인터리빙 → LLM에 `IMAGE_N` 레이블로 전달

### 쿠팡 파트너스 API
- HMAC-SHA256 서명: `datetime_gmt + method + path + query`
- Authorization 헤더: `CEA algorithm=HmacSHA256, access-key=..., signed-date=..., signature=...`
- 설정: `settings.json`의 `coupang_access_key`, `coupang_secret_key`

### Selenium 네이버 블로그 작성 (Windows 전용)
- 필수 라이브러리: selenium, pyperclip, win32clipboard(이미지), pyautogui(파일 다이얼로그)
- 동작 방식: 클립보드 붙여넣기로 텍스트/이미지 삽입, 휴먼 딜레이 시뮬레이션
- 지원 요소 타입: `text`, `header`, `image`, `url`(OG 카드), `url_text`(구매버튼)
- URL 단축: IS.GD API (`https://is.gd/create.php?format=json&url=...`)

### 설정 관리
- 저장 위치: `backend/settings.json`
- 민감정보 마스킹: GET `/api/settings` 응답에서 API 키 마스킹 처리
- GET `/api/settings/raw`는 내부용 (마스킹 없음)

### APScheduler
- 타임존: Asia/Seoul
- Trigger: cron (분 시 일 월 요일)
- 스케줄 메타데이터: `routers/scheduler.py`의 `_jobs` 딕셔너리 (메모리, 재시작 시 초기화)
- 실제 실행: `scheduler/tasks.py::run_pipeline_job(job_id)`

---

## 5. 실행 방법

### Backend
```bash
cd ws2/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (개발)
```bash
cd ws2/frontend
npm install
npm run dev   # → http://localhost:5173
```

### Frontend (프로덕션 빌드 → 백엔드 서빙)
```bash
cd ws2/frontend
npm run build
# dist/ 폴더를 backend/static/으로 복사
cp -r dist/* ../backend/static/
# 이후 http://localhost:8000 에서 풀스택 서빙
```

### Standalone (GitHub Pages)
```bash
cd ws2/standalone
npm run build
git push origin main   # → GitHub Actions → web branch 자동 배포
```

---

## 6. 환경 변수 / 설정 파일

**`ws2/.env`** (로컬 개발용)
```
gh_token=ghp_...      # GitHub PAT (repo + workflow scope)
openai_token=sk-...   # OpenAI
hf_token=hf_...       # HuggingFace (미사용)
```

**`ws2/backend/settings.json`** (런타임 설정 — UI에서 변경 가능)
```json
{
  "openai_api_key": "sk-...",
  "coupang_access_key": "...",
  "coupang_secret_key": "...",
  "coupang_domain": "https://api-gateway.coupang.com",
  "naver_id": "...",
  "naver_pw": "...",
  "pipeline_days": 2,
  "pipeline_max_posts": 10,
  "pipeline_top_celebs": 5,
  "chrome_user_data_dir": "C:/Utilities/Blog/chrome-user-data"
}
```

---

## 7. 남은 작업 / 개선 포인트

### 즉시 필요
- [ ] `backend/settings.json`에 실제 Naver ID/PW 입력 (Settings 페이지에서)
- [ ] `backend/settings.json`에 실제 OpenAI API 키 입력
- [ ] Chrome 드라이버 경로 확인 (webdriver-manager가 자동 설치)
- [ ] `pip install -r requirements.txt` 실행 (`pywin32` 포함)

### 기능 확장
- [ ] 스케줄러 job 영속성 (재시작 후에도 유지되도록 SQLite jobstore 연동)
- [ ] 쿠팡 상품 이미지 CORS 프록시 (브라우저에서 직접 불러오기 실패 시)
- [ ] 블로그 글 생성 시 쿠팡 상품 자동 연동 (CelebItem 키워드로 쿠팡 검색 → 어필리에이트 링크 자동 삽입)
- [ ] 발행 히스토리 저장 (DB 또는 JSON 파일)
- [ ] 썸네일 자동 생성 (PIL로 제품 이미지 합성)
- [ ] 네이버 블로그 이중 인증 대응
- [ ] `vvd.bz` 단축 URL 서버사이드 리다이렉트 추적

### 블로그 목록 확장
`backend/services/collector.py`의 `BLOGS` 리스트에 추가:
```python
("새블로그ID", "카테고리폴더명")
```
