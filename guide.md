# Celebrity Blog Generator — 개발 가이드

## 프로젝트 목적

쿠팡 파트너스(Affiliate) 수익화를 위한 자동화 블로그 생성 시스템.  
TV 프로그램·유튜브·뉴스 등에서 이슈가 된 **연예인과 그들의 아이템**을 자동 수집하고,
SEO 블로그 포스트를 작성한 뒤 네이버 블로그에 자동 발행한다.
각 아이템은 쿠팡 어필리에이션 URL로 연결해 독자의 구매를 유도한다.

---

## 전체 아키텍처

```
[네이버 블로거 RSS × 15]
        │
        ▼
  1. 수집 (collector.py)
     · RSS 파싱 → PostItem[]
     · HTML 스크랩 → OrderedBlock[] (텍스트+이미지 순서 보존)
        │
        ▼
  2. 분석 (analyzer.py)
     · GPT-4o-mini로 트렌딩 연예인 추출
        │
        ▼
  3. 추출 (extractor.py)
     · GPT-4o-mini로 CelebItem[] 구조화 (연예인·제품명·카테고리·이미지·링크)
        │
        ▼
  4. 쿠팡 검색 (coupang.py)   ← 핵심 수익화
     · product_name으로 쿠팡 검색
     · Affiliate URL → IS.GD 단축
     · CelebItem.link_url 갱신
        │
        ▼
  5. 생성 (generator.py)
     · GPT-4o-mini로 SEO 블로그 포스트 작성
     · BlogElement[] 반환 (header / text / url_text)
     · 대가성 문구 자동 삽입
        │
        ▼
  6. (선택) 비디오 생성 (video_maker.py)
     · 아이템 이미지 → FFmpeg MP4 슬라이드쇼
        │
        ▼
  7. 발행 (naver_writer.py)
     · Selenium으로 네이버 블로그 자동 로그인·발행
     · 썸네일, 이미지, 텍스트, 링크 버튼, 비디오 삽입
```

---

## 기술 스택

| 계층 | 기술 |
|---|---|
| Backend | FastAPI + Uvicorn (포트 8000) |
| Frontend | React 18 + TypeScript + Vite (포트 5173) |
| LLM | OpenAI gpt-4o-mini |
| 쿠팡 API | HMAC-SHA256 Partners Open API |
| 웹 자동화 | Selenium 4 + ChromeDriver |
| 스케줄링 | APScheduler 3.10 (Asia/Seoul) |
| 이미지 처리 | Pillow |
| 비디오 생성 | FFmpeg (슬라이드쇼) |

---

## 디렉토리 구조

```
celebrity-blog-generator/
├── backend/
│   ├── main.py                 # FastAPI 앱 + APScheduler
│   ├── settings.json           # 런타임 설정 (API 키, 계정 정보)
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py          # Pydantic 모델 전체
│   ├── services/
│   │   ├── settings_service.py # settings.json 로드/저장
│   │   ├── collector.py        # RSS 수집 + HTML 스크래핑
│   │   ├── analyzer.py         # GPT 연예인 트렌드 분석
│   │   ├── extractor.py        # GPT 구조화 추출
│   │   ├── generator.py        # GPT 블로그 포스트 생성 → BlogElement[]
│   │   ├── coupang.py          # 쿠팡 파트너스 API
│   │   ├── naver_writer.py     # Selenium 네이버 블로그 자동 발행
│   │   └── video_maker.py      # FFmpeg 슬라이드쇼 생성
│   ├── routers/
│   │   ├── pipeline.py         # /api/pipeline/* (수집→분석→추출→쿠팡→생성)
│   │   ├── coupang.py          # /api/coupang/*
│   │   ├── naver.py            # /api/naver/*
│   │   ├── scheduler.py        # /api/scheduler/*
│   │   └── settings.py         # /api/settings
│   └── scheduler/
│       └── tasks.py            # APScheduler 작업 정의
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx   # SSE 전체 파이프라인
│   │   │   ├── PipelinePage.tsx    # 4단계 수동 실행
│   │   │   ├── CoupangPage.tsx     # 상품 검색 UI
│   │   │   ├── BlogWriterPage.tsx  # 요소 편집 + 발행
│   │   │   ├── SchedulerPage.tsx   # 스케줄 관리
│   │   │   └── SettingsPage.tsx    # API 키/계정 설정
│   │   └── components/
│   │       ├── Layout.tsx
│   │       ├── ItemsPanel.tsx
│   │       └── BlogPostPanel.tsx
├── Blog-main/                  # 참조 프로젝트 (Blog/)
├── guide.md                    # 이 파일
├── plan.md                     # 남은 작업 목록
└── AGENT_CONTEXT.md
```

