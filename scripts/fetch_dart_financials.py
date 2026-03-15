"""
fetch_dart_financials.py
------------------------
DART OpenAPI(fnlttSinglAcntAll)를 이용해
companies_master_enriched.csv의 enabled=1 기업에 대해
최근 3개년 주요 재무 항목을 수집합니다.

연결재무제표 우선, 없으면 개별재무제표를 사용합니다.
결과: data/processed/financials/financials_3y.csv
실패: data/logs/financials_missing.log
"""

import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "master" / "companies_master_enriched.csv"
OUTPUT_CSV = ROOT / "data" / "processed" / "financials" / "financials_3y.csv"
LOG_DIR = ROOT / "data" / "logs"
MISSING_LOG = LOG_DIR / "financials_missing.log"

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

missing_logger = logging.getLogger("financials_missing")
missing_logger.setLevel(logging.WARNING)
_mh = logging.FileHandler(MISSING_LOG, encoding="utf-8")
_mh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
missing_logger.addHandler(_mh)
missing_logger.propagate = False

# ---------------------------------------------------------------------------
# 수집 설정
# ---------------------------------------------------------------------------
N_YEARS = 3                 # 수집할 연도 수
ANNUAL_REPORT_CODE = "11011"  # 사업보고서
API_SLEEP_SEC = 0.25        # API 호출 간 대기 (초)
REQUEST_TIMEOUT = 20        # 요청 타임아웃 (초)

DART_FINANCIAL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

# 재무제표 구분: 연결 우선, 실패 시 개별
FS_PRIORITY = [
    ("CFS", "연결"),
    ("OFS", "개별"),
]

# 계정명 → 내부 컬럼명 매핑 (첫 번째 매칭 기준)
ACCOUNT_MAP: dict[str, list[str]] = {
    "revenue": [
        "매출액", "영업수익", "수익(매출액)", "매출",
        "영업수익(매출액)", "수익", "매출액(영업수익)",
    ],
    "operating_income": [
        "영업이익", "영업이익(손실)", "영업손실",
    ],
    "net_income": [
        "당기순이익", "당기순이익(손실)", "당기순손실",
        "분기순이익", "연결당기순이익", "당기순이익(당기순손실)",
    ],
    "total_assets": ["자산총계"],
    "total_liabilities": ["부채총계"],
    "total_equity": ["자본총계"],
}

OUTPUT_COLUMNS = [
    "company_name", "ticker", "corp_code",
    "year", "fs_type",
    "revenue", "operating_income", "net_income",
    "total_assets", "total_liabilities", "total_equity",
]


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("DART_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "DART_API_KEY가 .env 파일에 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env에 DART_API_KEY=<키값> 형태로 추가하세요."
        )
    return key


def target_years(n: int = N_YEARS) -> list[int]:
    """
    현재 날짜 기준으로 수집할 연도 목록을 반환합니다.
    3월 말 이전이면 전년도 사업보고서가 미제출 가능성이 있으므로
    한 해 더 앞당겨 시작합니다.
    """
    today = date.today()
    # 사업보고서 제출 마감: 보통 3월 31일
    # 3월 31일 이전이면 직전년도 보고서가 아직 미확정일 수 있음
    start_year = today.year - 1 if today.month > 3 else today.year - 2
    return [start_year - i for i in range(n)]


