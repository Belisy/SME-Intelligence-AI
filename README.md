# SME Intelligence AI

## 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. DART API 키 설정

[DART OpenAPI](https://opendart.fss.or.kr/)에서 API 키를 발급받은 뒤,
프로젝트 루트에 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
# .env 파일을 열고 DART_API_KEY 값을 입력
```

`.env` 형식:
```
DART_API_KEY=발급받은키값
```

---

## scripts/fetch_corp_codes.py

`data/master/companies_master.csv`의 기업명을 기준으로 DART에서
`corp_code`, `ticker`, `market`을 자동 매핑합니다.

### 실행

```bash
python scripts/fetch_corp_codes.py
```

### 출력

| 경로 | 설명 |
|---|---|
| `data/master/companies_master_enriched.csv` | 매핑 결과가 추가된 CSV |
| `data/logs/missing_companies.log` | 매핑 실패 기업 목록 |

### 매핑 로직

1. DART OpenAPI에서 전체 상장사 코드 목록을 ZIP으로 다운로드
2. 기업명 **정확 매핑** 시도
3. 실패 시 **퍼지 매핑**(유사도 0.8 이상) 시도
4. 매핑 성공 기업은 개별 `company.json` API를 추가 호출해 시장 구분(KOSPI/KOSDAQ 등) 확인
5. 원본 파일은 유지하고 결과를 별도 파일로 저장

### 주의사항

- `corp_code`가 이미 채워진 행은 스킵됩니다.
- 퍼지 매핑은 `difflib.get_close_matches`를 사용하며, 기업명이 크게 다를 경우 오매핑될 수 있습니다. 결과 CSV를 검토 후 수동 수정하세요.
- DART API 호출은 기업 수만큼 발생합니다 (시장 조회). 호출 제한에 주의하세요.

---

## scripts/fetch_dart_financials.py

`companies_master_enriched.csv`의 `enabled=1` 기업을 대상으로
DART에서 최근 3개년 주요 재무 항목을 수집합니다.

### 실행 순서

`fetch_corp_codes.py` 실행 후 enriched CSV가 준비된 상태에서 실행합니다.

```bash
python scripts/fetch_dart_financials.py
```

### 출력

| 경로 | 설명 |
|---|---|
| `data/processed/financials/financials_3y.csv` | 3개년 재무 데이터 |
| `data/logs/financials_missing.log` | 전 연도 수집 실패 기업 목록 |

### 수집 항목

| 컬럼 | 설명 |
|---|---|
| `revenue` | 매출액 |
| `operating_income` | 영업이익 |
| `net_income` | 당기순이익 |
| `total_assets` | 자산총계 |
| `total_liabilities` | 부채총계 |
| `total_equity` | 자본총계 |

### 수집 로직

1. `enabled=1`이고 `corp_code`가 있는 기업만 처리
2. 현재 날짜 기준으로 최근 3개년 자동 계산 (3월 이전이면 전전년도부터 시작)
3. 연도별로 **연결재무제표(CFS)** 우선 조회, 없으면 **개별재무제표(OFS)** 사용
4. 금액 단위는 DART 원본 기준 (원)
5. API 호출 간 0.25초 대기 (호출량 제한 방지)

---

## scripts/fetch_dart_filings.py

`companies_master_enriched.csv`의 `enabled=1` 기업을 대상으로
DART에서 최근 1년 공시 목록을 수집합니다.

### 실행

```bash
python scripts/fetch_dart_filings.py
```

### 출력

| 경로 | 설명 |
|---|---|
| `data/processed/financials/filings_1y.csv` | 최근 1년 공시 목록 |
| `data/logs/filings_missing.log` | 공시 없음/실패 기업 목록 |

### 출력 컬럼

| 컬럼 | 설명 |
|---|---|
| `filing_date` | 공시 접수일 (YYYY-MM-DD) |
| `report_name` | DART 보고서명 |
| `title` | 공시명 (보고서명과 동일) |
| `receipt_no` | DART 접수번호 (중복 제거 기준) |

### 수집 로직

1. `enabled=1`이고 `corp_code`가 있는 기업만 처리
2. 오늘 기준 365일 전 ~ 오늘 범위 자동 계산
3. 페이지네이션 처리 (DART 최대 100건/페이지)
4. `receipt_no` 기준 중복 제거 후 저장
5. API 호출 간 0.25초 대기 (호출량 제한 방지)

---

## scripts/build_features.py

`financials_3y.csv`, `filings_1y.csv`, `companies_master_enriched.csv`를 결합해
기업별 파생 지표와 스코어를 생성합니다. DART API 호출 없음.

### 실행

```bash
python scripts/build_features.py
```

### 출력

| 경로 | 설명 |
|---|---|
| `data/processed/features/company_features.csv` | 기업별 피처 및 스코어 |
| `data/logs/features_build.log` | 빌드 로그 |

### 파생 지표 계산 규칙

| 컬럼 | 계산 방법 |
|---|---|
| `revenue_latest` | 최신 연도 매출액 |
| `revenue_prev` | 가장 오래된 연도 매출액 |
| `revenue_cagr_3y` | `(revenue_latest / revenue_prev)^(1/n) - 1`, n=연도 차이 |
| `operating_margin_latest` | `operating_income_latest / revenue_latest` |
| `debt_ratio_latest` | `total_liabilities_latest / total_equity_latest × 100` (equity ≤ 0이면 null) |
| `disclosure_count_1y` | `filings_1y.csv`의 기업별 고유 `receipt_no` 수 |

### 스코어 기준

**growth_score (0~100, 높을수록 성장성 우수)**

| 항목 | 조건 | 점수 |
|---|---|---|
| `revenue_cagr_3y` | ≥ 20% | +60 |
| | ≥ 10% | +40 |
| | ≥ 0% | +20 |
| | < 0% 또는 null | +0 |
| `operating_margin_latest` | ≥ 15% | +40 |
| | ≥ 8% | +25 |
| | ≥ 3% | +10 |
| | < 3% 또는 null | +0 |

**risk_score (0~100, 높을수록 재무 위험 높음)**

| 항목 | 조건 | 점수 |
|---|---|---|
| `debt_ratio_latest` | ≥ 300% | +60 |
| | ≥ 200% | +40 |
| | ≥ 100% | +20 |
| | < 100% 또는 null | +0 |
| `disclosure_count_1y` | ≥ 100건 | +40 |
| | ≥ 50건 | +25 |
| | ≥ 20건 | +10 |
| | < 20건 | +0 |

---

## scripts/build_rag_docs.py

`company_features.csv`, `financials_3y.csv`, `filings_1y.csv`를 결합해
기업별 RAG 문서(Markdown)를 생성합니다. DART API 호출 없음.

### 실행

```bash
python scripts/build_rag_docs.py
```

### 출력

| 경로 | 설명 |
|---|---|
| `data/processed/rag_docs/{ticker}.md` | 기업별 Markdown 문서 |
| `data/logs/rag_docs_build.log` | 빌드 로그 |

### 문서 구조

각 `{ticker}.md`는 아래 섹션으로 구성됩니다.

1. **기본 정보** — ticker, corp_code, 섹터, 시장
2. **최근 3개년 재무 요약** — 연도별 매출·영업이익·자산·부채·자본 (억원 단위)
3. **핵심 지표 요약** — CAGR, 영업이익률, 부채비율, 공시 건수, 스코어
4. **최근 1년 공시 요약** — 최신 10건, `[날짜] 보고서명 (접수번호)` 형식
5. **핵심 해석 요약** — rule-based 문장 3~5개 (LLM 미사용)
6. **출처** — 원본 CSV 경로