---

## 핵심 데이터 모델

```python
# 추출된 연예인 아이템
class CelebItem:
    celeb: str              # 연예인 이름 (예: "아이유")
    category: str           # 카테고리 (의류/신발/가방/뷰티/...)
    product_name: str       # 브랜드+모델명 (예: "발렌시아가 후디")
    image_urls: List[str]   # 원본 블로그 이미지 URL
    keywords: List[str]     # 방송명, 특징 키워드
    link_url: str           # 쿠팡 어필리에이션 URL (파이프라인에서 갱신)
    source_title: str       # 원본 포스트 제목
    source_url: str         # 원본 포스트 URL

# 쿠팡 검색 결과
class CoupangProduct:
    product_id: str
    product_name: str
    product_image: str
    product_url: str        # 쿠팡 상품 URL
    product_price: int
    affiliate_url: str      # 어필리에이션 URL (link.coupang.com)
    short_url: str          # IS.GD 단축 URL

# 블로그 요소
class BlogElement:
    type: str       # text | header | image | url | url_text | video
    content: Any    # 해당 타입의 콘텐츠
```

---

## 파이프라인 API

### SSE 전체 실행
```
GET /api/pipeline/run?days=2&max_posts=10&top_celebs=3&auto_publish=false
```
Server-Sent Events로 진행 상황 스트리밍.

### 개별 단계 (REST)
| 엔드포인트 | 설명 |
|---|---|
| `POST /api/pipeline/collect` | RSS 수집 |
| `POST /api/pipeline/analyze` | 연예인 분석 |
| `POST /api/pipeline/scrape` | 스크랩 + 추출 |
| `POST /api/pipeline/generate` | 블로그 생성 |

### 쿠팡
| 엔드포인트 | 설명 |
|---|---|
| `POST /api/coupang/search` | 키워드 상품 검색 |
| `GET /api/coupang/affiliate?product_url=` | 어필리에이션 URL 변환 |
| `POST /api/coupang/shorten` | IS.GD URL 단축 |

### 발행
```
POST /api/naver/write
{
  "title": "포스트 제목",
  "elements": [...],      # BlogElement[]
  "thumbnail_path": "...",
  "tags": [...]
}
```

---

## 쿠팡 파트너스 API

### HMAC-SHA256 인증
```python
datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
message = datetime_gmt + method + path + query_string
signature = hmac.new(secret_key.encode(), message.encode(), sha256).hexdigest()
Authorization = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_gmt}, signature={signature}"
```

### 제품 검색
```
GET /v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={keyword}&limit=10&imageSize=400x400
```
응답의 `data.productData[].productUrl` → 이미 어필리에이션 URL

### 어필리에이션 URL 변환
```
GET /v2/providers/affiliate_open_api/apis/openapi/links/products/byUrls?urls={encoded_url}
```
응답의 `data[0].landingUrl` → 어필리에이션 Landing URL

---

## 대가성 문구 (법적 의무)

쿠팡 파트너스 활동 시 **반드시** 삽입해야 하는 문구:

```
이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
```

- 블로그 포스트 **최상단** 또는 **최하단**에 반드시 삽입
- generator.py에서 자동으로 BlogElement에 포함
- naver_writer.py에서 text 요소로 발행

---

## 비디오 생성 (FFmpeg)

Blog 프로젝트(`Blog-main/VideoMaker.py`) 참조.

