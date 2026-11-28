import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Market Intelligence AI — Research Terminal',
  description:
    'AI-powered market intelligence and algorithmic trading research platform. ' +
    'Paper trading only. Not financial advice.',
  robots: 'noindex, nofollow',   // Private research tool — not for public indexing
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  )
}