def parse_amount(value: str) -> float | None:
    """DART 금액 문자열(쉼표 포함, 음수 가능)을 float으로 변환."""
    if not value or value.strip() in ("", "-", "―"):
        return None
    try:
        return float(value.replace(",", "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# DART API 호출
# ---------------------------------------------------------------------------
def fetch_financial_statements(
    api_key: str,
    corp_code: str,
    bsns_year: int,
    fs_div: str,
) -> list[dict] | None:
    """
    DART fnlttSinglAcntAll API 호출.
    성공 시 list[dict] 반환, 실패/데이터 없음 시 None.
    """
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(bsns_year),
        "reprt_code": ANNUAL_REPORT_CODE,
        "fs_div": fs_div,
    }
    try:
        resp = requests.get(DART_FINANCIAL_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"    API 요청 실패 (corp_code={corp_code}, {bsns_year}, {fs_div}): {exc}")
        return None

    if data.get("status") != "000":
        # 013: 조회된 데이터가 없음 — 정상 케이스
        if data.get("status") != "013":
            logger.warning(
                f"    API 오류 (corp_code={corp_code}, {bsns_year}, {fs_div}): "
                f"status={data.get('status')}, message={data.get('message')}"
            )
        return None

    return data.get("list", [])


def extract_accounts(items: list[dict]) -> dict[str, float | None]:
    """
    API 응답 리스트에서 ACCOUNT_MAP 기준으로 계정 금액을 추출합니다.
    account_nm 우선 순위에 따라 첫 번째 매칭 계정의 thstrm_amount를 사용합니다.
    """
    # account_nm → thstrm_amount 인덱스 구성
    nm_to_amount: dict[str, str] = {}
    for item in items:
        nm = (item.get("account_nm") or "").strip()
        amt = item.get("thstrm_amount") or item.get("thstrm_add_amount") or ""
        if nm and nm not in nm_to_amount:
            nm_to_amount[nm] = amt

    result: dict[str, float | None] = {}
    for col, candidates in ACCOUNT_MAP.items():
        value = None
        for candidate in candidates:
            if candidate in nm_to_amount:
                value = parse_amount(nm_to_amount[candidate])
                break
        result[col] = value
    return result


def fetch_one_year(
    api_key: str,
    corp_code: str,
    year: int,
) -> tuple[dict[str, float | None], str] | None:
    """
    단일 연도의 재무 데이터를 수집합니다.
    연결 → 개별 순으로 시도하며, 성공 시 (accounts, fs_type) 반환.
    두 방식 모두 실패하면 None 반환.
    """
    for fs_div, fs_label in FS_PRIORITY:
        time.sleep(API_SLEEP_SEC)
        items = fetch_financial_statements(api_key, corp_code, year, fs_div)
        if items:
            accounts = extract_accounts(items)
            # 핵심 항목(revenue, total_assets) 중 하나라도 있으면 유효한 데이터로 간주
            if accounts.get("revenue") is not None or accounts.get("total_assets") is not None:
                return accounts, fs_label
    return None


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    # 1. API 키 로드
    api_key = load_api_key()

    # 2. 입력 CSV 로드
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {INPUT_CSV}")
    companies = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    logger.info(f"전체 기업 수: {len(companies)}")

    # 3. 처리 대상 필터링: enabled=1 AND corp_code 존재
    target = companies[
        (companies["enabled"].str.strip() == "1")
        & (companies["corp_code"].str.strip() != "")
    ].copy()
    logger.info(f"처리 대상 기업 수: {len(target)} (enabled=1, corp_code 있음)")

    # 4. 수집 연도 결정
    years = target_years()
    logger.info(f"수집 연도: {years}")

    # 5. 재무 데이터 수집
    rows: list[dict] = []
    success_count, fail_count = 0, 0

    for _, company in target.iterrows():
        name = company["company_name"].strip()
        corp_code = company["corp_code"].strip()
        ticker = company.get("ticker", "").strip()
        logger.info(f"[{name}] corp_code={corp_code}")

        year_success = 0
        for year in years:
            result = fetch_one_year(api_key, corp_code, year)
            if result is None:
                logger.warning(f"  {year}년 데이터 없음")
                continue

            accounts, fs_type = result
            row = {
                "company_name": name,
                "ticker": ticker,
                "corp_code": corp_code,
                "year": year,
                "fs_type": fs_type,
                **accounts,
            }
            rows.append(row)
            year_success += 1
            logger.info(
                f"  {year}년 [{fs_type}] revenue={accounts.get('revenue')}, "
                f"total_assets={accounts.get('total_assets')}"
            )

        if year_success == 0:
            fail_count += 1
            missing_logger.warning(f"전 연도 수집 실패: {name} (corp_code={corp_code})")
            logger.warning(f"  → 전 연도 수집 실패, missing log에 기록")
        else:
            success_count += 1

    # 6. 결과 저장
    if rows:
        result_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
        result_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"저장 완료: {OUTPUT_CSV}  ({len(result_df)}행)")
    else:
        logger.warning("수집된 데이터가 없습니다.")

    logger.info(f"결과 요약 — 기업 성공: {success_count}, 기업 실패: {fail_count}")
    if fail_count:
        logger.info(f"실패 목록: {MISSING_LOG}")


if __name__ == "__main__":
    main()
