/**
 * rule-based 핵심 해석 문장 생성 (LLM 미사용)
 *
 * 기준:
 *  - CAGR >= 10%       → 높은 성장세
 *  - CAGR >= 0%        → 소폭 성장세
 *  - CAGR  < 0%        → 감소하는 성장세
 *  - Margin >= 10%     → 우수한 수익성
 *  - Margin >= 3%      → 보통 수준의 수익성
 *  - Margin  < 3%      → 낮은 수익성
 *  - DebtRatio < 100%  → 양호한 재무 안정성
 *  - DebtRatio < 200%  → 보통 수준의 재무 안정성
 *  - DebtRatio >= 200% → 높은 위험의 재무 안정성
 */

import type { CompanyFeature } from './types'

export function buildInterpretation(feat: CompanyFeature): string[] {
  const sentences: string[] = []

  // 1. 매출 성장률
  const cagr = feat.revenue_cagr_3y
  if (cagr != null && !isNaN(cagr)) {
    const pct = (cagr * 100).toFixed(1)
    const level = cagr >= 0.1 ? '높은' : cagr >= 0 ? '소폭' : '감소하는'
    sentences.push(`최근 3년 연평균 매출 성장률(CAGR)은 ${pct}%로 ${level} 성장세를 보이고 있다.`)
  } else {
    sentences.push('최근 3년 매출 성장률은 데이터 부족으로 산출되지 않았다.')
  }

  // 2. 영업이익률
  const margin = feat.operating_margin_latest
  if (margin != null && !isNaN(margin)) {
    const pct = (margin * 100).toFixed(1)
    const level = margin >= 0.1 ? '우수한' : margin >= 0.03 ? '보통 수준의' : '낮은'
    sentences.push(`최근 연도 영업이익률은 ${pct}%로 ${level} 수익성을 나타내고 있다.`)
  } else {
    sentences.push('최근 연도 영업이익률은 데이터 부족으로 산출되지 않았다.')
  }

  // 3. 부채비율
  const debt = feat.debt_ratio_latest
  if (debt != null && !isNaN(debt)) {
    const stability = debt < 100 ? '양호한' : debt < 200 ? '보통 수준의' : '높은 위험을 가진'
    sentences.push(`부채비율은 ${debt.toFixed(1)}%로 재무 안정성은 ${stability} 수준이다.`)
  } else {
    sentences.push('부채비율은 데이터 부족으로 산출되지 않았다.')
  }

  // 4. 공시 건수
  const disc = feat.disclosure_count_1y
  if (disc != null && !isNaN(disc)) {
    sentences.push(`최근 1년 공시 건수는 ${Math.round(disc)}건이다.`)
  }

  // 5. 성장·리스크 종합
  const g = feat.growth_score
  const r = feat.risk_score
  if (g != null && r != null && !isNaN(g) && !isNaN(r)) {
    const gLevel = g >= 60 ? '높음' : g >= 30 ? '보통' : '낮음'
    const rLevel = r >= 60 ? '높음' : r >= 30 ? '보통' : '낮음'
    sentences.push(
      `성장 스코어는 ${Math.round(g)}점(수준: ${gLevel}), 리스크 스코어는 ${Math.round(r)}점(수준: ${rLevel})으로 평가된다.`,
    )
  }

  return sentences
}
