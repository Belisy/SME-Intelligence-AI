import type { FilingRow } from '@/lib/types'

interface Props {
  filings: FilingRow[]
}

export default function FilingsList({ filings }: Props) {
  if (filings.length === 0) {
    return <p className="text-slate-400 text-sm">최근 1년 공시가 없습니다.</p>
  }

  return (
    <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100 shadow-sm bg-white">
      {filings.map((f) => (
        <li key={f.receipt_no} className="px-5 py-3.5 flex items-start gap-4 hover:bg-slate-50 transition-colors">
          {/* 날짜 */}
          <span className="shrink-0 text-xs text-slate-400 font-mono mt-0.5 w-24">{f.filing_date}</span>
          {/* 보고서명 */}
          <span className="text-sm text-slate-700 flex-1 leading-snug">{f.report_name || f.title}</span>
          {/* 접수번호 */}
          <span className="shrink-0 text-xs text-slate-300 font-mono mt-0.5">{f.receipt_no}</span>
        </li>
      ))}
    </ul>
  )
}
