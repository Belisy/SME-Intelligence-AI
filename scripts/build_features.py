"""
build_features.py
-----------------
financials_3y.csv, filings_1y.csv, companies_master_enriched.csv를 결합해
기업별 파생 지표와 스코어(company_features.csv)를 생성합니다.

결과: data/processed/features/company_features.csv
로그: data/logs/features_build.log
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
FINANCIALS_CSV = ROOT / "data" / "processed" / "financials" / "financials_3y.csv"
FILINGS_CSV    = ROOT / "data" / "processed" / "financials" / "filings_1y.csv"
MASTER_CSV     = ROOT / "data" / "master" / "companies_master_enriched.csv"
OUTPUT_CSV     = ROOT / "data" / "processed" / "features" / "company_features.csv"
LOG_DIR        = ROOT / "data" / "logs"
BUILD_LOG      = LOG_DIR / "features_build.log"

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BUILD_LOG, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 출력 컬럼 순서
# ---------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    "company_name", "ticker", "corp_code",
    "sector", "subsector", "market",
    "revenue_latest", "revenue_prev", "revenue_cagr_3y",
    "operating_income_latest", "operating_margin_latest",
    "total_assets_latest", "total_liabilities_latest", "total_equity_latest",
    "debt_ratio_latest",
    "disclosure_count_1y",
    "growth_score", "risk_score",
]

# ---------------------------------------------------------------------------
# 파생 지표 계산 함수
# ---------------------------------------------------------------------------

def calc_cagr(latest: float | None, prev: float | None, n_years: int = 2) -> float | None:
    """
    CAGR = (latest / prev)^(1/n_years) - 1
    latest 또는 prev가 null이거나 prev <= 0이면 None.
    """
    if pd.isna(latest) or pd.isna(prev) or prev <= 0:
        return None
    try:
        return (latest / prev) ** (1 / n_years) - 1
    except (ZeroDivisionError, ValueError):
        return None


def calc_margin(operating_income: float | None, revenue: float | None) -> float | None:
    """영업이익률 = operating_income / revenue. revenue <= 0 이면 None."""
    if pd.isna(operating_income) or pd.isna(revenue) or revenue <= 0:
        return None
    return operating_income / revenue


def calc_debt_ratio(liabilities: float | None, equity: float | None) -> float | None:
    """부채비율 = liabilities / equity * 100. equity <= 0 이면 None."""
    if pd.isna(liabilities) or pd.isna(equity) or equity <= 0:
        return None
    return liabilities / equity * 100


# ---------------------------------------------------------------------------
# 점수 산출 함수 (rule-based, 0~100)
# ---------------------------------------------------------------------------
# growth_score 기준:
#   revenue_cagr_3y  >= 20%  → +60점
#                   >= 10%  → +40점
#                   >=  0%  → +20점
#                    < 0% 또는 null → +0점
#   operating_margin_latest >= 15% → +40점
#                           >=  8% → +25점
#                           >=  3% → +10점
#                            <  3% 또는 null → +0점
#   합산 후 min(score, 100)
#
# risk_score 기준:
#   debt_ratio_latest >= 300% → +60점
#                     >= 200% → +40점
#                     >= 100% → +20점
#                      < 100% 또는 null → +0점
#   disclosure_count_1y >= 100 → +40점
#                        >=  50 → +25점
#                        >=  20 → +10점
#                         <  20 → +0점
#   합산 후 min(score, 100)

def _step(value: float | None, thresholds: list[tuple[float, int]]) -> int:
    """
    value를 내림차순 임계값 목록과 비교해 첫 번째 충족하는 점수를 반환.
    thresholds: [(임계값, 점수), ...] — 높은 임계값부터 정렬.
    """
    if value is None or pd.isna(value):
        return 0
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return 0


def calc_growth_score(
    revenue_cagr_3y: float | None,
    operating_margin_latest: float | None,
) -> int:
    cagr_score = _step(
        revenue_cagr_3y,
        [(0.20, 60), (0.10, 40), (0.00, 20)],
    )
    margin_score = _step(
        operating_margin_latest,
        [(0.15, 40), (0.08, 25), (0.03, 10)],
    )
    return min(cagr_score + margin_score, 100)


def calc_risk_score(
    debt_ratio_latest: float | None,
    disclosure_count_1y: int | None,
) -> int:
    debt_score = _step(
        debt_ratio_latest,
        [(300, 60), (200, 40), (100, 20)],
    )
    disc_score = _step(
        disclosure_count_1y,
        [(100, 40), (50, 25), (20, 10)],
    )
    return min(debt_score + disc_score, 100)


# ---------------------------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------------------------

def _normalize_id_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    지정 컬럼을 문자열로 통일합니다.
    - NaN → 빈 문자열 (앞자리 0 보존, "nan" 문자열 방지)
    - 앞뒤 공백 제거
    """
    for col in cols:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), other="")
            df[col] = df[col].astype(str).str.strip()
            # astype(str)이 NaN을 "nan"으로 바꾸는 경우 재처리
            df[col] = df[col].replace("nan", "")
    return df


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in (FINANCIALS_CSV, FILINGS_CSV, MASTER_CSV):
        if not path.exists():
            raise FileNotFoundError(f"입력 파일이 없습니다: {path}")

    # corp_code, ticker는 read_csv 시점에 str로 지정해 앞자리 0 보존
    ID_COLS = ["corp_code", "ticker"]
    financials = pd.read_csv(FINANCIALS_CSV, dtype={c: str for c in ID_COLS})
    filings    = pd.read_csv(FILINGS_CSV,    dtype=str)
    master     = pd.read_csv(MASTER_CSV,     dtype=str).fillna("")

    # 후처리: 공백 제거 및 "nan" 문자열 방지
    financials = _normalize_id_cols(financials, ID_COLS)
    filings    = _normalize_id_cols(filings,    ID_COLS)
    master     = _normalize_id_cols(master,     ID_COLS)

    # 숫자형 강제 변환 (API 저장 값이 문자열로 읽힐 경우 대비)
    numeric_cols = [
        "revenue", "operating_income", "net_income",
        "total_assets", "total_liabilities", "total_equity",
    ]
    for col in numeric_cols:
        if col in financials.columns:
            financials[col] = pd.to_numeric(financials[col], errors="coerce")

    financials["year"] = pd.to_numeric(financials["year"], errors="coerce")

    # merge 전 dtype 확인 로그
    for name, df in [("financials", financials), ("filings", filings), ("master", master)]:
        for col in ID_COLS:
            if col in df.columns:
                logger.info(f"  [{name}] {col} dtype={df[col].dtype}, sample={df[col].iloc[0] if len(df) else 'N/A'}")

    logger.info(
        f"로드 완료 — financials: {len(financials)}행, "
        f"filings: {len(filings)}행, master: {len(master)}행"
    )
    return financials, filings, master


