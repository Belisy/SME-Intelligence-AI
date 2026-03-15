"""
build_rag_docs.py
-----------------
기업별 RAG(Retrieval-Augmented Generation) 문서를 Markdown으로 생성합니다.

입력:
  data/master/companies_master_enriched.csv
  data/processed/financials/financials_3y.csv
  data/processed/financials/filings_1y.csv
  data/processed/features/company_features.csv

출력: data/processed/rag_docs/{ticker}.md
로그: data/logs/rag_docs_build.log
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parent.parent
MASTER_CSV  = ROOT / "data" / "master"      / "companies_master_enriched.csv"
FIN_CSV     = ROOT / "data" / "processed"  / "financials" / "financials_3y.csv"
FILINGS_CSV = ROOT / "data" / "processed"  / "financials" / "filings_1y.csv"
FEAT_CSV    = ROOT / "data" / "processed"  / "features"   / "company_features.csv"
OUT_DIR     = ROOT / "data" / "processed"  / "rag_docs"
LOG_DIR     = ROOT / "data" / "logs"
BUILD_LOG   = LOG_DIR / "rag_docs_build.log"

OUT_DIR.mkdir(parents=True, exist_ok=True)
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
# 설정 상수
# ---------------------------------------------------------------------------
MAX_FILINGS_IN_DOC = 10          # 문서에 포함할 최대 공시 건수
OKUEON             = 1e8         # 억원 단위 변환 기준 (1억 = 100,000,000)

# 핵심 지표 해석 임계값
CAGR_HIGH   = 0.10   # 매출 성장률 "높음" 기준 (10%)
MARGIN_HIGH = 0.10   # 영업이익률 "높음" 기준 (10%)
MARGIN_LOW  = 0.03   # 영업이익률 "낮음" 기준  (3%)
DEBT_LOW    = 100    # 부채비율 "양호" 기준    (100%)
DEBT_HIGH   = 200    # 부채비율 "높음" 기준    (200%)

ID_COLS = ["corp_code", "ticker"]


# ---------------------------------------------------------------------------
# 포맷 유틸
# ---------------------------------------------------------------------------

def fmt_oku(value: float | None, digits: int = 1) -> str:
    """원 단위 금액 → 억원 문자열. null이면 'N/A'."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value / OKUEON:,.{digits}f} 억원"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    """소수 비율 → 퍼센트 문자열. null이면 'N/A'."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def fmt_ratio(value: float | None, digits: int = 1) -> str:
    """부채비율처럼 이미 % 단위인 값 → 문자열. null이면 'N/A'."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}%"


def fmt_int(value, default: str = "N/A") -> str:
    """정수 포맷. null이면 default."""
    try:
        if pd.isna(value):
            return default
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return default


