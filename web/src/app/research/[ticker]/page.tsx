/**
 * /research/[ticker] — 기업 상세 분석 페이지 (Server Component)
 */

import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getFeatureByTicker, getFinancials, getFilings } from '@/lib/data'
import { buildInterpretation } from '@/lib/interpret'
import { fmtOku, fmtPct, fmtRatio, fmtInt } from '@/lib/format'
import MetricCard from '@/components/MetricCard'
import FinancialsTable from '@/components/FinancialsTable'
import FilingsList from '@/components/FilingsList'

export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// 섹션 컨테이너
// ---------------------------------------------------------------------------
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">{title}</h2>
      {children}
    </section>
  )
}

// ---------------------------------------------------------------------------
// growth_score / risk_score 색상 결정
// ---------------------------------------------------------------------------
function growthTone(score: number | null): 'good' | 'neutral' | 'bad' {
  if (score == null) return 'neutral'
  return score >= 60 ? 'good' : score >= 30 ? 'neutral' : 'bad'
}
function riskTone(score: number | null): 'good' | 'neutral' | 'bad' {
  if (score == null) return 'neutral'
  return score >= 60 ? 'bad' : score >= 30 ? 'neutral' : 'good'
}

// ---------------------------------------------------------------------------
// 페이지
// ---------------------------------------------------------------------------
interface PageProps {
  params: { ticker: string }
}

export default function CompanyDetailPage({ params }: PageProps) {
  const { ticker } = params

  const feat = getFeatureByTicker(ticker)
  if (!feat) notFound()

  const financials = getFinancials(feat.corp_code)
  const filings = getFilings(feat.corp_code)
  const interpretation = buildInterpretation(feat)

  const cagr = feat.revenue_cagr_3y
  const cagrTone: 'good' | 'neutral' | 'bad' =
    cagr == null ? 'neutral' : cagr >= 0.1 ? 'good' : cagr >= 0 ? 'neutral' : 'bad'

  const margin = feat.operating_margin_latest
  const marginTone: 'good' | 'neutral' | 'bad' =
    margin == null ? 'neutral' : margin >= 0.1 ? 'good' : margin >= 0.03 ? 'neutral' : 'bad'

  const debt = feat.debt_ratio_latest
  const debtTone: 'good' | 'neutral' | 'bad' =
    debt == null ? 'neutral' : debt < 100 ? 'good' : debt < 200 ? 'neutral' : 'bad'

  return (
    <div className="max-w-screen-lg mx-auto px-6 py-8">
      {/* 뒤로가기 */}
      <Link
        href="/research"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 transition-colors mb-6"
      >
        ← 기업 목록으로
      </Link>

      {/* 상단 기본 정보 */}
      <div className="flex flex-wrap items-start gap-4 mb-8">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold text-slate-900">{feat.company_name}</h1>
          <div className="flex flex-wrap gap-2 mt-2">
            <span className="bg-slate-100 text-slate-600 text-sm px-3 py-0.5 rounded-full font-mono">{feat.ticker}</span>
            <span className="bg-sky-50 text-sky-700 text-sm px-3 py-0.5 rounded-full">{feat.market}</span>
            {feat.sector && (
              <span className="bg-indigo-50 text-indigo-700 text-sm px-3 py-0.5 rounded-full">{feat.sector}</span>
            )}
            {feat.subsector && (
              <span className="bg-slate-50 text-slate-500 text-sm px-3 py-0.5 rounded-full">{feat.subsector}</span>
            )}
          </div>
        </div>
        <div className="text-right text-xs text-slate-300 font-mono">corp_code: {feat.corp_code}</div>
      </div>

      {/* 핵심 지표 카드 (2×3) */}
      <Section title="핵심 지표">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricCard label="매출 CAGR (3년)" value={fmtPct(cagr)} tone={cagrTone} />
          <MetricCard label="영업이익률 (최근)" value={fmtPct(margin)} tone={marginTone} />
          <MetricCard
            label="부채비율 (최근)"
            value={fmtRatio(debt)}
            tone={debtTone}
            sub="낮을수록 안정"
          />
          <MetricCard
            label="공시 건수 (1년)"
            value={fmtInt(feat.disclosure_count_1y)}
            sub="건"
          />
          <MetricCard
            label="성장 스코어"
            value={`${fmtInt(feat.growth_score)} / 100`}
            tone={growthTone(feat.growth_score)}
            sub="높을수록 성장성 우수"
          />
          <MetricCard
            label="리스크 스코어"
            value={`${fmtInt(feat.risk_score)} / 100`}
            tone={riskTone(feat.risk_score)}
            sub="낮을수록 재무 안정"
          />
        </div>
      </Section>

      {/* 최근 3개년 재무 테이블 */}
      <Section title="최근 3개년 재무 요약">
        <FinancialsTable rows={financials} />
      </Section>

      {/* 최근 1년 공시 목록 */}
      <Section title={`최근 1년 공시 (최신 ${filings.length}건)`}>
        <FilingsList filings={filings} />
      </Section>

      {/* 핵심 해석 요약 */}
      <Section title="핵심 해석 요약">
        {interpretation.length === 0 ? (
          <p className="text-slate-400 text-sm">해석 정보가 없습니다.</p>
        ) : (
          <ul className="space-y-2">
            {interpretation.map((sentence, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-slate-700">
                <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-slate-300" />
                {sentence}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* 최근 재무 요약 수치 */}
      <Section title="최근 연도 재무 요약">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricCard label="매출액 (최근)" value={fmtOku(feat.revenue_latest)} />
          <MetricCard label="영업이익 (최근)" value={fmtOku(feat.operating_income_latest)} />
          <MetricCard label="자산총계 (최근)" value={fmtOku(feat.total_assets_latest)} />
          <MetricCard label="부채총계 (최근)" value={fmtOku(feat.total_liabilities_latest)} />
          <MetricCard label="자본총계 (최근)" value={fmtOku(feat.total_equity_latest)} />
        </div>
      </Section>

      {/* 출처 */}
      <section className="border-t border-slate-100 pt-6 mt-4">
        <p className="text-xs text-slate-400 font-medium mb-1">데이터 출처</p>
        <ul className="text-xs text-slate-400 space-y-0.5 font-mono">
          <li>data/processed/financials/financials_3y.csv</li>
          <li>data/processed/financials/filings_1y.csv</li>
          <li>data/processed/features/company_features.csv</li>
        </ul>
      </section>
    </div>
  )
}
