/** 기업별 파생 지표·스코어 (company_features.csv) */
export interface CompanyFeature {
  company_name: string
  ticker: string
  corp_code: string
  sector: string
  subsector: string
  market: string
  revenue_latest: number | null
  revenue_prev: number | null
  revenue_cagr_3y: number | null
  operating_income_latest: number | null
  operating_margin_latest: number | null
  total_assets_latest: number | null
  total_liabilities_latest: number | null
  total_equity_latest: number | null
  debt_ratio_latest: number | null
  disclosure_count_1y: number | null
  growth_score: number | null
  risk_score: number | null
}

/** 연도별 재무 데이터 한 행 (financials_3y.csv) */
export interface FinancialRow {
  company_name: string
  ticker: string
  corp_code: string
  year: number
  fs_type: string
  revenue: number | null
  operating_income: number | null
  net_income: number | null
  total_assets: number | null
  total_liabilities: number | null
  total_equity: number | null
}

/** 공시 한 건 (filings_1y.csv) */
export interface FilingRow {
  company_name: string
  ticker: string
  corp_code: string
  filing_date: string
  report_name: string
  title: string
  receipt_no: string
}
