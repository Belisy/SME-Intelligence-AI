/** 원 단위 숫자 → 억원 문자열. null이면 'N/A' */
export function fmtOku(value: number | null | undefined, digits = 1): string {
  if (value == null || isNaN(value)) return 'N/A'
  return `${(value / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: digits })} 억원`
}

/** 소수 비율(0.12) → 퍼센트 문자열("12.0%"). null이면 'N/A' */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value == null || isNaN(value)) return 'N/A'
  return `${(value * 100).toFixed(digits)}%`
}

/** 이미 % 단위인 숫자(100.0) → 퍼센트 문자열. null이면 'N/A' */
export function fmtRatio(value: number | null | undefined, digits = 1): string {
  if (value == null || isNaN(value)) return 'N/A'
  return `${value.toFixed(digits)}%`
}

/** 정수 포맷 (천 단위 콤마). null이면 'N/A' */
export function fmtInt(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return 'N/A'
  return Math.round(value).toLocaleString('ko-KR')
}
