'use client'

/**
 * Deal Sourcing 결과 리스트 + 필터/정렬 컨트롤 (클라이언트 컴포넌트)
 *
 * 필터:  섹터 선택 / growth_score 최솟값 / risk_score 최댓값
 * 정렬:  growth_score 높은순 | risk_score 낮은순 | disclosure_count_1y 높은순
 * 결과:  테이블 형식, 행 클릭 시 /research/[ticker] 이동
 */

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import type { CompanyFeature } from '@/lib/types'
import { fmtPct, fmtRatio, fmtInt } from '@/lib/format'

// ---------------------------------------------------------------------------
// 정렬 옵션
// ---------------------------------------------------------------------------
const SORT_OPTIONS = [
  { label: '성장 스코어 높은순',    key: 'growth_score',        dir: -1 },
  { label: '리스크 스코어 낮은순',  key: 'risk_score',          dir:  1 },
  { label: '공시 건수 높은순',      key: 'disclosure_count_1y', dir: -1 },
] as const

type SortIdx = 0 | 1 | 2

// ---------------------------------------------------------------------------
// 스코어 배지
// ---------------------------------------------------------------------------
function ScoreBadge({ value, type }: { value: number | null; type: 'growth' | 'risk' }) {
  if (value == null) return <span className="text-slate-300">N/A</span>
  const score = Math.round(value)

  let cls: string
  if (type === 'growth') {
    cls = score >= 60 ? 'bg-emerald-100 text-emerald-700' : score >= 30 ? 'bg-yellow-50 text-yellow-700' : 'bg-slate-100 text-slate-500'
  } else {
    cls = score >= 60 ? 'bg-rose-100 text-rose-700' : score >= 30 ? 'bg-orange-50 text-orange-700' : 'bg-emerald-50 text-emerald-700'
  }

  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {score}
    </span>
  )
}

// ---------------------------------------------------------------------------
// 필터 입력 (숫자 0~100)
// ---------------------------------------------------------------------------
interface NumInputProps {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
}

function NumInput({ label, value, onChange, placeholder }: NumInputProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-slate-500 font-medium">{label}</span>
      <input
        type="number"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-28 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm text-slate-700 placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-300"
      />
    </label>
  )
}

// ---------------------------------------------------------------------------
// 메인 컴포넌트
// ---------------------------------------------------------------------------
interface Props {
  companies: CompanyFeature[]
  sectors: string[]
}

