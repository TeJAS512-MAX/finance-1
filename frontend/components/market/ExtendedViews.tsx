'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, BrainCircuit, CheckCircle,
  Database, FileText, Layers, Newspaper, RefreshCw, Search, Shield,
  ShieldAlert, Sliders, TrendingDown, TrendingUp, XCircle, Zap,
} from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import clsx from 'clsx'
import useSWR from 'swr'
import { API_BASE } from '@/lib/config'
import { fetcher, pnlBg, pnlColor, StatCard, StatusDot } from './MarketViews'
import { Sparkline } from './HeroSlidesCarousel'

// ─────────────────────────────────────────────────────────────────────────────
// 1. Market Overview (NIFTY-50 Regime + Ranked 37/67 NSE Universe)
// ─────────────────────────────────────────────────────────────────────────────

export function MarketOverviewView({
  onInspectSymbol,
  onQuickTrade,
}: {
  onInspectSymbol?: (sym: string) => void
  onQuickTrade?: (sym: string) => void
} = {}) {
  const { data: swing, isValidating } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const { data: intraday } = useSWR(`${API_BASE}/api/v1/signals`, fetcher, { refreshInterval: 15000 })
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('ALL')

  const ranked: any[] = swing?.all_ranked || []
  const sectors = useMemo(() => ['ALL', ...Array.from(new Set(ranked.map((r) => String(r.sector || 'OTHER'))))], [ranked])
  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase()
    return ranked.filter((r) => {
      if (sectorFilter !== 'ALL' && r.sector !== sectorFilter) return false
      if (q && !String(r.symbol).toUpperCase().includes(q)) return false
      return true
    })
  }, [ranked, search, sectorFilter])

  const positiveCount = ranked.filter((r) => Number(r.predicted_15d_net_pct) > 0).length
  const aboveSma200 = ranked.filter((r) => Number(r.sma200_dist_pct) > 0).length
  const intradaySignals: any[] = intraday?.signals || []

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="NIFTY50 > SMA200"
          value={swing?.nifty_above_sma200 ? 'BULL REGIME' : 'CAUTIOUS'}
          sub={swing?.nifty_above_sma50 ? 'Above 50 DMA & 200 DMA' : 'Below 50 DMA'}
          trend={swing?.nifty_above_sma200 ? 1 : -1}
        />
        <StatCard
          label="Swing Universe Breadth"
          value={`${positiveCount} / ${ranked.length}`}
          sub="POSITIVE 15D NET ALPHA"
          trend={positiveCount > 0 ? 1 : -1}
        />
        <StatCard
          label="Above 200 DMA"
          value={`${aboveSma200} / ${ranked.length}`}
          sub="LONG-TERM UPTREND"
        />
        <StatCard
          label="Registered Master"
          value={`${swing?.universe_symbols?.length ?? 67} NSE`}
          sub={`${intradaySignals.length} live 30m probes · as of ${swing?.as_of?.slice(0, 10) || '--'}`}
        />
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-terminal-border flex flex-wrap gap-3 justify-between items-center bg-terminal-surface/30">
          <div>
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Activity size={16} className="text-accent-primary" />
              NSE 15-Day Swing Screener ({filtered.length} stocks)
            </h3>
            <p className="text-xs text-text-muted mt-0.5">
              Ranked by after-cost 15-session predicted CNC delivery return (net of 0.32% RT cost)
            </p>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-text-muted" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter symbol..."
                className="bg-terminal-bg border border-terminal-border rounded pl-8 pr-3 py-1.5 text-xs font-mono text-text-primary focus:outline-none focus:border-accent-primary/50"
              />
            </div>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="bg-terminal-bg border border-terminal-border rounded px-2.5 py-1.5 text-xs font-mono text-text-primary"
            >
              {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            {isValidating && <span className="text-[10px] text-accent-primary font-mono animate-pulse">● SYNCING</span>}
          </div>
        </div>

        <div className="overflow-x-auto max-h-[540px] overflow-y-auto">
          <table className="w-full text-left font-mono text-xs whitespace-nowrap">
            <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-text-muted">
              <tr>
                <th className="py-2.5 px-4">Rank</th>
                <th className="py-2.5 px-4">Symbol</th>
                <th className="py-2.5 px-4">Sector</th>
                <th className="py-2.5 px-4 text-right">Last Close</th>
                <th className="py-2.5 px-4">15D Trend</th>
                <th className="py-2.5 px-4 text-right">Est 15d Net%</th>
                <th className="py-2.5 px-4 text-right">RSI(14)</th>
                <th className="py-2.5 px-4 text-right">Sharpe(20)</th>
                <th className="py-2.5 px-4 text-right">200 DMA%</th>
                <th className="py-2.5 px-4">Signal</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.symbol}
                  onClick={() => onInspectSymbol?.(r.symbol)}
                  className="border-b border-slate-200/70 hover:bg-blue-50/40 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-4 text-text-muted">#{r.rank}</td>
                  <td className="py-2 px-4 font-bold text-slate-900 hover:text-blue-700">{r.symbol}</td>
                  <td className="py-2 px-4 text-text-secondary">{r.sector}</td>
                  <td className="py-2 px-4 text-right tabular-nums">₹{Number(r.last_close).toFixed(2)}</td>
                  <td className="py-1.5 px-4">
                    <Sparkline
                      values={r.sparkline_15d}
                      positive={Number(r.predicted_15d_net_pct ?? 0) >= 0}
                      height={22}
                      width={74}
                    />
                  </td>
                  <td className={clsx('py-2 px-4 text-right font-semibold tabular-nums', pnlColor(r.predicted_15d_net_pct))}>
                    {r.predicted_15d_net_pct >= 0 ? '+' : ''}{Number(r.predicted_15d_net_pct).toFixed(2)}%
                  </td>
                  <td className="py-2 px-4 text-right tabular-nums">{r.rsi14}</td>
                  <td className="py-2 px-4 text-right tabular-nums">{r.sharpe_20}</td>
                  <td className={clsx('py-2 px-4 text-right tabular-nums', pnlColor(r.sma200_dist_pct))}>
                    {r.sma200_dist_pct >= 0 ? '+' : ''}{r.sma200_dist_pct}%
                  </td>
                  <td className="py-2 px-4">
                    <span className={clsx(
                      'px-2 py-0.5 rounded-md text-[10px] font-bold border',
                      r.direction === 'LONG'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-100 text-slate-500 border-slate-200'
                    )}>
                      {r.direction}
                    </span>
                  </td>
                  <td className="py-2 px-4 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onQuickTrade?.(r.symbol)
                      }}
                      className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-[10px] font-semibold transition-colors"
                    >
                      Trade
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={11} className="py-8 text-center text-text-muted">No matching symbols in ranked universe.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. Event Radar (Real Public News Events from /api/v1/news)
// ─────────────────────────────────────────────────────────────────────────────

