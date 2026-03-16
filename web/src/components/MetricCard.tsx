/** 핵심 지표 카드 — 라벨 + 값 + 선택적 색상 강조 */

interface MetricCardProps {
  label: string
  value: string
  /** 'good' | 'bad' | 'neutral' : 값의 방향성에 따라 텍스트 색상 강조 */
  tone?: 'good' | 'bad' | 'neutral'
  sub?: string
}

const toneClass: Record<string, string> = {
  good: 'text-emerald-600',
  bad: 'text-rose-600',
  neutral: 'text-slate-800',
}

export default function MetricCard({ label, value, tone = 'neutral', sub }: MetricCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 flex flex-col gap-1">
      <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</span>
      <span className={`text-2xl font-bold ${toneClass[tone]}`}>{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
    </div>
  )
}
