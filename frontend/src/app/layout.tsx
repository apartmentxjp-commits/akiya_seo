import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Akiya SEO — 空き家記事AIエージェント管理',
  description: '空き家・古民家SEO記事を自動生成するAIエージェントの管理ダッシュボード',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  )
}