def na(value) -> str:
    """빈 문자열 또는 null → 'N/A'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    s = str(value).strip()
    return s if s else "N/A"


# ---------------------------------------------------------------------------
# 핵심 해석 문장 생성 (rule-based, LLM 호출 없음)
# ---------------------------------------------------------------------------

def build_interpretation(feat: pd.Series, fin_df: pd.DataFrame) -> list[str]:
    """
    숫자 기반 rule-based 해석 문장 3~5개를 반환합니다.
    """
    sentences: list[str] = []
    corp_code = feat.get("corp_code", "")

    # 1) 매출 성장률
    cagr = feat.get("revenue_cagr_3y")
    if pd.notna(cagr):
        cagr_pct = cagr * 100
        level = "높은" if cagr >= CAGR_HIGH else ("소폭" if cagr >= 0 else "감소하는")
        sentences.append(
            f"최근 3년 연평균 매출 성장률(CAGR)은 {cagr_pct:.1f}%로 {level} 성장세를 보이고 있다."
        )
    else:
        sentences.append("최근 3년 매출 성장률은 데이터 부족으로 산출되지 않았다.")

    # 2) 영업이익률
    margin = feat.get("operating_margin_latest")
    if pd.notna(margin):
        margin_pct = margin * 100
        if margin >= MARGIN_HIGH:
            level = "우수한"
        elif margin >= MARGIN_LOW:
            level = "보통 수준의"
        else:
            level = "낮은"
        sentences.append(
            f"최근 연도 영업이익률은 {margin_pct:.1f}%로 {level} 수익성을 나타내고 있다."
        )
    else:
        sentences.append("최근 연도 영업이익률은 데이터 부족으로 산출되지 않았다.")

    # 3) 부채비율
    debt = feat.get("debt_ratio_latest")
    if pd.notna(debt):
        if debt < DEBT_LOW:
            stability = "양호한"
        elif debt < DEBT_HIGH:
            stability = "보통 수준의"
        else:
            stability = "높은 위험을 가진"
        sentences.append(
            f"부채비율은 {debt:.1f}%로 재무 안정성은 {stability} 수준이다."
        )
    else:
        sentences.append("부채비율은 데이터 부족으로 산출되지 않았다.")

    # 4) 공시 건수
    disc = feat.get("disclosure_count_1y")
    if pd.notna(disc):
        sentences.append(f"최근 1년 공시 건수는 {int(disc)}건이다.")

    # 5) 성장·리스크 종합
    growth = feat.get("growth_score")
    risk   = feat.get("risk_score")
    if pd.notna(growth) and pd.notna(risk):
        g_level = "높음" if growth >= 60 else ("보통" if growth >= 30 else "낮음")
        r_level = "높음" if risk   >= 60 else ("보통" if risk   >= 30 else "낮음")
        sentences.append(
            f"성장 스코어는 {int(growth)}점(수준: {g_level}), "
            f"리스크 스코어는 {int(risk)}점(수준: {r_level})으로 평가된다."
        )

    return sentences


# ---------------------------------------------------------------------------
# Markdown 문서 생성
# ---------------------------------------------------------------------------

def build_markdown(
    feat: pd.Series,
    fin_rows: pd.DataFrame,
    filing_rows: pd.DataFrame,
) -> str:
    lines: list[str] = []

    company_name = na(feat.get("company_name"))
    ticker       = na(feat.get("ticker"))

    # 1. 회사명
    lines += [f"# {company_name}", ""]

    # 2. 기본 정보
    lines += [
        "## 기본 정보",
        "",
        f"| 항목 | 값 |",
        f"|---|---|",
        f"| Ticker     | {ticker} |",
        f"| Corp Code  | {na(feat.get('corp_code'))} |",
        f"| 섹터       | {na(feat.get('sector'))} |",
        f"| 서브섹터   | {na(feat.get('subsector'))} |",
        f"| 시장       | {na(feat.get('market'))} |",
        "",
    ]

    # 3. 최근 3개년 재무 요약
    lines += ["## 최근 3개년 재무 요약", ""]
    if fin_rows.empty:
        lines += ["데이터 없음", ""]
    else:
        fin_sorted = fin_rows.sort_values("year", ascending=False)
        lines += [
            "| 연도 | 재무제표 | 매출액 | 영업이익 | 자산총계 | 부채총계 | 자본총계 |",
            "|---|---|---|---|---|---|---|",
        ]
        for _, row in fin_sorted.iterrows():
            lines.append(
                f"| {int(row['year'])} "
                f"| {na(row.get('fs_type'))} "
                f"| {fmt_oku(row.get('revenue'))} "
                f"| {fmt_oku(row.get('operating_income'))} "
                f"| {fmt_oku(row.get('total_assets'))} "
                f"| {fmt_oku(row.get('total_liabilities'))} "
                f"| {fmt_oku(row.get('total_equity'))} |"
            )
        lines.append("")

    # 4. 핵심 지표 요약
    lines += [
        "## 핵심 지표 요약",
        "",
        "| 지표 | 값 |",
        "|---|---|",
        f"| 매출 CAGR (3년)       | {fmt_pct(feat.get('revenue_cagr_3y'))} |",
        f"| 영업이익률 (최근)     | {fmt_pct(feat.get('operating_margin_latest'))} |",
        f"| 부채비율 (최근)       | {fmt_ratio(feat.get('debt_ratio_latest'))} |",
        f"| 최근 1년 공시 건수   | {fmt_int(feat.get('disclosure_count_1y'))} |",
        f"| 성장 스코어           | {fmt_int(feat.get('growth_score'))} / 100 |",
        f"| 리스크 스코어         | {fmt_int(feat.get('risk_score'))} / 100 |",
        "",
    ]

    # 5. 최근 1년 공시 요약
    lines += ["## 최근 1년 공시 요약", ""]
    if filing_rows.empty:
        lines += ["공시 데이터 없음", ""]
    else:
        top_filings = filing_rows.sort_values("filing_date", ascending=False).head(MAX_FILINGS_IN_DOC)
        for _, row in top_filings.iterrows():
            lines.append(
                f"- [{na(row.get('filing_date'))}] "
                f"{na(row.get('report_name'))} "
                f"({na(row.get('receipt_no'))})"
            )
        lines.append("")

    # 6. 핵심 해석 요약
    lines += ["## 핵심 해석 요약", ""]
    for sentence in build_interpretation(feat, fin_rows):
        lines.append(f"- {sentence}")
    lines.append("")

    # 7. 출처
    lines += [
        "## 출처",
        "",
        "- `data/processed/financials/financials_3y.csv`",
        "- `data/processed/financials/filings_1y.csv`",
        "- `data/processed/features/company_features.csv`",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------------------------

def _normalize_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in ID_COLS:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), other="")
            df[col] = df[col].astype(str).str.strip().replace("nan", "")
    return df


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in (MASTER_CSV, FIN_CSV, FILINGS_CSV, FEAT_CSV):
        if not path.exists():
            raise FileNotFoundError(f"입력 파일이 없습니다: {path}")

    master   = _normalize_id_cols(pd.read_csv(MASTER_CSV,  dtype=str).fillna(""))
    features = _normalize_id_cols(pd.read_csv(FEAT_CSV,    dtype={c: str for c in ID_COLS}))
    filings  = _normalize_id_cols(pd.read_csv(FILINGS_CSV, dtype=str))
    fin      = _normalize_id_cols(pd.read_csv(FIN_CSV,     dtype={c: str for c in ID_COLS}))

    fin["year"] = pd.to_numeric(fin["year"], errors="coerce")
    numeric_fin = ["revenue", "operating_income", "net_income",
                   "total_assets", "total_liabilities", "total_equity"]
    for col in numeric_fin:
        if col in fin.columns:
            fin[col] = pd.to_numeric(fin[col], errors="coerce")

    numeric_feat = [
        "revenue_latest", "revenue_prev", "revenue_cagr_3y",
        "operating_income_latest", "operating_margin_latest",
        "total_assets_latest", "total_liabilities_latest", "total_equity_latest",
        "debt_ratio_latest", "disclosure_count_1y", "growth_score", "risk_score",
    ]
    for col in numeric_feat:
        if col in features.columns:
            features[col] = pd.to_numeric(features[col], errors="coerce")

    logger.info(
        f"로드 완료 — master: {len(master)}행, features: {len(features)}행, "
        f"financials: {len(fin)}행, filings: {len(filings)}행"
    )
    return master, features, fin, filings


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== build_rag_docs.py 시작 ===")

    master, features, fin, filings = load_inputs()

    success, fail = 0, 0

    for _, feat in features.iterrows():
        corp_code    = str(feat.get("corp_code", "")).strip()
        ticker       = str(feat.get("ticker", "")).strip()
        company_name = str(feat.get("company_name", "")).strip()

        if not ticker or ticker == "N/A":
            logger.warning(f"  ticker 없음, 스킵: {company_name} (corp_code={corp_code})")
            fail += 1
            continue

        # 기업 재무 행
        fin_rows = fin[fin["corp_code"] == corp_code].copy()
        # 기업 공시 행
        filing_rows = filings[filings["corp_code"] == corp_code].copy()

        # Markdown 생성
        md = build_markdown(feat, fin_rows, filing_rows)

        # 저장
        out_path = OUT_DIR / f"{ticker}.md"
        out_path.write_text(md, encoding="utf-8")
        logger.info(
            f"  생성: {out_path.name}  "
            f"(재무 {len(fin_rows)}행, 공시 {len(filing_rows)}건)"
        )
        success += 1

    logger.info(f"결과 요약 — 생성: {success}, 스킵: {fail}")
    logger.info(f"출력 폴더: {OUT_DIR}")
    logger.info("=== build_rag_docs.py 완료 ===")


if __name__ == "__main__":
    main()