export default function SourcingList({ companies, sectors }: Props) {
  const router = useRouter()

  // 필터 상태
  const [sector, setSector]           = useState('')
  const [growthMin, setGrowthMin]     = useState('')
  const [riskMax, setRiskMax]         = useState('')
  const [sortIdx, setSortIdx]         = useState<SortIdx>(0)

  const sortOpt = SORT_OPTIONS[sortIdx]

  // 필터 + 정렬 적용
  const filtered = useMemo(() => {
    let list = companies

    if (sector) {
      list = list.filter((c) => c.sector === sector)
    }

    if (growthMin !== '') {
      const min = Number(growthMin)
      list = list.filter((c) => (c.growth_score ?? -1) >= min)
    }

    if (riskMax !== '') {
      const max = Number(riskMax)
      list = list.filter((c) => (c.risk_score ?? 101) <= max)
    }

    return [...list].sort((a, b) => {
      const av = a[sortOpt.key as keyof CompanyFeature] as number | null
      const bv = b[sortOpt.key as keyof CompanyFeature] as number | null
      // null은 항상 뒤로
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1
      return (av - bv) * sortOpt.dir
    })
  }, [companies, sector, growthMin, riskMax, sortIdx])

  const handleReset = () => {
    setSector('')
    setGrowthMin('')
    setRiskMax('')
    setSortIdx(0)
  }

  return (
    <div>
      {/* ── 필터 영역 ── */}
      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 mb-6">
        <div className="flex flex-wrap items-end gap-4">
          {/* 섹터 */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-slate-500 font-medium">산업 섹터</span>
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              <option value="">전체 섹터</option>
              {sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>

          {/* growth_score 최솟값 */}
          <NumInput
            label="성장 스코어 최솟값 (0~100)"
            value={growthMin}
            onChange={setGrowthMin}
            placeholder="예: 40"
          />

          {/* risk_score 최댓값 */}
          <NumInput
            label="리스크 스코어 최댓값 (0~100)"
            value={riskMax}
            onChange={setRiskMax}
            placeholder="예: 30"
          />

          {/* 정렬 */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-slate-500 font-medium">정렬 기준</span>
            <select
              value={sortIdx}
              onChange={(e) => setSortIdx(Number(e.target.value) as SortIdx)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              {SORT_OPTIONS.map((o, i) => (
                <option key={i} value={i}>{o.label}</option>
              ))}
            </select>
          </label>

          {/* 초기화 */}
          <button
            onClick={handleReset}
            className="self-end rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors shadow-sm"
          >
            초기화
          </button>
        </div>
      </div>

      {/* ── 결과 수 ── */}
      <p className="text-sm text-slate-400 mb-3">
        {filtered.length}개 기업 · 클릭 시 상세 리포트로 이동
      </p>

      {/* ── 결과 테이블 ── */}
      {filtered.length === 0 ? (
        <div className="py-20 text-center text-slate-400 bg-white rounded-xl border border-slate-100 shadow-sm">
          조건에 맞는 기업이 없습니다.
        </div>
      ) : (
        <div className="rounded-xl border border-slate-100 shadow-sm overflow-x-auto bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide border-b border-slate-100">
              <tr>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">기업명</th>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">섹터</th>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">서브섹터</th>
                <th className="px-4 py-3 text-center font-medium whitespace-nowrap">성장 스코어</th>
                <th className="px-4 py-3 text-center font-medium whitespace-nowrap">리스크 스코어</th>
                <th className="px-4 py-3 text-right font-medium whitespace-nowrap">매출 CAGR</th>
                <th className="px-4 py-3 text-right font-medium whitespace-nowrap">부채비율</th>
                <th className="px-4 py-3 text-right font-medium whitespace-nowrap">공시 건수</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr
                  key={c.ticker}
                  onClick={() => router.push(`/research/${c.ticker}`)}
                  className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors group"
                >
                  {/* 기업명 + 티커 */}
                  <td className="px-4 py-3">
                    <p className="font-semibold text-slate-800 group-hover:text-slate-900">
                      {c.company_name}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">{c.ticker}</p>
                  </td>

                  {/* 섹터 */}
                  <td className="px-4 py-3">
                    {c.sector ? (
                      <span className="bg-sky-50 text-sky-700 text-xs px-2 py-0.5 rounded-full">
                        {c.sector}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>

                  {/* 서브섹터 */}
                  <td className="px-4 py-3 text-slate-500 text-xs">{c.subsector || '—'}</td>

                  {/* 성장 스코어 */}
                  <td className="px-4 py-3 text-center">
                    <ScoreBadge value={c.growth_score} type="growth" />
                  </td>

                  {/* 리스크 스코어 */}
                  <td className="px-4 py-3 text-center">
                    <ScoreBadge value={c.risk_score} type="risk" />
                  </td>

                  {/* 매출 CAGR */}
                  <td className={`px-4 py-3 text-right font-medium ${
                    (c.revenue_cagr_3y ?? 0) < 0 ? 'text-rose-600' : 'text-slate-700'
                  }`}>
                    {fmtPct(c.revenue_cagr_3y)}
                  </td>

                  {/* 부채비율 */}
                  <td className="px-4 py-3 text-right text-slate-700">
                    {fmtRatio(c.debt_ratio_latest)}
                  </td>

                  {/* 공시 건수 */}
                  <td className="px-4 py-3 text-right text-slate-700">
                    {fmtInt(c.disclosure_count_1y)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
