import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SME Intelligence AI',
  description: 'SME 기업 공시·재무 기반 리서치 어시스턴트',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        {/* 사이트 공통 헤더 */}
        <header className="bg-slate-900 text-white px-6 py-4 flex items-center gap-3 shadow-md">
          <span className="text-lg font-bold tracking-tight">SME Intelligence AI</span>
          <span className="text-slate-400 text-sm">Research Assistant</span>
        </header>
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  )
}
