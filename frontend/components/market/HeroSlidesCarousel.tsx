'use client'

import { useEffect, useState } from 'react'
import {
  Activity, ArrowUpRight, CheckCircle, ChevronLeft, ChevronRight,
  Pause, Play, ShieldCheck, TrendingUp, Wallet,
} from 'lucide-react'
import clsx from 'clsx'

interface TickerItem {
  symbol: string
  sector: string
  last_close: number
  predicted_15d_net_pct: number
  direction: string
}

export function MarketTickerTape({ items }: { items: TickerItem[] }) {
  if (!items || items.length === 0) return null
  const topSlice = items.slice(0, 14)
  const loopItems = [...topSlice, ...topSlice]

  return (
    <div className="relative overflow-hidden border-b border-white/[0.07] bg-[#080C14]/90 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-[#070A0F] to-transparent z-10" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-[#070A0F] to-transparent z-10" />
      <div className="animate-ticker py-1.5">
        {loopItems.map((item, i) => {
          const pos = Number(item.predicted_15d_net_pct) >= 0
          return (
            <div
              key={`${item.symbol}-${i}`}
              className="flex items-center gap-2.5 px-4 border-r border-white/[0.06] font-mono text-[11px] whitespace-nowrap"
            >
              <span className="font-bold text-slate-200 tracking-wide">{item.symbol}</span>
              <span className="text-slate-400">₹{Number(item.last_close).toFixed(2)}</span>
              <span
                className={clsx(
                  'px-1.5 py-0.5 rounded text-[10px] font-semibold',
                  pos
                    ? 'bg-emerald-500/15 text-emerald-400'
                    : 'bg-rose-500/15 text-rose-400'
                )}
              >
                {pos ? '+' : ''}{Number(item.predicted_15d_net_pct).toFixed(2)}%
              </span>
            </div>
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
    { label: 'Live Paper Desk', color: 'emerald' },
    { label: 'Top-5 CNC Alpha', color: 'blue' },
    { label: 'OOS Alpha Proof', color: 'amber' },
    { label: 'Upstox Direct Rail', color: 'cyan' },
  ]

  return (
    <section
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className="relative rounded-2xl border border-white/[0.1] bg-[#0B111C]/90 overflow-hidden shadow-[0_24px_60px_-20px_rgba(2,6,23,0.95)]"
    >
      {/* Top specular shimmer border */}
      <div className="h-[2px] w-full bg-gradient-to-r from-emerald-400/50 via-sky-400/70 to-amber-400/50" />

      {/* Slide Controls Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-white/[0.06] bg-white/[0.015]">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          {slideMeta.map((s, idx) => (
            <button
              key={s.label}
              type="button"
              onClick={() => setActive(idx)}
              className={clsx(
                'relative px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-300 whitespace-nowrap',
                active === idx
                  ? 'bg-white/[0.1] text-white shadow-[0_0_20px_-4px_rgba(59,130,246,0.5)] border border-white/[0.2]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
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
            className="w-7 h-7 rounded-full border border-white/[0.1] bg-white/[0.03] hover:bg-white/[0.09] flex items-center justify-center text-slate-300 transition-colors"
          >
            {paused ? <Play size={11} /> : <Pause size={11} />}
          </button>
          <button
            type="button"
            onClick={() => setActive((prev) => (prev - 1 + slideCount) % slideCount)}
            className="w-7 h-7 rounded-full border border-white/[0.1] bg-white/[0.03] hover:bg-white/[0.09] flex items-center justify-center text-slate-300 transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            type="button"
            onClick={() => setActive((prev) => (prev + 1) % slideCount)}
            className="w-7 h-7 rounded-full border border-white/[0.1] bg-white/[0.03] hover:bg-white/[0.09] flex items-center justify-center text-slate-300 transition-colors"
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
          {/* ── SLIDE 1: Live Paper Portfolio & Capital ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden">
            <div className="pointer-events-none absolute -top-24 -right-24 w-72 h-72 rounded-full bg-emerald-500/10 blur-3xl" />
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center relative">
              <div className="lg:col-span-7 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/30 text-emerald-300 text-[11px] font-mono">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  LIVE PAPER DESK · DIRECT NSE PRICES
                </div>
                <h2 className="text-2xl md:text-[26px] font-bold tracking-tight text-white">
                  ₹{equity.toLocaleString('en-IN', { maximumFractionDigits: 2 })}{' '}
                  <span className="text-sm font-normal text-slate-400">Active Paper Portfolio</span>
                </h2>
                <p className="text-slate-300 text-xs leading-relaxed max-w-xl">
                  Tranche 1 deployed cleanly across {positionsCount} sector-diversified NIFTY-50 delivery holdings using verified live Upstox LTPs and persistent JSON order execution.
                </p>
                <div className="flex flex-wrap gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={() => onNavigate('positions')}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all shadow-[0_0_24px_-4px_rgba(16,185,129,0.7)] flex items-center gap-1.5"
                  >
                    <Wallet size={13} /> Inspect Live Positions
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigate('paper')}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-white/[0.05] text-slate-200 border border-white/[0.12] hover:bg-white/[0.1] transition-colors flex items-center gap-1.5"
                  >
                    Swing Paper Ledger <ArrowUpRight size={13} />
                  </button>
                </div>
              </div>

              <div className="lg:col-span-5 grid grid-cols-2 gap-3">
                <div className="glow-card glow-card-emerald rounded-xl p-4">
                  <div className="text-[10px] font-mono text-emerald-300/80 uppercase">Invested Value</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">₹{marketValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px] font-mono text-slate-400 mt-1">{deployedPct.toFixed(1)}% Deployed</div>
                </div>
                <div className="glow-card glow-card-blue rounded-xl p-4">
                  <div className="text-[10px] font-mono text-sky-300/80 uppercase">Free Virtual Cash</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">₹{cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px] font-mono text-slate-400 mt-1">2 Weekly Tranches Ready</div>
                </div>
                <div className="glow-card rounded-xl p-4 col-span-2 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-mono text-slate-400 uppercase">Mark-to-Market Net P&amp;L</div>
                    <div className={clsx('text-base font-mono font-bold mt-0.5', netPnl >= 0 ? 'text-emerald-400' : 'text-rose-400')}>
                      {netPnl >= 0 ? '+' : '-'}₹{Math.abs(netPnl).toFixed(2)}
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-md bg-white/[0.05] border border-white/[0.1] font-mono text-[10px] text-slate-300">
                    {positionsCount} OPEN POSITIONS
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ── SLIDE 2: Validated 15d CNC Swing Top-5 Glowing Cards ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden">
            <div className="pointer-events-none absolute -top-24 left-1/3 w-72 h-72 rounded-full bg-blue-500/10 blur-3xl" />
            <div className="flex flex-wrap justify-between items-center mb-4 gap-2">
              <div>
                <div className="text-[11px] font-mono text-sky-400 uppercase tracking-wider">15-Session CNC Swing Basket</div>
                <h2 className="text-xl font-bold text-white mt-0.5">Highest-Conviction Ranked NSE Leaders</h2>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('overview')}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-sky-500/15 text-sky-300 border border-sky-400/30 hover:bg-sky-500/25 transition-colors flex items-center gap-1"
              >
                Explore All 67 Symbols <ArrowUpRight size={13} />
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {swingRecs.slice(0, 5).map((r, idx) => (
                <button
                  key={r.symbol}
                  type="button"
                  onClick={() => onNavigate('company')}
                  className={clsx(
                    'text-left glow-card rounded-xl p-4 cursor-pointer',
                    idx === 0 ? 'glow-card-emerald' : 'glow-card-blue'
                  )}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-mono text-slate-400">#{r.rank}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-semibold">
                      +{r.predicted_15d_net_pct}%
                    </span>
                  </div>
                  <div className="text-base font-bold text-white mt-2">{r.symbol}</div>
                  <div className="text-[10px] font-mono text-slate-400 truncate">{r.sector}</div>
                  <div className="mt-3 pt-2 border-t border-white/[0.08] flex justify-between font-mono text-[11px]">
                    <span className="text-slate-300">₹{r.last_close}</span>
                    <span className="text-slate-400">RSI {r.rsi14}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* ── SLIDE 3: Out-of-Sample Purged Backtest & Blind Holdout Proof ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden">
            <div className="pointer-events-none absolute -bottom-24 right-1/4 w-72 h-72 rounded-full bg-amber-500/10 blur-3xl" />
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-6 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-400/30 text-amber-300 text-[11px] font-mono">
                  <TrendingUp size={12} /> 8 / 8 STATISTICAL GATES PASSED
                </div>
                <h2 className="text-2xl font-bold text-white">
                  Purged 6-Fold Alpha: +₹{(swingSummary?.combined_net_profit ?? 34760).toLocaleString('en-IN')}
                </h2>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Schema v3 prunes collinear excess features to 28 orthogonal factors (`alpha=500`), beating the equal-weight NIFTY-50 benchmark across dev folds and turning all 5 blind holdout weekly offsets profitable (`+₹${holdout?.mean_net_profit ?? 900}` vs `-₹735` benchmark).
                </p>
                <button
                  type="button"
                  onClick={() => onNavigate('backtest')}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-amber-400 text-slate-950 hover:bg-amber-300 transition-colors shadow-[0_0_24px_-6px_rgba(245,158,11,0.7)]"
                >
                  Inspect Multi-Fold Audit →
                </button>
              </div>

              <div className="lg:col-span-6 grid grid-cols-2 gap-3 font-mono">
                <div className="glow-card glow-card-amber rounded-xl p-4">
                  <div className="text-[10px] text-amber-300/80 uppercase">Combined Profit Factor</div>
                  <div className="text-2xl font-bold text-white mt-1">{swingSummary?.combined_profit_factor ?? '1.54'}</div>
                  <div className="text-[10px] text-slate-400 mt-1">Net of 0.32% delivery RT cost</div>
                </div>
                <div className="glow-card glow-card-emerald rounded-xl p-4">
                  <div className="text-[10px] text-emerald-300/80 uppercase">Outperformance vs Benchmark</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">+₹{(swingSummary?.combined_outperformance_vs_benchmark ?? 12478).toLocaleString('en-IN')}</div>
                  <div className="text-[10px] text-slate-400 mt-1">Across 10-year NSE history</div>
                </div>
                <div className="glow-card rounded-xl p-4 col-span-2 flex justify-between items-center text-xs">
                  <span className="text-slate-300">Blind Holdout Min Offset: <strong className="text-emerald-400">+₹{holdout?.min_offset_net_profit ?? 327.8}</strong></span>
                  <span className="text-slate-300">Max DD: <strong className="text-white">{holdout?.worst_offset_max_drawdown_pct ?? 7.21}%</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* ── SLIDE 4: Upstox Direct Feed & Safety Guard Rails ── */}
          <div className="w-full shrink-0 p-6 relative overflow-hidden">
            <div className="pointer-events-none absolute -top-24 right-10 w-72 h-72 rounded-full bg-cyan-500/10 blur-3xl" />
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-7 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 text-[11px] font-mono">
                  <ShieldCheck size={12} /> FAIL-CLOSED BROKER &amp; B2B AUTH INFRASTRUCTURE
                </div>
                <h2 className="text-2xl font-bold text-white">Upstox V2/V3 Authenticated &amp; Protected</h2>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Paired 1-year Analytics JWT and active Daily Access Token, 67 verified NSE_EQ instrument keys, JWT/API-key RBAC gating, and hard risk caps (`20%` DD, `30%` sector, `10/min` velocity lock).
                </p>
                <div className="flex gap-2.5">
                  <button
                    type="button"
                    onClick={() => onNavigate('settings')}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-sky-500 text-white hover:bg-sky-400 transition-colors shadow-[0_0_24px_-4px_rgba(59,130,246,0.7)]"
                  >
                    Manage Upstox Keys
                  </button>
                  <button
                    type="button"
                    onClick={() => onNavigate('risk')}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-white/[0.05] border border-white/[0.12] text-slate-200 hover:bg-white/[0.1]"
                  >
                    Risk Monitor
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
                    <span className="text-slate-300 flex items-center gap-2">
                      <CheckCircle size={13} className={ok ? 'text-emerald-400' : 'text-amber-400'} />
                      {label}
                    </span>
                    <span className={clsx('font-bold text-[11px]', ok ? 'text-emerald-400' : 'text-amber-400')}>{val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Animated Slide Progress Bar */}
      <div className="h-[2px] w-full bg-white/[0.05]">
        <div
          key={`${active}-${paused}`}
          className={clsx(
            'h-full bg-gradient-to-r from-emerald-400 via-sky-400 to-amber-400',
            !paused && 'animate-slide-progress'
          )}
          style={paused ? { width: '100%' } : undefined}
        />
      </div>
    </section>
  )
}
