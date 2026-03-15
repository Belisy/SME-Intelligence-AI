"""
fetch_corp_codes.py
-------------------
DART OpenAPI를 이용해 companies_master.csv의 각 기업에
corp_code, ticker, market을 자동 매핑하고
data/master/companies_master_enriched.csv 로 저장합니다.

매핑 실패 기업은 data/logs/missing_companies.log 에 기록됩니다.
"""

import io
import logging
import os
import sys
import zipfile
from difflib import get_close_matches
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "master"
LOG_DIR = ROOT / "data" / "logs"
INPUT_CSV = DATA_DIR / "companies_master.csv"
OUTPUT_CSV = DATA_DIR / "companies_master_enriched.csv"
MISSING_LOG = LOG_DIR / "missing_companies.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

missing_logger = logging.getLogger("missing")
missing_logger.setLevel(logging.WARNING)
missing_handler = logging.FileHandler(MISSING_LOG, encoding="utf-8")
missing_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
missing_logger.addHandler(missing_handler)
missing_logger.propagate = False

# ---------------------------------------------------------------------------
# DART API
# ---------------------------------------------------------------------------
DART_CORPCODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_COMPANY_URL = "https://opendart.fss.or.kr/api/company.json"

CORP_CLS_MAP = {
    "Y": "KOSPI",
    "K": "KOSDAQ",
    "N": "KONEX",
    "E": "기타",
}


def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("DART_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "DART_API_KEY가 .env 파일에 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env에 DART_API_KEY=<키값> 형태로 추가하세요."
        )
    return key


def fetch_dart_corp_list(api_key: str) -> pd.DataFrame:
    """DART에서 전체 기업 코드 목록을 내려받아 DataFrame으로 반환."""
    logger.info("DART 기업 코드 목록 다운로드 중...")
    resp = requests.get(DART_CORPCODE_URL, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
        xml_bytes = zf.read(xml_name)

    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.iter("list"):
        rows.append(
            {
                "corp_code": (item.findtext("corp_code") or "").strip(),
                "corp_name": (item.findtext("corp_name") or "").strip(),
                "stock_code": (item.findtext("stock_code") or "").strip(),
            }
        )

    df = pd.DataFrame(rows)
    # 상장 종목만 (stock_code가 있는 것)
    listed = df[df["stock_code"].str.len() > 0].copy()
    listed.reset_index(drop=True, inplace=True)
    logger.info(f"상장 기업 {len(listed):,}개 로드 완료")
    return listed


def fetch_market(api_key: str, corp_code: str) -> str:
    """단일 기업의 시장 구분(KOSPI/KOSDAQ 등)을 DART에서 조회."""
    try:
        resp = requests.get(
            DART_COMPANY_URL,
            params={"crtfc_key": api_key, "corp_code": corp_code},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "000":
            cls_code = data.get("corp_cls", "")
            return CORP_CLS_MAP.get(cls_code, cls_code)
    except Exception as exc:
        logger.warning(f"시장 조회 실패 (corp_code={corp_code}): {exc}")
    return ""


def match_company(
    name: str,
    dart_df: pd.DataFrame,
    name_to_idx: dict[str, int],
    fuzzy_cutoff: float = 0.8,
) -> dict | None:
    """
    정확 매핑 → 퍼지 매핑 순으로 시도.
    매칭 결과 dict(corp_code, ticker) 또는 None 반환.
    """
    # 1) 정확 매핑
    if name in name_to_idx:
        row = dart_df.iloc[name_to_idx[name]]
        return {"corp_code": row["corp_code"], "ticker": row["stock_code"]}

    # 2) 퍼지 매핑 (difflib)
    candidates = get_close_matches(
        name, name_to_idx.keys(), n=1, cutoff=fuzzy_cutoff
    )
    if candidates:
        matched_name = candidates[0]
        logger.info(f"  퍼지 매칭: '{name}' → '{matched_name}'")
        row = dart_df.iloc[name_to_idx[matched_name]]
        return {"corp_code": row["corp_code"], "ticker": row["stock_code"]}

    return None


def main() -> None:
    # 1. API 키 로드
    api_key = load_api_key()

    # 2. 입력 CSV 로드
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {INPUT_CSV}")
    companies = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    logger.info(f"입력 기업 수: {len(companies)}")

    # 3. DART 기업 목록 다운로드
    dart_df = fetch_dart_corp_list(api_key)
    name_to_idx: dict[str, int] = {
        row["corp_name"]: i for i, row in dart_df.iterrows()
    }

    # 4. 매핑 수행
    success, failed = 0, 0
    for idx, row in companies.iterrows():
        name = str(row["company_name"]).strip()

        # 이미 corp_code가 채워진 경우 스킵
        if row.get("corp_code", "").strip():
            logger.info(f"  스킵 (이미 매핑됨): {name}")
            success += 1
            continue

        match = match_company(name, dart_df, name_to_idx)
        if match:
            companies.at[idx, "corp_code"] = match["corp_code"]
            companies.at[idx, "ticker"] = match["ticker"]

            # 시장 구분 조회
            market = fetch_market(api_key, match["corp_code"])
            companies.at[idx, "market"] = market

            logger.info(
                f"  매핑 성공: {name} → corp_code={match['corp_code']}, "
                f"ticker={match['ticker']}, market={market}"
            )
            success += 1
        else:
            failed += 1
            missing_logger.warning(f"매핑 실패: {name}")
            logger.warning(f"  매핑 실패: {name}")

    # 5. 결과 저장
    companies.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"저장 완료: {OUTPUT_CSV}")
    logger.info(f"결과 요약 — 성공: {success}, 실패: {failed}")
    if failed:
        logger.info(f"매핑 실패 목록: {MISSING_LOG}")


if __name__ == "__main__":
    main()
