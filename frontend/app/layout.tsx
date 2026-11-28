import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AECE Desk — NSE Quantitative Trading & Portfolio Terminal',
  description:
    'Institutional NSE equity research, staggered swing execution, and real-time portfolio risk terminal.',
  robots: 'noindex, nofollow',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#F5F7FA] text-[#0F172A]">{children}</body>
    </html>
  )
}