export function EventRadarView() {
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/news?limit=50`, fetcher, { refreshInterval: 20000 })
  const [filter, setFilter] = useState<'ALL' | 'POSITIVE' | 'NEGATIVE' | 'HIGH_CRED'>('ALL')
  const items: any[] = data?.items || []

  const filtered = useMemo(() => items.filter((n) => {
    if (filter === 'POSITIVE') return n.sentiment_label === 'POSITIVE'
    if (filter === 'NEGATIVE') return n.sentiment_label === 'NEGATIVE'
    if (filter === 'HIGH_CRED') return Number(n.credibility_score ?? 0) >= 0.8
    return true
  }), [items, filter])

  const highCred = items.filter((n) => Number(n.credibility_score ?? 0) >= 0.8).length
  const posCount = items.filter((n) => n.sentiment_label === 'POSITIVE').length
  const negCount = items.filter((n) => n.sentiment_label === 'NEGATIVE').length

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Tracked Catalysts" value={`${items.length}`} sub="INGESTED PUBLIC EVENTS" />
        <StatCard label="High Credibility" value={`${highCred}`} sub="CREDIBILITY >= 80%" />
        <StatCard label="Bullish Events" value={`${posCount}`} sub="POSITIVE SENTIMENT" trend={1} />
        <StatCard label="Bearish Events" value={`${negCount}`} sub="NEGATIVE SENTIMENT" trend={negCount > 0 ? -1 : 0} />
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-terminal-border flex flex-wrap gap-2 justify-between items-center bg-terminal-surface/30">
          <div className="flex items-center gap-2">
            <Newspaper size={16} className="text-accent-primary" />
            <h3 className="text-sm font-semibold text-text-primary">Public Event Radar &amp; Catalyst Stream</h3>
          </div>
          <div className="flex gap-1.5 font-mono text-[11px]">
            {([
              ['ALL', 'All'],
              ['HIGH_CRED', 'High Credibility'],
              ['POSITIVE', 'Positive'],
              ['NEGATIVE', 'Negative'],
            ] as const).map(([key, lbl]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={clsx(
                  'px-2.5 py-1 rounded border',
                  filter === key ? 'border-accent-primary text-accent-primary bg-accent-primary/10' : 'border-terminal-border text-text-muted'
                )}
              >
                {lbl}
              </button>
            ))}
            {isValidating && <span className="ml-2 text-accent-primary self-center">● LIVE</span>}
          </div>
        </div>
        <div className="divide-y divide-terminal-border max-h-[540px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-text-muted">No matching catalysts in events database.</div>
          ) : filtered.map((n, i) => (
            <div key={n.id || i} className="p-4 hover:bg-terminal-cardHover transition-colors">
              <div className="flex justify-between gap-4 items-start">
                <p className="text-sm font-medium text-text-primary">{n.headline}</p>
                <span className="px-2 py-0.5 rounded border border-terminal-border text-[10px] font-mono text-text-secondary shrink-0">
                  {n.verification_status || 'PUBLIC'}
                </span>
              </div>
              <div className="flex flex-wrap gap-4 mt-2 text-[11px] font-mono text-text-muted">
                <span className="flex items-center gap-1.5">
                  <StatusDot status={n.sentiment_label === 'POSITIVE' ? 'positive' : n.sentiment_label === 'NEGATIVE' ? 'negative' : 'neutral'} />
                  {n.sentiment_label}
                </span>
                <span>{n.publisher}</span>
                <span>{n.event_type}</span>
                <span>CRED: {((n.credibility_score ?? 0) * 100).toFixed(0)}%</span>
                <span>{n.published_at ? new Date(n.published_at).toLocaleString('en-IN') : '--'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. Company Intel (67-Symbol Live Upstox Quote + Swing & Position Inspector)
// ─────────────────────────────────────────────────────────────────────────────

export function CompanyIntelView({
  selectedSymbol,
  onQuickTrade,
}: {
  selectedSymbol?: string
  onQuickTrade?: (sym: string) => void
} = {}) {
  const { data: swing } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 20000 })
  const { data: posData } = useSWR(`${API_BASE}/api/v1/portfolio/positions`, fetcher, { refreshInterval: 5000 })
  const symbols: string[] = swing?.universe_symbols || ['TECHM', 'RELIANCE', 'TCS', 'COALINDIA', 'WIPRO', 'ADANIPORTS', 'NESTLEIND']
  const [selected, setSelected] = useState(selectedSymbol || 'TECHM')
  useEffect(() => {
    if (selectedSymbol) setSelected(selectedSymbol)
  }, [selectedSymbol])
  const { data: quote, isValidating: loadingQuote, error: quoteErr } = useSWR(
    selected ? `${API_BASE}/api/v1/signals/quote/${encodeURIComponent(selected)}` : null,
    fetcher,
    { refreshInterval: 10000 }
  )

  const swingRow = (swing?.all_ranked || []).find((r: any) => r.symbol === selected)
  const heldPos = (posData?.positions || []).find((p: any) => p.symbol === selected)

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="card p-5 flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Layers size={16} className="text-accent-primary" />
            Company Intel ({symbols.length} Upstox NSE Equities)
          </h3>
          <p className="text-xs text-text-muted mt-0.5">Live Upstox quote, circuit limits, Swing Alpha score &amp; active paper position</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="bg-white border border-slate-200 focus:border-blue-500 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 min-w-[200px] shadow-sm outline-none"
          >
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {onQuickTrade && (
            <button
              type="button"
              onClick={() => onQuickTrade(selected)}
              className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              Quick Paper Order ({selected})
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label={`${selected} Live LTP`}
          value={quote?.ltp ? `₹${Number(quote.ltp).toFixed(2)}` : loadingQuote ? 'Loading...' : '--'}
          sub={quote?.instrument_key || (quoteErr ? 'Quote unavailable' : 'Upstox Official Feed')}
        />
        <StatCard
          label="Sector"
          value={quote?.sector || swingRow?.sector || '--'}
          sub={`Volume: ${Number(quote?.volume || 0).toLocaleString('en-IN')}`}
        />
        <StatCard
          label="15d Swing Forecast"
          value={swingRow ? `${swingRow.predicted_15d_net_pct >= 0 ? '+' : ''}${swingRow.predicted_15d_net_pct}%` : 'Extended 66'}
          sub={swingRow ? `Rank #${swingRow.rank} · ${swingRow.direction}` : 'Quote-ready (Next-50)'}
          trend={swingRow?.predicted_15d_net_pct}
        />
        <StatCard
          label="Paper Holding"
          value={heldPos ? `${heldPos.quantity} sh` : '0 sh'}
          sub={heldPos ? `Avg ₹${Number(heldPos.avg_price).toFixed(2)} · P&L ${heldPos.pnl >= 0 ? '+' : ''}₹${Number(heldPos.pnl).toFixed(2)}` : 'Not held in paper portfolio'}
          trend={heldPos?.pnl}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-5 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Upstox Live OHLC &amp; Circuits</h4>
          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            {[
              ['Open', quote?.open ? `₹${quote.open}` : '--'],
              ['High / Low', quote?.high ? `₹${quote.high} / ₹${quote.low}` : '--'],
              ['Prev Close', quote?.close ? `₹${quote.close}` : '--'],
              ['Avg Traded Price', quote?.avg_price ? `₹${quote.avg_price}` : '--'],
              ['Upper Circuit', quote?.upper_circuit ? `₹${quote.upper_circuit}` : '--'],
              ['Lower Circuit', quote?.lower_circuit ? `₹${quote.lower_circuit}` : '--'],
            ].map(([k, v]) => (
              <div key={k} className="border-b border-terminal-border/40 pb-2 flex justify-between">
                <span className="text-text-muted">{k}</span>
                <span className="text-text-primary font-semibold">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-5 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Technical &amp; Alpha Factor Breakdown</h4>
          {swingRow ? (
            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              {[
                ['Gross 15d Pred', `${swingRow.predicted_15d_gross_pct}%`],
                ['Net After 0.32% RT', `${swingRow.predicted_15d_net_pct}%`],
                ['RSI(14)', `${swingRow.rsi14}`],
                ['Sharpe(20)', `${swingRow.sharpe_20}`],
                ['20d Return', `${swingRow.ret_20 ?? '--'}%`],
                ['200 DMA Dist', `${swingRow.sma200_dist_pct}%`],
                ['Dist 20d High', `${swingRow.dist_20_high_pct ?? '--'}%`],
                ['Dist 60d High', `${swingRow.dist_60_high_pct ?? '--'}%`],
              ].map(([k, v]) => (
                <div key={k} className="border-b border-terminal-border/40 pb-2 flex justify-between">
                  <span className="text-text-muted">{k}</span>
                  <span className="text-text-primary font-semibold">{v}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs font-mono text-text-muted">
              {selected} is mapped in the 67-stock Upstox Instrument Master (`INSTRUMENT_KEYS`) with live quotes enabled. Core 37 NIFTY-50 symbols carry validated Schema v3 rankings.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. Causal Map (Real Schema v3 Model Factor Attribution Weights)
// ─────────────────────────────────────────────────────────────────────────────

export function CausalMapView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const coefs: Record<string, number> = readiness?.swing_15d_model?.top_ridge_coefficients || {}
  const chartData = Object.entries(coefs)
    .map(([feature, weight]) => ({ feature, weight: Number(weight), absWeight: Math.abs(Number(weight)) }))
    .sort((a, b) => b.absWeight - a.absWeight)

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="card p-5">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Database size={16} className="text-accent-primary" />
              Alpha Factor Causal Attribution (Schema v3 · 28 Orthogonal Features)
            </h3>
            <p className="text-xs text-text-muted mt-1">
              Exact signed standardized Ridge regression weights (`alpha=500`, `1%–99%` winsorizer, collinear `excess_*` features pruned)
            </p>
          </div>
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-fin-pos/10 text-fin-pos border border-fin-pos/30">
            REAL MODEL WEIGHTS
          </span>
        </div>

        <div className="h-[460px]">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.slice(0, 16)} layout="vertical" margin={{ top: 5, right: 20, left: 95, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis type="category" dataKey="feature" width={95} tick={{ fill: '#0F172A', fontSize: 11, fontFamily: 'monospace' }} />
                <ReferenceLine x={0} stroke="#CBD5E1" />
                <Tooltip formatter={(val: any) => [`${Number(val).toFixed(4)}`, 'Ridge Coef']} />
                <Bar dataKey="weight" radius={[2, 2, 2, 2]}>
                  {chartData.slice(0, 16).map((entry) => (
                    <Cell key={entry.feature} fill={pnlBg(entry.weight)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs font-mono text-text-muted">Loading model coefficients...</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="card p-4">
          <p className="text-text-muted uppercase text-[10px]">Pullback Mean-Reversion</p>
          <p className="text-text-primary mt-1 font-semibold">dist_60_high ({coefs.dist_60_high ?? '--'}), ret_20 ({coefs.ret_20 ?? '--'})</p>
          <p className="text-text-muted mt-1">Negative weights reward oversold quality pullbacks below 60-day highs.</p>
        </div>
        <div className="card p-4">
          <p className="text-text-muted uppercase text-[10px]">Structural Trend Anchor</p>
          <p className="text-text-primary mt-1 font-semibold">sma200_dist ({coefs.sma200_dist ?? '--'}), dist_20_high ({coefs.dist_20_high ?? '--'})</p>
          <p className="text-text-muted mt-1">Positive weights favor names holding long-term 200 DMA uptrends.</p>
        </div>
        <div className="card p-4">
          <p className="text-text-muted uppercase text-[10px]">Market Regime Filter</p>
          <p className="text-text-primary mt-1 font-semibold">mkt_ret_20 ({coefs.mkt_ret_20 ?? '--'}), mkt_vol_20 ({coefs.mkt_vol_20 ?? '--'})</p>
          <p className="text-text-muted mt-1">Orthogonalized market context replaces collinear `excess_*` terms.</p>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 5 & 6. Expectations & Priced-In Diagnostics
// ─────────────────────────────────────────────────────────────────────────────

export function ExpectationsView() {
  const { data: swing } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const { data: signals } = useSWR(`${API_BASE}/api/v1/signals`, fetcher, { refreshInterval: 15000 })
  const { data: ledger } = useSWR(`${API_BASE}/api/v1/bot/swing/ledger`, fetcher, { refreshInterval: 15000 })

  const recs: any[] = swing?.recommendations || []
  const dirModel = signals?.direction_model
  const tranches: any[] = ledger?.ledger?.tranches || []

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Active 15d CNC Tranche Picks"
          value={`${recs.length} / 5`}
          sub={`Hurdle > 0.32% RT Cost · As of ${swing?.as_of?.slice(0, 10) || '--'}`}
          trend={recs.length > 0 ? 1 : 0}
        />
        <StatCard
          label="Next-Session Model Gate"
          value={(dirModel?.state || 'UNKNOWN').toUpperCase()}
          sub={dirModel?.test_mae_pct ? `MAE ${dirModel.test_mae_pct}% vs ${dirModel.baseline_mae_pct}% baseline` : 'Withheld when < baseline'}
        />
        <StatCard
          label="Prospective Ledger Tranches"
          value={`${tranches.length} logged`}
          sub={`Open: ${ledger?.aggregate?.open_tranches ?? 0} · Resolved: ${ledger?.aggregate?.resolved_tranches ?? 0}`}
        />
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Current Model Return Expectations vs Transaction Cost Hurdle</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-terminal-border text-text-muted">
                <th className="py-2 px-3">Symbol</th>
                <th className="py-2 px-3 text-right">Last Close</th>
                <th className="py-2 px-3 text-right">Gross 15d%</th>
                <th className="py-2 px-3 text-right">Cost Hurdle</th>
                <th className="py-2 px-3 text-right">Net Expected%</th>
                <th className="py-2 px-3 text-right">Allocated ₹</th>
              </tr>
            </thead>
            <tbody>
              {recs.map((r) => (
                <tr key={r.symbol} className="border-b border-terminal-border/40">
                  <td className="py-2 px-3 font-bold text-text-primary">{r.symbol}</td>
                  <td className="py-2 px-3 text-right">₹{r.last_close}</td>
                  <td className="py-2 px-3 text-right text-accent-primary">+{r.predicted_15d_gross_pct}%</td>
                  <td className="py-2 px-3 text-right text-text-muted">0.32%</td>
                  <td className="py-2 px-3 text-right text-fin-pos font-bold">+{r.predicted_15d_net_pct}%</td>
                  <td className="py-2 px-3 text-right">₹{(Number(r.last_close) * Number(r.suggested_qty)).toFixed(2)}</td>
                </tr>
              ))}
              {recs.length === 0 && (
                <tr><td colSpan={6} className="py-6 text-center text-text-muted">No recommendations cleared hurdle.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export function PricedInView() {
  const { data: swing } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const ranked: any[] = swing?.all_ranked || []
  const oversoldPullbacks = [...ranked].filter((r) => Number(r.sma200_dist_pct) > -5 && Number(r.rsi14) <= 45).slice(0, 10)
  const stretchedNames = [...ranked].sort((a, b) => Number(b.rsi14) - Number(a.rsi14)).slice(0, 10)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-fade-in">
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-1 flex items-center gap-2">
          <TrendingUp size={15} className="text-fin-pos" /> Unpriced Pullback Candidates (RSI &le; 45)
        </h3>
        <p className="text-xs text-text-muted mb-3">Stocks below short-term overbought levels retaining trend support</p>
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-terminal-border text-text-muted">
              <th className="py-2">Symbol</th>
              <th className="py-2 text-right">RSI(14)</th>
              <th className="py-2 text-right">60d High%</th>
              <th className="py-2 text-right">Est Net%</th>
            </tr>
          </thead>
          <tbody>
            {oversoldPullbacks.map((r) => (
              <tr key={r.symbol} className="border-b border-terminal-border/40">
                <td className="py-2 font-bold">{r.symbol}</td>
                <td className="py-2 text-right text-fin-pos">{r.rsi14}</td>
                <td className="py-2 text-right">{r.dist_60_high_pct ?? '--'}%</td>
                <td className={clsx('py-2 text-right', pnlColor(r.predicted_15d_net_pct))}>{r.predicted_15d_net_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-1 flex items-center gap-2">
          <TrendingDown size={15} className="text-fin-warn" /> Priced-In / Extended Momentum (Highest RSI)
        </h3>
        <p className="text-xs text-text-muted mb-3">Extended names where upside is increasingly priced in short-term</p>
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-terminal-border text-text-muted">
              <th className="py-2">Symbol</th>
              <th className="py-2 text-right">RSI(14)</th>
              <th className="py-2 text-right">20d Ret%</th>
              <th className="py-2 text-right">Est Net%</th>
            </tr>
          </thead>
          <tbody>
            {stretchedNames.map((r) => (
              <tr key={r.symbol} className="border-b border-terminal-border/40">
                <td className="py-2 font-bold">{r.symbol}</td>
                <td className={clsx('py-2 text-right', r.rsi14 >= 65 ? 'text-fin-warn' : 'text-text-primary')}>{r.rsi14}</td>
                <td className="py-2 text-right">{r.ret_20 ?? '--'}%</td>
                <td className={clsx('py-2 text-right', pnlColor(r.predicted_15d_net_pct))}>{r.predicted_15d_net_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 7, 8, 9. Backtesting, Strategy Lab & Model Lab (Zero Static Placeholders)
// ─────────────────────────────────────────────────────────────────────────────

export function BacktestingView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const swing = readiness?.swing_15d_model
  const folds: any[] = [
    ...(swing?.dev_folds || []).map((f: any) => ({ ...f, name: f.fold })),
    ...(swing?.blind_holdout ? [{ ...swing.blind_holdout, name: 'blind_holdout_250d' }] : []),
  ]
  const intraFolds: any[] = readiness?.walk_forward_oos?.folds || []

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Swing 6-Fold Net OOS"
          value={`+₹${(swing?.summary?.combined_net_profit ?? 0).toLocaleString('en-IN')}`}
          sub={`Outperformance +₹${(swing?.summary?.combined_outperformance_vs_benchmark ?? 0).toLocaleString('en-IN')}`}
          trend={1}
        />
        <StatCard label="Profit Factor" value={`${swing?.summary?.combined_profit_factor ?? '--'}`} sub="ALL TRADES NET OF 0.32% COST" trend={1} />
        <StatCard
          label="Blind Holdout (250d)"
          value={`+₹${(swing?.blind_holdout?.mean_net_profit ?? 0).toFixed(2)}`}
          sub={`Benchmark: ₹${(swing?.blind_holdout?.benchmark_equal_weight_profit ?? 0).toFixed(2)}`}
          trend={1}
        />
        <StatCard label="Validation Gates" value={swing?.swing_oos_ready ? '8 / 8 PASS' : 'BLOCKED'} sub={`Max Holdout DD: ${swing?.blind_holdout?.worst_offset_max_drawdown_pct ?? '--'}%`} trend={swing?.swing_oos_ready ? 1 : -1} />
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
          <BarChart3 size={16} className="text-accent-primary" />
          Purged Chronological Folds + Blind Holdout (Strategy vs Equal-Weight NIFTY50 Benchmark)
        </h3>
        <div className="h-[240px] mb-5">
          {folds.length > 0 && (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={folds}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} tickFormatter={(v) => `₹${v}`} />
                <ReferenceLine y={0} stroke="#CBD5E1" />
                <Tooltip />
                <Bar dataKey="mean_net_profit" name="Swing AI Net ₹" fill="#059669" radius={[4, 4, 0, 0]} />
                <Bar dataKey="benchmark_equal_weight_profit" name="Benchmark ₹" fill="#2563EB" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-terminal-border text-text-muted">
                <th className="py-2">Fold</th>
                <th className="py-2">Window</th>
                <th className="py-2 text-right">AI Net ₹</th>
                <th className="py-2 text-right">Benchmark ₹</th>
                <th className="py-2 text-right">WR%</th>
                <th className="py-2 text-right">PF</th>
                <th className="py-2 text-right">Max DD%</th>
                <th className="py-2 text-right">IC</th>
              </tr>
            </thead>
            <tbody>
              {folds.map((f) => (
                <tr key={f.name} className="border-b border-terminal-border/40">
                  <td className="py-2 font-bold text-text-primary">{f.name}</td>
                  <td className="py-2 text-text-muted">{f.start?.slice(0, 10)} → {f.end?.slice(0, 10)}</td>
                  <td className={clsx('py-2 text-right font-semibold', pnlColor(f.mean_net_profit))}>₹{f.mean_net_profit}</td>
                  <td className={clsx('py-2 text-right', pnlColor(f.benchmark_equal_weight_profit))}>₹{f.benchmark_equal_weight_profit}</td>
                  <td className="py-2 text-right">{f.mean_win_rate_pct}%</td>
                  <td className="py-2 text-right">{f.mean_profit_factor}</td>
                  <td className="py-2 text-right">{f.worst_offset_max_drawdown_pct}%</td>
                  <td className="py-2 text-right">{f.mean_daily_spearman_ic}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {intraFolds.length > 0 && (
        <div className="card p-5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">
            Track B: 30m Intraday Walk-Forward Audit (Research-Only · Withheld From Live Capital)
          </h4>
          <p className="text-xs font-mono text-text-muted">
            Combined Net: ₹{readiness?.walk_forward_oos?.combined_net_profit} · PF {readiness?.walk_forward_oos?.combined_profit_factor} · Trades {readiness?.walk_forward_oos?.combined_trades}
          </p>
        </div>
      )}
    </div>
  )
}

export function StrategyLabView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const rules = readiness?.swing_15d_model?.strategy_rules || {}

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
          <Sliders size={16} className="text-accent-primary" />
          Production Strategy Specification — `swing_15d_cnc_delivery`
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
          {[
            ['Holding Horizon', `${rules.holding_horizon_sessions ?? 15} sessions`],
            ['Rebalance Cadence', `Every ${rules.rebalance_step_sessions ?? 5} sessions (3 tranches)`],
            ['Max Picks / Tranche', `${rules.max_positions_per_tranche ?? 5} stocks`],
            ['Sector Concentration Cap', `${rules.max_per_sector ?? 2} per sector`],
            ['Total Capital Cap', `${rules.total_deployed_pct ?? 50}% CNC`],
            ['Cost Assumption', `${rules.delivery_round_trip_cost_pct ?? 0.32}% round-trip`],
            ['Upstox Product Type', `CNC Delivery (${rules.product ?? 'D'})`],
            ['Deployment Status', readiness?.swing_oos_ready ? 'VALIDATED 8/8' : 'BLOCKED'],
          ].map(([k, v]) => (
            <div key={k} className="border border-terminal-border rounded p-3 bg-terminal-bg">
              <div className="text-[10px] text-text-muted uppercase">{k}</div>
              <div className="text-sm font-bold text-text-primary mt-1">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">Strategy Gate Matrix</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div className="border border-fin-pos/40 bg-fin-pos/5 rounded p-4">
            <div className="text-fin-pos font-bold">1. 15d CNC Swing Alpha</div>
            <div className="text-text-muted mt-1">Status: {readiness?.swing_oos_ready ? 'ACTIVE / PAPER VALIDATED' : 'RESEARCH'}</div>
            <div className="text-text-primary mt-2">PF {readiness?.swing_15d_model?.summary?.combined_profit_factor} · Blind Holdout +₹{readiness?.swing_15d_model?.blind_holdout?.mean_net_profit}</div>
          </div>
          <div className="border border-fin-warn/40 bg-fin-warn/5 rounded p-4">
            <div className="text-fin-warn font-bold">2. 30m Intraday Tribunal</div>
            <div className="text-text-muted mt-1">Status: RESEARCH ONLY (BLOCKED)</div>
            <div className="text-text-primary mt-2">OOS Net ₹{readiness?.walk_forward_oos?.combined_net_profit ?? '--'} · PF {readiness?.walk_forward_oos?.combined_profit_factor ?? '--'}</div>
          </div>
          <div className="border border-terminal-border bg-terminal-surface/30 rounded p-4">
            <div className="text-text-secondary font-bold">3. Next-Session Open-to-Close</div>
            <div className="text-text-muted mt-1">Status: {String(readiness?.daily_model?.state || 'WITHHELD').toUpperCase()}</div>
            <div className="text-text-primary mt-2">MAE {readiness?.daily_model?.test_mae_pct ?? '--'}% vs {readiness?.daily_model?.baseline_mae_pct ?? '--'}% base</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ModelLabView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const swing = readiness?.swing_15d_model
  const daily = readiness?.daily_model
  const intra = readiness?.intraday_model
  const coefs = Object.entries(swing?.top_ridge_coefficients || {})

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 font-mono text-xs space-y-1.5">
          <div className="text-accent-primary font-bold">Swing 15d Ridge (Schema v{swing?.schema_version ?? 3})</div>
          <div className="text-text-muted">Features: 28 orthogonalized · alpha=500 · 1–99% winsorizer</div>
          <div className="text-text-primary">Symbols: {swing?.symbols_count ?? 37} · Data through: {swing?.data_through?.slice(0, 10) || '--'}</div>
          <div className="text-fin-pos">Mean Spearman IC: {swing?.summary?.mean_daily_spearman_ic ?? '--'}</div>
        </div>
        <div className="card p-4 font-mono text-xs space-y-1.5">
          <div className="text-text-primary font-bold">Intraday 30m Meta-Label Tribunal</div>
          <div className="text-text-muted">Features: {intra?.feature_count ?? 18} · Approval threshold: {intra?.approval_threshold ?? 0.58}</div>
          <div className="text-fin-warn">OOS Status: Research Only (-₹{Math.abs(readiness?.walk_forward_oos?.combined_net_profit ?? 0)})</div>
        </div>
        <div className="card p-4 font-mono text-xs space-y-1.5">
          <div className="text-text-primary font-bold">Daily Next-Session Ridge</div>
          <div className="text-text-muted">Source: {daily?.data_source || 'Upstox v3'} · Through {daily?.trained_through?.slice(0, 10) || '--'}</div>
          <div className="text-text-primary">Test MAE: {daily?.test_mae_pct ?? '--'}% vs Baseline {daily?.baseline_mae_pct ?? '--'}%</div>
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Full 28 Standardized Feature Coefficients</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-xs">
          {coefs.map(([feat, w]) => (
            <div key={feat} className="flex justify-between px-3 py-2 rounded border border-terminal-border bg-terminal-bg">
              <span className="text-text-secondary">{feat}</span>
              <span className={clsx('font-bold', pnlColor(Number(w)))}>{Number(w) >= 0 ? '+' : ''}{Number(w).toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. Trade Journal (Real Executed Paper Orders + Prospective Ledger + Bot Journal)
// ─────────────────────────────────────────────────────────────────────────────

export function TradeJournalView() {
  const { data: ordData } = useSWR(`${API_BASE}/api/v1/orders`, fetcher, { refreshInterval: 5000 })
  const { data: ledgerData } = useSWR(`${API_BASE}/api/v1/bot/swing/ledger`, fetcher, { refreshInterval: 10000 })
  const { data: botJournal } = useSWR(`${API_BASE}/api/v1/bot/journal`, fetcher, { refreshInterval: 10000 })

  const orders: any[] = ordData?.orders || []
  const tranches: any[] = ledgerData?.ledger?.tranches || []
  const agg = ledgerData?.aggregate || {}
  const decisions: any[] = botJournal?.journal || []

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Executed Paper Orders" value={`${orders.length}`} sub={`MODE: ${ordData?.mode || 'Paper'}`} />
        <StatCard label="Open Swing Tranches" value={`${agg.open_tranches ?? 0}`} sub="15-SESSION PROSPECTIVE" />
        <StatCard label="Resolved Tranches" value={`${agg.resolved_tranches ?? 0}`} sub={`Win Rate: ${agg.win_rate_pct ?? 0}%`} />
        <StatCard label="Ledger Net PnL" value={`₹${agg.net_pnl_inr ?? 0}`} sub={`Profit Factor: ${agg.profit_factor ?? 0}`} trend={agg.net_pnl_inr ?? 0} />
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
          <FileText size={16} className="text-accent-primary" /> Prospective 15-Day Swing Tranche Ledger
        </h3>
        {tranches.length === 0 ? (
          <p className="text-xs font-mono text-text-muted">No recorded swing tranches yet.</p>
        ) : tranches.map((t) => (
          <div key={t.tranche_id} className="border border-terminal-border rounded p-4 mb-3 bg-terminal-bg font-mono text-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-text-primary">{t.tranche_id} · Entry {t.entry_date?.slice(0, 10)}</span>
              <span className={clsx('px-2 py-0.5 rounded text-[10px] font-bold uppercase', t.status === 'resolved' ? 'bg-fin-pos/15 text-fin-pos' : 'bg-accent-primary/15 text-accent-primary')}>
                {t.status}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
              {(t.positions || []).map((p: any) => (
                <div key={p.symbol} className="border border-terminal-border/60 rounded p-2 bg-terminal-surface/30">
                  <div className="font-bold text-text-primary">{p.symbol} ({p.suggested_qty} sh)</div>
                  <div className="text-text-muted">Entry: ₹{p.entry_close}</div>
                  <div className="text-fin-pos">Est 15d: +{p.predicted_15d_pct}%</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {decisions.length > 0 && (
        <div className="card p-5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">Autonomous Bot Evaluations ({decisions.length})</h4>
          <div className="space-y-2 text-xs font-mono">
            {decisions.slice(0, 10).map((d, idx) => (
              <div key={idx} className="flex justify-between border-b border-terminal-border/40 pb-1.5">
                <span>{d.symbol} · {d.final_decision}</span>
                <span className="text-text-muted">{d.timestamp?.slice(0, 19)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 11, 12, 13. Data Quality, System Health & Live Alerts
// ─────────────────────────────────────────────────────────────────────────────

export function DataQualityView() {
  const { data: tok } = useSWR(`${API_BASE}/api/v1/token/status`, fetcher, { refreshInterval: 5000 })
  const { data: swing } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const [probeSym, setProbeSym] = useState('RELIANCE')
  const [probeResult, setProbeResult] = useState<any>(null)
  const [probing, setProbing] = useState(false)

  const runLiveProbe = async () => {
    setProbing(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/signals/quote/${encodeURIComponent(probeSym)}`)
      setProbeResult(await res.json())
    } catch {
      setProbeResult({ detail: 'Network error contacting backend' })
    }
    setProbing(false)
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Daily Trading JWT"
          value={tok?.token_valid ? 'ACTIVE' : 'EXPIRED/MISSING'}
          sub={tok?.expires_at ? `Exp: ${tok.expires_at.slice(0, 16)}` : 'Refresh in API Token tab'}
          trend={tok?.token_valid ? 1 : -1}
        />
        <StatCard
          label="1-Year Analytics JWT"
          value={tok?.analytics_token_valid ? 'ACTIVE' : 'MISSING'}
          sub={tok?.analytics_expires_at ? `Exp: ${tok.analytics_expires_at.slice(0, 10)}` : 'Set UPSTOX_ANALYTICS_TOKEN'}
          trend={tok?.analytics_token_valid ? 1 : -1}
        />
        <StatCard label="Candle Cache Date" value={swing?.as_of?.slice(0, 10) || '--'} sub={`Stale days: ${swing?.stale_days ?? '--'} · Source: ${swing?.data_source || '--'}`} />
        <StatCard label="Upstox Instrument Master" value={`${swing?.universe_symbols?.length ?? 67} ISINs`} sub="Verified NSE_EQ keys" />
      </div>

      <div className="card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <RefreshCw size={15} className="text-accent-primary" /> Live Upstox Connectivity Probe
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={probeSym}
            onChange={(e) => setProbeSym(e.target.value.toUpperCase())}
            className="bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-xs font-mono text-text-primary w-40"
          />
          <button
            type="button"
            onClick={runLiveProbe}
            disabled={probing}
            className="px-4 py-2 rounded text-xs font-semibold bg-accent-primary/20 text-accent-primary border border-accent-primary/40 hover:bg-accent-primary/30"
          >
            {probing ? 'Testing...' : 'Test Live Quote'}
          </button>
        </div>
        {probeResult && (
          <pre className="p-3 rounded bg-terminal-bg border border-terminal-border text-[11px] font-mono text-text-primary overflow-x-auto">
            {JSON.stringify(probeResult, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

export function SystemHealthView() {
  const { data: health } = useSWR(`${API_BASE}/health/detail`, fetcher, { refreshInterval: 5000 })
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 10000 })
  const checks: Record<string, boolean> = readiness?.checks || {}
  const limits: Record<string, any> = health?.risk_limits || {}
  const features: Record<string, any> = health?.features || {}

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="API Status" value={String(health?.status || 'UNKNOWN').toUpperCase()} sub={`Env: ${health?.env || '--'} · v${health?.version || '1.0'}`} trend={1} />
        <StatCard label="Uptime" value={`${health?.uptime_seconds ?? '--'}s`} sub="LIVE SERVER PROCESS" />
        <StatCard label="Live Trading" value={health?.safety_flags?.live_trading_enabled ? 'ENABLED' : 'LOCKED (PAPER)'} sub={`Paper Base: ₹${health?.safety_flags?.paper_trading_initial_capital ?? 50000}`} />
        <StatCard label="B2B Auth Mode" value={features.api_auth_enabled ? 'ENFORCED' : 'OPEN (DEV)'} sub={`SME Finance: ${features.sme_finance ? 'ON' : 'HIDDEN'}`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-5 space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">Hard Non-Overridable Risk Limits</h4>
          {Object.entries(limits).map(([k, v]) => (
            <div key={k} className="flex justify-between font-mono text-xs border-b border-terminal-border/40 pb-1.5">
              <span className="text-text-muted">{k}</span>
              <span className="text-text-primary font-bold">{String(v)}</span>
            </div>
          ))}
        </div>
        <div className="card p-5 space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">Readiness Safety Gates</h4>
          {Object.entries(checks).map(([k, ok]) => (
            <div key={k} className="flex justify-between font-mono text-xs border-b border-terminal-border/40 pb-1.5">
              <span className="text-text-muted">{k}</span>
              <span className={ok ? 'text-fin-pos font-bold' : 'text-fin-neg font-bold'}>{ok ? 'PASS' : 'BLOCKED'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function AlertsView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 10000 })
  const { data: tok } = useSWR(`${API_BASE}/api/v1/token/status`, fetcher, { refreshInterval: 10000 })
  const { data: health } = useSWR(`${API_BASE}/health/detail`, fetcher, { refreshInterval: 10000 })
  const blockers: string[] = readiness?.blocking_reasons || []

  const alerts = [
    {
      level: health?.safety_flags?.emergency_kill_switch_active ? 'critical' : 'ok',
      title: health?.safety_flags?.emergency_kill_switch_active ? 'Emergency Kill Switch ACTIVE' : 'Emergency Kill Switch Clear',
      detail: 'Automated capital protection circuit active across all execution paths.',
    },
    {
      level: tok?.token_valid ? 'ok' : 'warn',
      title: tok?.token_valid ? 'Upstox Daily Access Token Active' : 'Upstox Daily Access Token Missing/Expired',
      detail: tok?.expires_at ? `Valid until ${tok.expires_at}` : 'Refresh token via API Token page before enabling live orders.',
    },
    {
      level: tok?.analytics_token_valid ? 'ok' : 'warn',
      title: tok?.analytics_token_valid ? 'Upstox 1-Year Analytics Token Valid' : 'Analytics Token Missing',
      detail: tok?.analytics_expires_at ? `Valid until ${tok.analytics_expires_at}` : 'Configure UPSTOX_ANALYTICS_TOKEN in .env.',
    },
    ...blockers.map((b) => ({
      level: 'warn',
      title: `Gate Blocker: ${b}`,
      detail: 'Keeps real-money auto-execution locked until resolved (paper & swing CNC active).',
    })),
  ]

  return (
    <div className="card p-5 space-y-3 animate-fade-in">
      <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
        <AlertTriangle size={16} className="text-fin-warn" />
        System Alerts, Safety Locks &amp; Readiness Diagnostics ({alerts.length})
      </h3>
      <div className="space-y-2.5">
        {alerts.map((a, idx) => (
          <div
            key={idx}
            className={clsx(
              'p-3.5 rounded border flex items-start gap-3 text-xs font-mono',
              a.level === 'critical' ? 'bg-fin-neg/10 border-fin-neg/30'
                : a.level === 'warn' ? 'bg-fin-warn/10 border-fin-warn/30'
                  : 'bg-fin-pos/10 border-fin-pos/30'
            )}
          >
            {a.level === 'ok'
              ? <CheckCircle size={15} className="text-fin-pos shrink-0 mt-0.5" />
              : a.level === 'critical'
                ? <XCircle size={15} className="text-fin-neg shrink-0 mt-0.5" />
                : <ShieldAlert size={15} className="text-fin-warn shrink-0 mt-0.5" />}
            <div>
              <div className="font-bold text-text-primary">{a.title}</div>
              <div className="text-text-muted mt-0.5">{a.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