# ---------------------------------------------------------------------------
# 특징 생성
# ---------------------------------------------------------------------------

def build_financials_features(financials: pd.DataFrame) -> pd.DataFrame:
    """
    재무 데이터에서 기업별 latest / prev / 파생 지표를 추출합니다.
    corp_code 기준으로 집계합니다.
    """
    fin = financials.dropna(subset=["corp_code", "year"]).copy()
    fin["year"] = fin["year"].astype(int)
    fin.sort_values(["corp_code", "year"], inplace=True)

    rows = []
    for corp_code, grp in fin.groupby("corp_code"):
        latest_row = grp.iloc[-1]   # 가장 최근 연도
        oldest_row = grp.iloc[0]    # 가장 오래된 연도

        revenue_latest = latest_row.get("revenue")
        revenue_prev   = oldest_row.get("revenue")
        n_years        = latest_row["year"] - oldest_row["year"]
        # 연도 차이가 0이면 CAGR 계산 불가
        cagr = calc_cagr(revenue_latest, revenue_prev, n_years) if n_years > 0 else None

        op_income_latest = latest_row.get("operating_income")
        margin           = calc_margin(op_income_latest, revenue_latest)

        total_assets      = latest_row.get("total_assets")
        total_liabilities = latest_row.get("total_liabilities")
        total_equity      = latest_row.get("total_equity")
        debt_ratio        = calc_debt_ratio(total_liabilities, total_equity)

        rows.append({
            "corp_code":               corp_code,
            "company_name":            latest_row.get("company_name", ""),
            "ticker":                  latest_row.get("ticker", ""),
            "revenue_latest":          revenue_latest,
            "revenue_prev":            revenue_prev,
            "revenue_cagr_3y":         cagr,
            "operating_income_latest": op_income_latest,
            "operating_margin_latest": margin,
            "total_assets_latest":     total_assets,
            "total_liabilities_latest": total_liabilities,
            "total_equity_latest":     total_equity,
            "debt_ratio_latest":       debt_ratio,
        })

    result = pd.DataFrame(rows)
    logger.info(f"재무 특징 생성 완료: {len(result)}개 기업")
    return result