```python
# 이미지 목록 → 슬라이드쇼 MP4
ffmpeg -loop 1 -t 4 -i image0.jpg \
       -loop 1 -t 4 -i image1.jpg \
       -filter_complex "[0:v]fade=t=out:st=3:d=1[v0]; ..." \
       output.mp4
```

- 각 이미지 4초 표시
- Fade in/out 전환 효과 (1초)
- 네이버 블로그 video 요소로 삽입

---

## 네이버 블로그 자동 발행 (Selenium)

Blog 프로젝트(`Blog-main/NaverBlogWriter.py`) 참조.

### 요소 타입별 처리
| type | 처리 방식 |
|---|---|
| `text` | 15px 폰트, 백틱(`) → 굵게 |
| `header` | Ctrl+Alt+Q 헤더 단축키 |
| `image` | 클립보드 복사 → Ctrl+V |
| `url` | OG Link 카드 삽입 |
| `url_text` | "최저가 구매하러 가기" 38px 굵은 링크 버튼 |
| `video` | 동영상 업로드 버튼 → 파일 경로 입력 |

### 발행 프로세스
1. Chrome 실행 (기존 user-data-dir 활용 → 로그인 상태 유지)
2. 로그인 페이지 → ID/PW 클립보드 붙여넣기
3. `blog.naver.com/GoBlogWrite.naver` 접속
4. 제목 입력 → 썸네일 설정 → 요소 순서대로 삽입
5. 발행 → 공감 허용 체크 → 최종 확인

---

## 블로그 포스트 구조

```
[대가성 문구]
이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

[도입부]
{연예인명}의 최근 착용 아이템들을 소개합니다...

--- 아이템 반복 ---
[header] 아이템명 (카테고리)
[text]   상세 설명 (특징, 방송 착용 정보)
[url_text] affiliate_url  →  "최저가 구매하러 가기" 버튼
-----------------

[마무리]
다양한 아이템들을 소개해드렸습니다...

[해시태그]
#연예인명 #패션 #쿠팡 ...
```

---

## 설정 (backend/settings.json)

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

`GET /api/settings` — API 키/비번 마스킹  
`GET /api/settings/raw` — 원본 (내부용)  
`POST /api/settings` — 저장

---

## 실행 방법

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (개발)
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Frontend (프로덕션 빌드)
```bash
cd frontend
npm run build
# 빌드 결과물은 backend/static/ 으로 복사
# http://localhost:8000 에서 통합 서빙
```

---

## 개발 로드맵

### 완료 ✅
- FastAPI + React 풀스택 구조
- RSS 수집 + HTML 스크래핑 (Ordered Blocks)
- GPT 연예인 분석·추출·블로그 생성
- 쿠팡 파트너스 API 통합
- Selenium 네이버 블로그 자동 발행
- APScheduler 스케줄 관리
- SSE 실시간 파이프라인

### 진행 중 🔄
- generator.py → 구조화된 BlogElement[] 출력
- pipeline → 쿠팡 검색 단계 자동 통합
- 대가성 문구 자동 삽입
- VideoMaker 서비스 추가

### 예정 📋
- 스케줄 영속성 (SQLite JobStore)
- 발행 히스토리 저장
- 블로그 수집 대상 확장 (현재 15개)
- 연예인 필터링 퍼지 매칭
- 결과 JSON/CSV 내보내기

---

## 참조 프로젝트 (Blog-main/)

`Blog-main/` 디렉토리는 구 쿠팡 상품 리뷰 블로그 자동화 시스템.  
다음 구현을 참조:

| Blog-main 파일 | 참조 대상 |
|---|---|
| `NaverBlogWriter.py` | Selenium 발행 로직, 요소 삽입 방식 |
| `VideoMaker.py` | FFmpeg 슬라이드쇼 생성 |
| `CoupangSearcher.py` | HMAC 인증, 상품 검색 API |
| `ImageGenerator.py` | BiRefNet 배경 제거, 이미지 합성 |
| `GeminiDescGenerator.py` | 제품 설명 생성 프롬프트 |
| `template.txt` | 블로그 글 톤앤매너 (친근한 한국어, 이모티콘) |
