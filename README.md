---
title: Bloggers
emoji: 🌟
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# 셀럽 아이템 블로그 생성기

네이버 블로거들의 최신 게시글을 분석하여 트렌딩 연예인을 찾고, 자동으로 블로그 포스트를 생성합니다.

## 사용법
1. OpenAI API 키 입력
2. 수집 기간 설정 (최근 N일)
3. 🚀 버튼 클릭

## API
- `GET /api/health` — 상태 확인
- `POST /api/collect` — RSS 게시글 수집
- `POST /api/analyze` — 트렌딩 연예인 추출
- `POST /api/items` — 아이템 크롤링
- `POST /api/generate` — 블로그 포스트 생성
- `GET /api/pipeline?days=2&openai_api_key=sk-...` — SSE 전체 파이프라인