def build_filing_features(filings: pd.DataFrame) -> pd.DataFrame:
    """filings_1y.csv에서 기업별 공시 건수를 집계합니다."""
    counts = (
        filings.dropna(subset=["corp_code"])
        .groupby("corp_code")["receipt_no"]
        .nunique()
        .reset_index()
        .rename(columns={"receipt_no": "disclosure_count_1y"})
    )
    logger.info(f"공시 건수 집계 완료: {len(counts)}개 기업")
    return counts


def attach_master_info(features: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """master CSV에서 sector, subsector, market 컬럼을 join합니다."""
    meta = master[["corp_code", "sector", "subsector", "market"]].copy()
    merged = features.merge(meta, on="corp_code", how="left")
    logger.info(f"마스터 정보 결합 완료: {len(merged)}행")
    return merged


def apply_scores(features: pd.DataFrame) -> pd.DataFrame:
    """growth_score, risk_score를 행별로 계산해 컬럼을 추가합니다."""
    features["growth_score"] = features.apply(
        lambda r: calc_growth_score(
            r.get("revenue_cagr_3y"),
            r.get("operating_margin_latest"),
        ),
        axis=1,
    )
    features["risk_score"] = features.apply(
        lambda r: calc_risk_score(
            r.get("debt_ratio_latest"),
            r.get("disclosure_count_1y"),
        ),
        axis=1,
    )
    return features


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== build_features.py 시작 ===")

    # 1. 데이터 로드
    financials, filings, master = load_inputs()

    # 2. 재무 특징 생성
    fin_features = build_financials_features(financials)

    # 3. 공시 건수 집계
    filing_features = build_filing_features(filings)

    # 4. 결합
    features = fin_features.merge(filing_features, on="corp_code", how="left")
    features["disclosure_count_1y"] = (
        features["disclosure_count_1y"].fillna(0).astype(int)
    )

    # 5. 마스터 정보 (sector, subsector, market) 결합
    features = attach_master_info(features, master)

    # 6. 점수 산출
    features = apply_scores(features)

    # 7. 출력 컬럼 정렬 및 저장
    for col in OUTPUT_COLUMNS:
        if col not in features.columns:
            features[col] = np.nan

    result = features[OUTPUT_COLUMNS].copy()
    result.sort_values("company_name", inplace=True)
    result.reset_index(drop=True, inplace=True)

    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"저장 완료: {OUTPUT_CSV}  ({len(result)}행, {len(result.columns)}컬럼)")

    # 8. 요약 로그
    null_summary = result[OUTPUT_COLUMNS[6:]].isna().sum()
    missing_cols = null_summary[null_summary > 0]
    if not missing_cols.empty:
        logger.info("null 값이 있는 컬럼:")
        for col, cnt in missing_cols.items():
            logger.info(f"  {col}: {cnt}개 기업 null")

    logger.info("=== build_features.py 완료 ===")


if __name__ == "__main__":
    main()
