import type { FinancialRow } from '@/lib/types'
import { fmtOku } from '@/lib/format'

interface Props {
  rows: FinancialRow[]
}

const HEADERS = ['연도', '재무제표', '매출액', '영업이익', '자산총계', '부채총계', '자본총계'] as const

export default function FinancialsTable({ rows }: Props) {
  if (rows.length === 0) {
    return <p className="text-slate-400 text-sm">재무 데이터가 없습니다.</p>
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-100 shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
          <tr>
            {HEADERS.map((h) => (
              <th key={h} className="px-4 py-3 text-right first:text-left font-medium whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year} className="border-t border-slate-100 hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-semibold text-slate-700">{row.year}</td>
              <td className="px-4 py-3 text-right">
                <span className="bg-sky-50 text-sky-700 text-xs px-2 py-0.5 rounded-full">{row.fs_type || 'N/A'}</span>
              </td>
              <td className="px-4 py-3 text-right text-slate-700">{fmtOku(row.revenue)}</td>
              <td className={`px-4 py-3 text-right ${(row.operating_income ?? 0) < 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                {fmtOku(row.operating_income)}
              </td>
              <td className="px-4 py-3 text-right text-slate-700">{fmtOku(row.total_assets)}</td>
              <td className="px-4 py-3 text-right text-slate-700">{fmtOku(row.total_liabilities)}</td>
              <td className="px-4 py-3 text-right text-slate-700">{fmtOku(row.total_equity)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
