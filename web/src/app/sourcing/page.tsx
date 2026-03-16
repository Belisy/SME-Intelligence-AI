/**
 * /sourcing — Deal Sourcing Assistant (Server Component)
 * 데이터는 서버에서 로드하고 필터·정렬은 SourcingList 클라이언트 컴포넌트에서 처리합니다.
 */

import { getCompanyFeatures, getSectors } from '@/lib/data'
import SourcingList from '@/components/SourcingList'

export const dynamic = 'force-dynamic'

export default function SourcingPage() {
  const companies = getCompanyFeatures()
  const sectors = getSectors()

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      {/* 페이지 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Deal Sourcing</h1>
        <p className="text-slate-500 mt-1 text-sm">
          산업·재무 조건 기반 투자 후보 기업 탐색 · {companies.length}개 기업 수록
        </p>
      </div>

      <SourcingList companies={companies} sectors={sectors} />
    </div>
  )
}
