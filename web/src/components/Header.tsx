'use client'

/** 공통 헤더 + 내비게이션 (usePathname이 필요해 Client Component) */

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_LINKS = [
  { href: '/research', label: 'Research' },
  { href: '/sourcing', label: 'Deal Sourcing' },
] as const

export default function Header() {
  const pathname = usePathname()

  return (
    <header className="bg-slate-900 text-white shadow-md">
      <div className="max-w-screen-xl mx-auto px-6 flex items-center gap-6 h-14">
        {/* 로고 */}
        <Link href="/research" className="text-base font-bold tracking-tight shrink-0">
          SME Intelligence AI
        </Link>

        {/* 구분선 */}
        <span className="h-4 w-px bg-slate-700" />

        {/* 내비게이션 */}
        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={[
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  active
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800',
                ].join(' ')}
              >
                {label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
