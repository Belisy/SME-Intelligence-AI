/**
 * 서버 전용 데이터 로더 (fs 사용 — 클라이언트 컴포넌트에서 import 금지)
 *
 * DATA_ROOT 우선순위:
 *   1. 환경변수 DATA_ROOT
 *   2. process.cwd()/../data  (web/ 디렉터리에서 실행 시 자동으로 상위 data/ 참조)
 */

import fs from 'fs'
import path from 'path'
import type { CompanyFeature, FinancialRow, FilingRow } from './types'

const DATA_ROOT = process.env.DATA_ROOT
  ? path.resolve(process.env.DATA_ROOT)
  : path.join(process.cwd(), '..', 'data')

// ---------------------------------------------------------------------------
// CSV 파서 (의존성 없이 직접 구현, quoted field 지원)
// ---------------------------------------------------------------------------

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      inQuotes = !inQuotes
    } else if (ch === ',' && !inQuotes) {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

function parseCsv(filePath: string): Record<string, string>[] {
  if (!fs.existsSync(filePath)) return []
  // utf-8-sig (BOM) 제거
  const content = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '')
  const lines = content.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return []
  const headers = parseCsvLine(lines[0])
  return lines.slice(1).map((line) => {
    const vals = parseCsvLine(line)
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']))
  })
}

function toNum(val: string | undefined): number | null {
  if (!val || val.trim() === '' || val.trim().toLowerCase() === 'n/a') return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

// ---------------------------------------------------------------------------
// 공개 데이터 로더
// ---------------------------------------------------------------------------

/** 전체 기업 피처 목록 */
export function getCompanyFeatures(): CompanyFeature[] {
  const rows = parseCsv(
    path.join(DATA_ROOT, 'processed', 'features', 'company_features.csv'),
  )
  return rows.map((r) => ({
    company_name: r.company_name ?? '',
    ticker: r.ticker ?? '',
    corp_code: r.corp_code ?? '',
    sector: r.sector ?? '',
    subsector: r.subsector ?? '',
    market: r.market ?? '',
    revenue_latest: toNum(r.revenue_latest),
    revenue_prev: toNum(r.revenue_prev),
    revenue_cagr_3y: toNum(r.revenue_cagr_3y),
    operating_income_latest: toNum(r.operating_income_latest),
    operating_margin_latest: toNum(r.operating_margin_latest),
    total_assets_latest: toNum(r.total_assets_latest),
    total_liabilities_latest: toNum(r.total_liabilities_latest),
    total_equity_latest: toNum(r.total_equity_latest),
    debt_ratio_latest: toNum(r.debt_ratio_latest),
    disclosure_count_1y: toNum(r.disclosure_count_1y),
    growth_score: toNum(r.growth_score),
    risk_score: toNum(r.risk_score),
  }))
}

/** ticker로 단일 기업 피처 조회 */
export function getFeatureByTicker(ticker: string): CompanyFeature | null {
  return getCompanyFeatures().find((c) => c.ticker === ticker) ?? null
}

/** corp_code로 3개년 재무 데이터 조회 (최신연도 → 오래된연도 정렬) */
export function getFinancials(corpCode: string): FinancialRow[] {
  const rows = parseCsv(
    path.join(DATA_ROOT, 'processed', 'financials', 'financials_3y.csv'),
  )
  return rows
    .filter((r) => r.corp_code === corpCode)
    .map((r) => ({
      company_name: r.company_name ?? '',
      ticker: r.ticker ?? '',
      corp_code: r.corp_code ?? '',
      year: parseInt(r.year, 10),
      fs_type: r.fs_type ?? '',
      revenue: toNum(r.revenue),
      operating_income: toNum(r.operating_income),
      net_income: toNum(r.net_income),
      total_assets: toNum(r.total_assets),
      total_liabilities: toNum(r.total_liabilities),
      total_equity: toNum(r.total_equity),
    }))
    .sort((a, b) => b.year - a.year)
}

/** corp_code로 최근 1년 공시 목록 조회 (최신순, 최대 10건) */
export function getFilings(corpCode: string, limit = 10): FilingRow[] {
  const rows = parseCsv(
    path.join(DATA_ROOT, 'processed', 'financials', 'filings_1y.csv'),
  )
  return rows
    .filter((r) => r.corp_code === corpCode)
    .map((r) => ({
      company_name: r.company_name ?? '',
      ticker: r.ticker ?? '',
      corp_code: r.corp_code ?? '',
      filing_date: r.filing_date ?? '',
      report_name: r.report_name ?? '',
      title: r.title ?? '',
      receipt_no: r.receipt_no ?? '',
    }))
    .sort((a, b) => b.filing_date.localeCompare(a.filing_date))
    .slice(0, limit)
}

/** 고유 섹터 목록 */
export function getSectors(): string[] {
  const features = getCompanyFeatures()
  return [...new Set(features.map((f) => f.sector).filter(Boolean))].sort()
}
