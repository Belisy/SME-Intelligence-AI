"""
fetch_dart_filings.py
---------------------
DART OpenAPI(list.json)를 이용해
companies_master_enriched.csv의 enabled=1 기업에 대해
최근 1년 공시 목록을 수집합니다.

결과: data/processed/financials/filings_1y.csv
실패: data/logs/filings_missing.log
"""

import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "master" / "companies_master_enriched.csv"
OUTPUT_CSV = ROOT / "data" / "processed" / "financials" / "filings_1y.csv"
LOG_DIR = ROOT / "data" / "logs"
MISSING_LOG = LOG_DIR / "filings_missing.log"

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

missing_logger = logging.getLogger("filings_missing")
missing_logger.setLevel(logging.WARNING)
_mh = logging.FileHandler(MISSING_LOG, encoding="utf-8")
_mh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
missing_logger.addHandler(_mh)
missing_logger.propagate = False

# ---------------------------------------------------------------------------
# 수집 설정
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = 365          # 최근 N일치 공시 수집
PAGE_SIZE = 100              # DART API 최대 허용값
API_SLEEP_SEC = 0.25         # API 호출 간 대기 (초)
REQUEST_TIMEOUT = 20         # 요청 타임아웃 (초)

DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"

OUTPUT_COLUMNS = [
    "company_name", "ticker", "corp_code",
    "filing_date", "report_name", "title", "receipt_no",
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


def date_range() -> tuple[str, str]:
    """오늘 기준 LOOKBACK_DAYS 전 ~ 오늘을 YYYYMMDD 형식으로 반환."""
    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def fmt_filing_date(raw: str) -> str:
    """DART rcept_dt(YYYYMMDD) → YYYY-MM-DD."""
    raw = raw.strip()
    if len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


# ---------------------------------------------------------------------------
# DART API 호출
# ---------------------------------------------------------------------------
def fetch_filings_page(
    api_key: str,
    corp_code: str,
    bgn_de: str,
    end_de: str,
    page_no: int,
) -> tuple[list[dict], int]:
    """
    DART list.json 단일 페이지 호출.
    (items, total_count) 반환. 실패 시 ([], 0).
    """
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_no": page_no,
        "page_count": PAGE_SIZE,
        "sort": "date",
        "sort_mth": "desc",
    }
    try:
        resp = requests.get(DART_LIST_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(
            f"    API 요청 실패 (corp_code={corp_code}, page={page_no}): {exc}"
        )
        return [], 0

    status = data.get("status")
    if status == "013":
        # 조회된 데이터 없음 — 정상 케이스
        return [], 0
    if status != "000":
        logger.warning(
            f"    API 오류 (corp_code={corp_code}, page={page_no}): "
            f"status={status}, message={data.get('message')}"
        )
        return [], 0

    items = data.get("list", [])
    total_count = int(data.get("total_count", len(items)))
    return items, total_count


def fetch_all_filings(
    api_key: str,
    corp_code: str,
    bgn_de: str,
    end_de: str,
) -> list[dict]:
    """페이지네이션을 처리해 기간 내 전체 공시 목록을 반환."""
    all_items: list[dict] = []
    page_no = 1

    while True:
        time.sleep(API_SLEEP_SEC)
        items, total_count = fetch_filings_page(
            api_key, corp_code, bgn_de, end_de, page_no
        )
        all_items.extend(items)

        fetched_so_far = (page_no - 1) * PAGE_SIZE + len(items)
        if not items or fetched_so_far >= total_count:
            break
        page_no += 1

    return all_items


def parse_filing(item: dict, company_name: str, ticker: str, corp_code: str) -> dict:
    """DART list 항목 하나를 출력 컬럼 형식으로 변환."""
    report_nm = (item.get("report_nm") or "").strip()
    return {
        "company_name": company_name,
        "ticker": ticker,
        "corp_code": corp_code,
        "filing_date": fmt_filing_date(item.get("rcept_dt", "")),
        "report_name": report_nm,
        "title": report_nm,          # list API는 보고서명이 곧 공시명
        "receipt_no": (item.get("rcept_no") or "").strip(),
    }


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

    # 4. 수집 기간 결정
    bgn_de, end_de = date_range()
    logger.info(f"수집 기간: {bgn_de} ~ {end_de}")

    # 5. 기업별 공시 수집
    all_rows: list[dict] = []
    success_count, fail_count = 0, 0

    for _, company in target.iterrows():
        name = company["company_name"].strip()
        corp_code = company["corp_code"].strip()
        ticker = company.get("ticker", "").strip()
        logger.info(f"[{name}] corp_code={corp_code}")

        items = fetch_all_filings(api_key, corp_code, bgn_de, end_de)

        if not items:
            fail_count += 1
            missing_logger.warning(f"공시 없음: {name} (corp_code={corp_code})")
            logger.warning(f"  → 공시 없음, missing log에 기록")
            continue

        rows = [parse_filing(item, name, ticker, corp_code) for item in items]
        all_rows.extend(rows)
        success_count += 1
        logger.info(f"  공시 {len(rows)}건 수집")

    # 6. 중복 제거 (receipt_no 기준)
    if all_rows:
        result_df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
        before = len(result_df)
        result_df.drop_duplicates(subset=["receipt_no"], inplace=True)
        result_df.sort_values(["company_name", "filing_date"], ascending=[True, False], inplace=True)
        result_df.reset_index(drop=True, inplace=True)
        after = len(result_df)
        if before != after:
            logger.info(f"중복 제거: {before - after}건 제거 → {after}건")

        result_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"저장 완료: {OUTPUT_CSV}  ({len(result_df)}행)")
    else:
        logger.warning("수집된 공시가 없습니다.")

    logger.info(f"결과 요약 — 기업 성공: {success_count}, 기업 실패: {fail_count}")
    if fail_count:
        logger.info(f"실패 목록: {MISSING_LOG}")


if __name__ == "__main__":
    main()
