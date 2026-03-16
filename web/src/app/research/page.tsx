/**
 * /research — 기업 목록/검색 페이지 (Server Component)
 * 데이터를 서버에서 로드해 클라이언트 CompanyList에 전달합니다.
 */

import { getCompanyFeatures, getSectors } from '@/lib/data'
import CompanyList from '@/components/CompanyList'

export const dynamic = 'force-dynamic' // 매 요청마다 최신 CSV 반영

export default function ResearchPage() {
  const companies = getCompanyFeatures()
  const sectors = getSectors()

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      {/* 페이지 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">기업 리서치</h1>
        <p className="text-slate-500 mt-1 text-sm">
          공시·재무 데이터 기반 SME 기업 분석 플랫폼 · {companies.length}개 기업 수록
        </p>
      </div>

      {/* 검색/필터/정렬 + 카드 그리드 (클라이언트 인터랙션) */}
      <CompanyList companies={companies} sectors={sectors} />
    </div>
  )
}
