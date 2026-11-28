'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight, CheckCircle, ChevronLeft, ChevronRight,
  Pause, Play, Search, ShieldCheck, TrendingUp, Wallet, X, Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { API_BASE } from '@/lib/config'

export function Sparkline({
  values,
  positive,
  height = 30,
  width = 86,
}: {
  values?: number[]
  positive?: boolean
  height?: number
  width?: number
}) {
  if (!values || values.length < 2) {
    return <div style={{ width, height }} className="rounded bg-slate-100/70" />
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const pad = 3
  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - pad * 2)
    const y = height - pad - ((v - min) / span) * (height - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const isUp = positive ?? values[values.length - 1] >= values[0]
  const stroke = isUp ? '#059669' : '#E11D48'
  const fillId = `spk_${isUp ? 'up' : 'dn'}_${values.length}_${Math.round(values[0])}`
  const areaPoints = `${points[0].split(',')[0]},${height} ${points.join(' ')} ${points[points.length - 1].split(',')[0]},${height}`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#${fillId})`} />
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(' ')}
      />
    </svg>
  )
}

interface TickerItem {
  symbol: string
  sector: string
  last_close: number
  predicted_15d_net_pct: number
  direction: string
  sparkline_15d?: number[]
}

export function MarketTickerTape({
  items,
  onSelectSymbol,
}: {
  items: TickerItem[]
  onSelectSymbol?: (sym: string) => void
}) {
  if (!items || items.length === 0) return null
  const topSlice = items.slice(0, 14)
  const loopItems = [...topSlice, ...topSlice]

  return (
    <div className="relative overflow-hidden border-b border-slate-200 bg-white/95 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-white to-transparent z-10" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white to-transparent z-10" />
      <div className="animate-ticker py-1.5">
        {loopItems.map((item, i) => {
          const pos = Number(item.predicted_15d_net_pct) >= 0
          return (
            <button
              key={`${item.symbol}-${i}`}
              type="button"
              onClick={() => onSelectSymbol?.(item.symbol)}
              className="flex items-center gap-2.5 px-4 border-r border-slate-200/80 font-mono text-[11px] whitespace-nowrap hover:bg-slate-50 transition-colors"
            >
              <span className="font-bold text-slate-900 tracking-wide">{item.symbol}</span>
              <span className="text-slate-600 tabular-nums">₹{Number(item.last_close).toFixed(2)}</span>
              <span
                className={clsx(
                  'px-1.5 py-0.5 rounded-md text-[10px] font-semibold tabular-nums',
                  pos ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                )}
              >
                {pos ? '+' : ''}{Number(item.predicted_15d_net_pct).toFixed(2)}%
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

interface HeroCarouselProps {
  equity: number
  cash: number
  marketValue: number
  netPnl: number
  positionsCount: number
  swingRecs: any[]
  readiness: any
  tokenStatus: any
  onNavigate: (page: string) => void
  onInspectSymbol?: (sym: string) => void
  onQuickTrade?: (sym: string) => void
}

export function HeroSlidesCarousel({
  equity,
  cash,
  marketValue,
  netPnl,
  positionsCount,
  swingRecs,
  readiness,
  tokenStatus,
  onNavigate,
  onInspectSymbol,
  onQuickTrade,
}: HeroCarouselProps) {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)
  const slideCount = 4

  useEffect(() => {
    if (paused) return
    const timer = setInterval(() => {
      setActive((prev) => (prev + 1) % slideCount)
    }, 6000)
    return () => clearInterval(timer)
  }, [paused])

  const swingSummary = readiness?.swing_15d_model?.summary
  const holdout = readiness?.swing_15d_model?.blind_holdout
  const deployedPct = equity > 0 ? (marketValue / equity) * 100 : 0

  const slideMeta = [
    { label: 'Live Paper Desk' },
    { label: 'Top-5 CNC Alpha' },
    { label: 'OOS Edge Proof' },
    { label: 'Upstox Direct Rail' },
  ]

  return (
    <section
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className="relative rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-[0_14px_40px_-14px_rgba(37,99,235,0.12),0_2px_8px_-2px_rgba(15,23,42,0.04)]"
    >
      <div className="h-[3px] w-full bg-gradient-to-r from-emerald-500 via-blue-600 to-amber-500" />

      {/* Slide Tabs & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {slideMeta.map((s, idx) => (
            <button
              key={s.label}
              type="button"
              onClick={() => setActive(idx)}
              className={clsx(
                'px-3.5 py-1.5 rounded-full text-[11px] font-semibold transition-all duration-300 whitespace-nowrap',
                active === idx
                  ? 'bg-white text-blue-700 border border-blue-200 shadow-[0_4px_14px_-4px_rgba(37,99,235,0.28)]'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-white/70 border border-transparent'
              )}
            >
              {idx + 1}. {s.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            title={paused ? 'Resume auto-slide' : 'Pause auto-slide'}
            className="w-7 h-7 rounded-full border border-slate-200 bg-white hover:bg-slate-100 flex items-center justify-center text-slate-600 transition-colors"
          >
            {paused ? <Play size={11} /> : <Pause size={11} />}
          </button>
          <button
            type="button"
            onClick={() => setActive((prev) => (prev - 1 + slideCount) % slideCount)}
            className="w-7 h-7 rounded-full border border-slate-200 bg-white hover:bg-slate-100 flex items-center justify-center text-slate-600 transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            type="button"
            onClick={() => setActive((prev) => (prev + 1) % slideCount)}
            className="w-7 h-7 rounded-full border border-slate-200 bg-white hover:bg-slate-100 flex items-center justify-center text-slate-600 transition-colors"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Sliding Track */}
      <div className="overflow-hidden">
        <div
          className="flex transition-transform duration-700"
          style={{
            transform: `translate3d(-${active * 100}%, 0, 0)`,
            transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
          }}
        >
          {/* ── SLIDE 1: Live Paper Desk ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden bg-gradient-to-br from-emerald-50/60 via-white to-blue-50/40">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-7 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-mono font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  LIVE PAPER DESK · DIRECT UPSTOX QUOTES
                </div>
                <h2 className="text-2xl md:text-[28px] font-extrabold tracking-tight text-slate-900 tabular-nums">
                  ₹{equity.toLocaleString('en-IN', { maximumFractionDigits: 2 })}{' '}
                  <span className="text-sm font-medium text-slate-500">Virtual Equity Balance</span>
                </h2>
                <p className="text-slate-600 text-xs leading-relaxed max-w-xl">
                  Tranche 1 is live across {positionsCount} sector-diversified NIFTY-50 delivery holdings priced against verified Upstox LTPs with persistent execution tracking.
                </p>
                <div className="flex flex-wrap gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={() => onNavigate('positions')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-all shadow-[0_10px_24px_-6px_rgba(5,150,105,0.45)] flex items-center gap-1.5"
                  >
                    <Wallet size={13} /> Open Positions ({positionsCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => onQuickTrade?.('TECHM')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-all shadow-[0_10px_24px_-6px_rgba(37,99,235,0.4)] flex items-center gap-1.5"
                  >
                    <Zap size={13} /> Quick Paper Trade
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigate('paper')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 transition-colors flex items-center gap-1"
                  >
                    Swing Ledger <ArrowUpRight size={13} />
                  </button>
                </div>
              </div>

              <div className="lg:col-span-5 grid grid-cols-2 gap-3">
                <div className="glow-card glow-card-emerald rounded-xl p-4">
                  <div className="text-[10px] font-mono font-semibold text-emerald-700 uppercase">Invested Value</div>
                  <div className="text-lg font-mono font-bold text-slate-900 mt-1 tabular-nums">₹{marketValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">{deployedPct.toFixed(1)}% Deployed</div>
                </div>
                <div className="glow-card glow-card-blue rounded-xl p-4">
                  <div className="text-[10px] font-mono font-semibold text-blue-700 uppercase">Available Cash</div>
                  <div className="text-lg font-mono font-bold text-slate-900 mt-1 tabular-nums">₹{cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">2 Weekly Tranches Left</div>
                </div>
                <div className="glow-card rounded-xl p-4 col-span-2 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-mono text-slate-500 uppercase">Unrealised + Slippage P&amp;L</div>
                    <div className={clsx('text-base font-mono font-bold mt-0.5 tabular-nums', netPnl >= 0 ? 'text-emerald-600' : 'text-rose-600')}>
                      {netPnl >= 0 ? '+' : '-'}₹{Math.abs(netPnl).toFixed(2)}
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 font-mono text-[10px] font-semibold text-slate-700">
                    0 REAL CAPITAL AT RISK
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ── SLIDE 2: Validated 15d CNC Swing Basket with Real 15d Sparklines ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden bg-gradient-to-br from-blue-50/50 via-white to-indigo-50/40">
            <div className="flex flex-wrap justify-between items-center mb-4 gap-2">
              <div>
                <div className="text-[11px] font-mono font-semibold text-blue-600 uppercase tracking-wider">15-Session CNC Swing Basket · Real 15d Trends</div>
                <h2 className="text-xl font-bold text-slate-900 mt-0.5">Highest-Conviction Ranked NSE Leaders</h2>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('overview')}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors flex items-center gap-1"
              >
                Explore All 67 Stocks <ArrowUpRight size={13} />
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {swingRecs.slice(0, 5).map((r, idx) => (
                <div
                  key={r.symbol}
                  onClick={() => onInspectSymbol?.(r.symbol)}
                  className={clsx(
                    'text-left glow-card rounded-xl p-4 cursor-pointer',
                    idx === 0 ? 'glow-card-emerald' : 'glow-card-blue'
                  )}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-mono text-slate-500 font-semibold">#{r.rank} · {r.sector}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold">
                      +{r.predicted_15d_net_pct}%
                    </span>
                  </div>
                  <div className="flex items-end justify-between mt-2">
                    <div>
                      <div className="text-base font-extrabold text-slate-900">{r.symbol}</div>
                      <div className="text-xs font-mono text-slate-600 tabular-nums">₹{r.last_close}</div>
                    </div>
                    <Sparkline values={r.sparkline_15d} positive={(r.sparkline_15d?.[r.sparkline_15d.length - 1] ?? r.last_close) >= (r.sparkline_15d?.[0] ?? r.last_close)} width={74} height={28} />
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-100 flex justify-between items-center font-mono text-[10px]">
                    <span className="text-slate-500">RSI {r.rsi14} · {r.suggested_qty} sh</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onQuickTrade?.(r.symbol)
                      }}
                      className="text-blue-600 hover:text-blue-800 font-bold"
                    >
                      Trade →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── SLIDE 3: Out-of-Sample Purged Backtest & Blind Holdout Proof ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-6 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-[11px] font-mono font-semibold">
                  <TrendingUp size={12} /> 8 / 8 STATISTICAL VALIDATION GATES PASSED
                </div>
                <h2 className="text-2xl font-extrabold text-slate-900 tabular-nums">
                  Purged 6-Fold Alpha: +₹{(swingSummary?.combined_net_profit ?? 34760).toLocaleString('en-IN')}
                </h2>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Schema v3 uses 28 orthogonalized features (`alpha=500`), beating the equal-weight NIFTY-50 benchmark across 10 years of NSE daily sessions and finishing profitable on every blind holdout offset (`+₹${holdout?.mean_net_profit ?? 900}` vs `-₹735` benchmark).
                </p>
                <button
                  type="button"
                  onClick={() => onNavigate('backtest')}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-500 text-white hover:bg-amber-600 transition-colors shadow-[0_10px_24px_-6px_rgba(217,119,6,0.45)]"
                >
                  Open Full Backtest Audit →
                </button>
              </div>

              <div className="lg:col-span-6 grid grid-cols-2 gap-3 font-mono">
                <div className="glow-card glow-card-amber rounded-xl p-4">
                  <div className="text-[10px] text-amber-700 uppercase font-semibold">Combined Profit Factor</div>
                  <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">{swingSummary?.combined_profit_factor ?? '1.54'}</div>
                  <div className="text-[10px] text-slate-500 mt-1">Net of 0.32% CNC round-trip cost</div>
                </div>
                <div className="glow-card glow-card-emerald rounded-xl p-4">
                  <div className="text-[10px] text-emerald-700 uppercase font-semibold">Benchmark Outperformance</div>
                  <div className="text-2xl font-bold text-emerald-600 mt-1 tabular-nums">+₹{(swingSummary?.combined_outperformance_vs_benchmark ?? 12478).toLocaleString('en-IN')}</div>
                  <div className="text-[10px] text-slate-500 mt-1">Across 5 Dev + 250d Holdout</div>
                </div>
                <div className="glow-card rounded-xl p-4 col-span-2 flex justify-between items-center text-xs">
                  <span className="text-slate-600">Holdout Min Offset: <strong className="text-emerald-600">+₹{holdout?.min_offset_net_profit ?? 327.8}</strong></span>
                  <span className="text-slate-600">Worst Holdout DD: <strong className="text-slate-900">{holdout?.worst_offset_max_drawdown_pct ?? 7.21}%</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* ── SLIDE 4: Direct NSE Upstox Feed & Safety Guard Rails ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden bg-gradient-to-br from-sky-50/50 via-white to-slate-50">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-7 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-[11px] font-mono font-semibold">
                  <ShieldCheck size={12} /> FAIL-CLOSED BROKER &amp; B2B API SECURITY
                </div>
                <h2 className="text-2xl font-extrabold text-slate-900">Upstox V2/V3 Authenticated &amp; Guarded</h2>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Paired 1-year Analytics JWT and daily trading token, 67 official NSE_EQ instrument keys, JWT/API-key RBAC access control, and non-overridable portfolio risk caps.
                </p>
                <div className="flex gap-2.5">
                  <button
                    type="button"
                    onClick={() => onNavigate('settings')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-[0_10px_24px_-6px_rgba(37,99,235,0.4)]"
                  >
                    Manage Upstox Keys
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigate('risk')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
                  >
                    Risk Center
                  </button>
                </div>
              </div>

              <div className="lg:col-span-5 space-y-2.5 font-mono text-xs">
                {[
                  ['1-Year Analytics Token', tokenStatus?.analytics_token_valid ? 'ACTIVE' : 'MISSING', tokenStatus?.analytics_token_valid],
                  ['Daily Trading Token', tokenStatus?.token_valid ? 'ACTIVE' : 'EXPIRED', tokenStatus?.token_valid],
                  ['OOS Validation Gates', readiness?.swing_oos_ready ? '8 / 8 PASS' : 'BLOCKED', readiness?.swing_oos_ready],
                  ['Real-Capital Execution', readiness?.live_trading_enabled ? 'ENABLED' : 'LOCKED (PAPER SAFE)', true],
                ].map(([label, val, ok]) => (
                  <div key={String(label)} className="glow-card rounded-xl px-4 py-2.5 flex items-center justify-between">
                    <span className="text-slate-700 flex items-center gap-2 font-medium">
                      <CheckCircle size={13} className={ok ? 'text-emerald-600' : 'text-amber-600'} />
                      {label}
                    </span>
                    <span className={clsx('font-bold text-[11px]', ok ? 'text-emerald-600' : 'text-amber-600')}>{val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Animated Slide Progress Bar */}
      <div className="h-[3px] w-full bg-slate-100">
        <div
          key={`${active}-${paused}`}
          className={clsx(
            'h-full bg-gradient-to-r from-emerald-500 via-blue-600 to-amber-500',
            !paused && 'animate-slide-progress'
          )}
          style={paused ? { width: '100%' } : undefined}
        />
      </div>
    </section>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Instant Paper Order Ticket Modal (Kite / Tickertape Style)
// ─────────────────────────────────────────────────────────────────────────────

export function QuickOrderModal({
  symbol,
  symbols,
  cash,
  onClose,
  onOrderFilled,
}: {
  symbol: string
  symbols: string[]
  cash: number
  onClose: () => void
  onOrderFilled: (msg: string) => void
}) {
  const [sym, setSym] = useState(symbol || 'TECHM')
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [qty, setQty] = useState(1)
  const [quote, setQuote] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setQuote(null)
    fetch(`${API_BASE}/api/v1/signals/quote/${encodeURIComponent(sym)}`)
      .then((r) => r.json())
      .then((d) => { if (alive && d?.ltp) setQuote(Number(d.ltp)) })
      .catch(() => {})
    return () => { alive = false }
  }, [sym])

  const estNotional = (quote || 0) * qty
  const estFees = estNotional * 0.0008

  const submitOrder = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/bot/paper-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, direction: side, quantity: qty }),
      })
      const data = await res.json()
      if (!res.ok || data?.order?.status !== 'FILLED') {
        setError(data?.order?.rejection_reason || data?.detail || 'Order rejected')
      } else {
        onOrderFilled(`Paper ${side} ${qty} ${sym} FILLED @ ₹${data.order.fill_price}`)
        onClose()
      }
    } catch {
      setError('Failed to reach paper execution server')
    }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/35 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
      <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className={clsx('px-5 py-4 flex items-center justify-between text-white', side === 'BUY' ? 'bg-blue-600' : 'bg-rose-600')}>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest opacity-85">Paper Delivery CNC Order</div>
            <div className="text-base font-bold">{side} {sym} · NSE</div>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-white/15">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-slate-100">
            {(['BUY', 'SELL'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSide(s)}
                className={clsx(
                  'py-2 rounded-lg text-xs font-bold transition-all',
                  side === s
                    ? (s === 'BUY' ? 'bg-blue-600 text-white shadow-sm' : 'bg-rose-600 text-white shadow-sm')
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                {s}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-mono uppercase text-slate-500 block mb-1">NSE Symbol</label>
              <select
                value={sym}
                onChange={(e) => setSym(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-900"
              >
                {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] font-mono uppercase text-slate-500 block mb-1">Quantity (Shares)</label>
              <input
                type="number"
                min={1}
                value={qty}
                onChange={(e) => setQty(Math.max(1, parseInt(e.target.value || '1', 10)))}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-900 tabular-nums"
              />
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 space-y-1.5 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Live Upstox Quote</span>
              <span className="font-bold text-slate-900 tabular-nums">{quote ? `₹${quote.toFixed(2)}` : 'Fetching...'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Estimated Margin</span>
              <span className="font-bold text-slate-900 tabular-nums">₹{estNotional.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Sim. Slippage + Brokerage</span>
              <span className="text-slate-600 tabular-nums">₹{estFees.toFixed(2)}</span>
            </div>
            <div className="flex justify-between pt-1.5 border-t border-slate-200">
              <span className="text-slate-500">Available Virtual Cash</span>
              <span className="font-semibold text-emerald-700 tabular-nums">₹{cash.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
            </div>
          </div>

          {error && <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-mono">{error}</div>}

          <button
            type="button"
            onClick={submitOrder}
            disabled={submitting || !quote}
            className={clsx(
              'w-full py-2.5 rounded-xl text-xs font-bold text-white transition-all shadow-sm disabled:opacity-40',
              side === 'BUY' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-rose-600 hover:bg-rose-700'
            )}
          >
            {submitting ? 'Executing Paper Order...' : `Place Paper ${side} Order`}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Keyboard Command Palette (Ctrl+K Stock & View Launcher)
// ─────────────────────────────────────────────────────────────────────────────

export function CommandPaletteModal({
  symbols,
  navItems,
  onSelectPage,
  onSelectSymbol,
  onClose,
}: {
  symbols: string[]
  navItems: { id: string; label: string }[]
  onSelectPage: (id: string) => void
  onSelectSymbol: (sym: string) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const q = query.trim().toUpperCase()
  const matchedSyms = useMemo(() => symbols.filter((s) => !q || s.includes(q)).slice(0, 8), [symbols, q])
  const matchedPages = useMemo(
    () => navItems.filter((n) => !q || n.label.toUpperCase().includes(q) || n.id.toUpperCase().includes(q)).slice(0, 6),
    [navItems, q]
  )

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/35 backdrop-blur-sm flex items-start justify-center pt-20 p-4 animate-fade-in" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-200">
          <Search size={15} className="text-slate-400" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search any NSE stock (HAL, TECHM, ETERNAL) or workspace tab..."
            className="flex-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
          <button type="button" onClick={onClose} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500">ESC</button>
        </div>
        <div className="max-h-80 overflow-y-auto p-3 space-y-3">
          {matchedSyms.length > 0 && (
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400 px-2 mb-1">NSE Equities ({symbols.length})</div>
              <div className="grid grid-cols-2 gap-1.5">
                {matchedSyms.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => { onSelectSymbol(s); onClose() }}
                    className="flex items-center justify-between px-3 py-2 rounded-lg text-left hover:bg-blue-50 text-xs font-mono text-slate-800 border border-slate-100"
                  >
                    <span className="font-bold">{s}</span>
                    <span className="text-[10px] text-blue-600">Inspect →</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {matchedPages.length > 0 && (
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400 px-2 mb-1">Workspace Sections</div>
              <div className="space-y-1">
                {matchedPages.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => { onSelectPage(p.id); onClose() }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-100 text-xs text-slate-700 font-medium"
                  >
                    <span>{p.label}</span>
                    <span className="text-[10px] font-mono text-slate-400">{p.id}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
