# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SME-Intelligence-AI — an AI system for SME (Small and Medium Enterprise) intelligence. The project is in early setup; no source code or configuration files exist yet beyond a `data/master/` directory for storing data assets.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # DART_API_KEY 입력
```

## Scripts

```bash
python scripts/fetch_corp_codes.py     # DART corp_code/ticker/market 매핑
python scripts/fetch_dart_financials.py  # 최근 3개년 재무 데이터 수집
python scripts/fetch_dart_filings.py     # 최근 1년 공시 목록 수집
python scripts/build_features.py         # 파생 지표 및 스코어 생성 (API 호출 없음)
python scripts/build_rag_docs.py         # 기업별 Markdown RAG 문서 생성 (API 호출 없음)

# 웹앱 실행 (web/ 디렉터리)
cd web && npm install && npm run dev     # http://localhost:3000 → /research
```

## Data layout

- `data/master/companies_master.csv` — 원본 기업 목록 (수동 관리)
- `data/master/companies_master_enriched.csv` — corp_code/ticker/market 매핑 결과
- `data/processed/financials/financials_3y.csv` — 최근 3개년 재무 데이터
- `data/processed/financials/filings_1y.csv` — 최근 1년 공시 목록
- `data/processed/features/company_features.csv` — 파생 지표 및 스코어 (build_features.py 출력)
- `data/processed/rag_docs/{ticker}.md` — 기업별 RAG 문서 (build_rag_docs.py 출력)
- `web/` — Next.js 14 웹앱 (App Router, TypeScript, Tailwind)
  - `web/src/lib/data.ts` — CSV 로더 (서버 전용, `../data` 참조)
  - `web/src/lib/interpret.ts` — rule-based 해석 문장 생성 (Python interpret 로직과 동일)
- `data/logs/` — 매핑/수집 실패 기업 로그

## Architecture

파이프라인 순서: `companies_master.csv` → `fetch_corp_codes.py` (DART ZIP 다운로드 → XML 파싱 → 정확/퍼지 매핑 → market 조회) → `companies_master_enriched.csv` → `fetch_dart_financials.py` (fnlttSinglAcntAll API, CFS→OFS 순 시도, 연도별 수집) → `financials_3y.csv`.
`DART_API_KEY`는 `.env`에서 `python-dotenv`로 로드. 금액 단위는 DART 원본 기준(원).
