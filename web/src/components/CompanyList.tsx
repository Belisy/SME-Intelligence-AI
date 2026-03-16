'use client'

/**
 * 기업 목록 + 검색/필터/정렬 (클라이언트 컴포넌트)
 * Server Component에서 데이터를 받아 로컬 상태로 필터링합니다.
 */

import { useState, useMemo } from 'react'
import Link from 'next/link'
import type { CompanyFeature } from '@/lib/types'
import { fmtPct, fmtRatio, fmtInt } from '@/lib/format'

// ---------------------------------------------------------------------------
// 정렬 옵션
// ---------------------------------------------------------------------------
const SORT_OPTIONS = [
  { label: '성장 스코어 높은순', key: 'growth_score', dir: -1 },
  { label: '리스크 스코어 낮은순', key: 'risk_score', dir: 1 },
  { label: '리스크 스코어 높은순', key: 'risk_score', dir: -1 },
  { label: '매출 CAGR 높은순', key: 'revenue_cagr_3y', dir: -1 },
  { label: '공시 건수 많은순', key: 'disclosure_count_1y', dir: -1 },
  { label: '기업명 가나다순', key: 'company_name', dir: 1 },
] as const

type SortKey = (typeof SORT_OPTIONS)[number]

// ---------------------------------------------------------------------------
// 스코어 뱃지 색상
// ---------------------------------------------------------------------------
function growthBadge(score: number | null) {
  if (score == null) return 'bg-slate-100 text-slate-400'
  if (score >= 60) return 'bg-emerald-100 text-emerald-700'
  if (score >= 30) return 'bg-yellow-50 text-yellow-700'
  return 'bg-slate-100 text-slate-500'
}

function riskBadge(score: number | null) {
  if (score == null) return 'bg-slate-100 text-slate-400'
  if (score >= 60) return 'bg-rose-100 text-rose-700'
  if (score >= 30) return 'bg-orange-50 text-orange-700'
  return 'bg-emerald-50 text-emerald-700'
}

// ---------------------------------------------------------------------------
// 기업 카드
// ---------------------------------------------------------------------------
function CompanyCard({ company }: { company: CompanyFeature }) {
  const cagr = company.revenue_cagr_3y
  const cagrStr = fmtPct(cagr)
  const cagrNegative = cagr != null && cagr < 0

  return (
    <Link href={`/research/${company.ticker}`}>
      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 hover:shadow-md hover:border-slate-200 transition-all cursor-pointer h-full flex flex-col gap-3">
        {/* 상단: 회사명 + 시장 */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-bold text-slate-900 text-base leading-tight">{company.company_name}</h3>
            <p className="text-xs text-slate-400 mt-0.5">{company.ticker}</p>
          </div>
          <span className="shrink-0 bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full">
            {company.market || 'N/A'}
          </span>
        </div>

        {/* 섹터 뱃지 */}
        <div className="flex flex-wrap gap-1.5">
          {company.sector && (
            <span className="bg-sky-50 text-sky-700 text-xs px-2 py-0.5 rounded-full">{company.sector}</span>
          )}
          {company.subsector && (
            <span className="bg-slate-50 text-slate-500 text-xs px-2 py-0.5 rounded-full">{company.subsector}</span>
          )}
        </div>

        {/* 핵심 지표 */}
        <div className="grid grid-cols-2 gap-2 mt-auto">
          <div>
            <p className="text-xs text-slate-400">매출 CAGR</p>
            <p className={`text-sm font-semibold ${cagrNegative ? 'text-rose-600' : 'text-slate-800'}`}>{cagrStr}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">영업이익률</p>
            <p className="text-sm font-semibold text-slate-800">{fmtPct(company.operating_margin_latest)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">부채비율</p>
            <p className="text-sm font-semibold text-slate-800">{fmtRatio(company.debt_ratio_latest)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">공시 건수</p>
            <p className="text-sm font-semibold text-slate-800">{fmtInt(company.disclosure_count_1y)}</p>
          </div>
        </div>

        {/* 스코어 뱃지 */}
        <div className="flex gap-2 pt-1 border-t border-slate-50">
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${growthBadge(company.growth_score)}`}>
            성장 {company.growth_score ?? 'N/A'}
          </span>
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${riskBadge(company.risk_score)}`}>
            리스크 {company.risk_score ?? 'N/A'}
          </span>
        </div>
      </div>
    </Link>
  )
}

// ---------------------------------------------------------------------------
// 메인 컴포넌트
// ---------------------------------------------------------------------------
interface Props {
  companies: CompanyFeature[]
  sectors: string[]
}

export default function CompanyList({ companies, sectors }: Props) {
  const [query, setQuery] = useState('')
  const [sector, setSector] = useState('')
  const [sortIdx, setSortIdx] = useState(0)

  const sortOpt: SortKey = SORT_OPTIONS[sortIdx]

  const filtered = useMemo(() => {
    let list = companies

    // 검색
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter(
        (c) =>
          c.company_name.toLowerCase().includes(q) ||
          c.ticker.toLowerCase().includes(q),
      )
    }

    // 섹터 필터
    if (sector) {
      list = list.filter((c) => c.sector === sector)
    }

    // 정렬
    list = [...list].sort((a, b) => {
      const av = a[sortOpt.key as keyof CompanyFeature] ?? (sortOpt.dir === 1 ? Infinity : -Infinity)
      const bv = b[sortOpt.key as keyof CompanyFeature] ?? (sortOpt.dir === 1 ? Infinity : -Infinity)
      if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * sortOpt.dir
      return ((av as number) - (bv as number)) * sortOpt.dir
    })

    return list
  }, [companies, query, sector, sortIdx])

  return (
    <div>
      {/* 검색/필터 컨트롤 */}
      <div className="flex flex-wrap gap-3 mb-6">
        {/* 검색창 */}
        <input
          type="text"
          placeholder="기업명 또는 종목코드 검색..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 min-w-56 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-300"
        />

        {/* 섹터 필터 */}
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm shadow-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-300"
        >
          <option value="">전체 섹터</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* 정렬 */}
        <select
          value={sortIdx}
          onChange={(e) => setSortIdx(Number(e.target.value))}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm shadow-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-300"
        >
          {SORT_OPTIONS.map((o, i) => (
            <option key={i} value={i}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* 결과 수 */}
      <p className="text-sm text-slate-400 mb-4">{filtered.length}개 기업</p>

      {/* 기업 카드 그리드 */}
      {filtered.length === 0 ? (
        <div className="py-20 text-center text-slate-400">검색 결과가 없습니다.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((c) => (
            <CompanyCard key={c.ticker} company={c} />
          ))}
        </div>
      )}
    </div>
  )
}
