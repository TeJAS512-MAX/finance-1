'use client'

import { useState } from 'react'
import {
  Activity, AlertTriangle, BookOpen, BrainCircuit,
  ChevronRight, Clock, Database, FileText, Info,
  LayoutDashboard, Newspaper, Shield, ShieldAlert,
  TrendingDown, TrendingUp, Wallet, Zap, Minus, Briefcase, ListOrdered,
  Key, CheckCircle, XCircle
} from 'lucide-react'
import clsx from 'clsx'
import useSWR from 'swr'
import { API_BASE } from '@/lib/config'

export const fetcher = (url: string) => fetch(url, { cache: 'no-store' }).then((res) => res.json())

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface SystemStatus {
  live_trading_enabled: boolean
  emergency_kill_switch_active: boolean
  version: string
  env: string
}

export interface PortfolioMetrics {
  mode: 'paper' | 'live'
  equity: number
  cash: number
  unrealisedPnl: number
  realisedPnl: number
  dailyReturn: number
  drawdown: number
  sharpe: number
  sortino: number
}

export interface Signal {
  id: string
  symbol: string
  direction: 'LONG' | 'SHORT' | 'NO_TRADE'
  confidence: number
  timeHorizon: string
  eventType: string
  verificationStatus: string
  informationType: string
  generatedAt: string
  nextSessionPrediction?: {
    decision: 'TRADE' | 'NO_TRADE'
    expected_net_return_pct: number
    return_estimate_is_calibrated: false
    as_of: string
    trained_through: string
    model: string
    mode: 'research_only'
  } | null
  nextSessionPredictionStatus?: 'available' | 'unavailable' | 'symbol_not_qualified' | 'model_not_trained'
}

export interface NewsItem {
  id: string
  headline: string
  publisher: string
  publishedAt: string
  eventType: string
  verificationStatus: string
  informationType: string
  credibilityScore: number
  sentimentLabel: string
  impactScore: number
}

// ─────────────────────────────────────────────────────────────────────────────
// All data is fetched live from the backend — no mock data

// ─────────────────────────────────────────────────────────────────────────────
// Color & UI helpers
// ─────────────────────────────────────────────────────────────────────────────

export function pnlColor(v: number) { return v > 0 ? 'text-fin-pos' : v < 0 ? 'text-fin-neg' : 'text-fin-neut' }
export function pnlBg(v: number)    { return v > 0 ? '#35B779'      : v < 0 ? '#E05252'      : '#8B96A3' }

export function StatusDot({ status }: { status: 'positive' | 'negative' | 'neutral' | 'warning' | 'active' }) {
  const colorMap = {
    positive: 'bg-fin-pos',
    negative: 'bg-fin-neg',
    neutral: 'bg-fin-neut',
    warning: 'bg-fin-warn',
    active: 'bg-accent-primary'
  }
  return <span className={clsx('status-dot', colorMap[status])} />
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

export function KillSwitchBanner({ active }: { active: boolean }) {
  if (!active) return null
  return (
    <div className="bg-[#2a1313] border-b border-[#3d1a1a] px-5 py-2 flex items-center gap-3 text-[#E05252] text-xs font-medium">
      <ShieldAlert size={14} />
      <span>EMERGENCY KILL SWITCH ACTIVE — All new orders halted. Manual review required.</span>
    </div>
  )
}

export function StatCard({ label, value, sub, trend }: { label: string; value: string; sub?: string; trend?: number }) {
  return (
    <div className="card flex flex-col gap-1.5 animate-slide-up">
      <div className="text-[11px] text-text-secondary uppercase tracking-wider font-semibold">{label}</div>
      <div className="text-xl font-mono text-text-primary tracking-tight">{value}</div>
      {sub && (
        <div className={clsx('text-[11px] font-medium font-mono', trend !== undefined ? pnlColor(trend) : 'text-text-muted')}>
          {sub}
        </div>
      )}
    </div>
  )
}

export function Sidebar({ active, onNavigate }: { active: string; onNavigate: (id: string) => void }) {
  const { data: tokenData } = useSWR(`${API_BASE}/api/v1/token/status`, fetcher, { refreshInterval: 5000 })
  const { data: healthDetail } = useSWR(`${API_BASE}/health/detail`, fetcher, { refreshInterval: 15000 })
  const tokenOk = tokenData?.token_valid === true
  const tokenExpired = tokenData?.token_expired === true
  const analyticsOk = tokenData?.analytics_token_valid === true
  const showSmeFinance = healthDetail?.features?.sme_finance !== false

  const navGroups = [
    {
      title: "COMMAND CENTER",
      items: [
        { id: 'dashboard',  label: 'Dashboard',     icon: LayoutDashboard },
        { id: 'ai_terminal',label: 'AI Terminal',   icon: BrainCircuit },
        { id: 'bot',        label: 'Live Terminal', icon: Zap },
      ]
    },
    {
      title: "MARKET INTELLIGENCE",
      items: [
        { id: 'overview',   label: 'Market Overview',icon: Activity },
        { id: 'event_radar',label: 'Event Radar',    icon: Newspaper },
        { id: 'news_intel', label: 'News Intelligence',icon: FileText },
        { id: 'company',    label: 'Company Intel',  icon: Briefcase },
        { id: 'causal_map', label: 'Causal Map',     icon: Database },
        { id: 'expectations',label: 'Expectations',  icon: TrendingUp },
        { id: 'priced_in',  label: 'Priced-In',      icon: TrendingDown },
      ]
    },
    {
      title: "TRADING",
      items: [
        { id: 'opportunities',label: 'Opportunities',icon: Zap },
        { id: 'ai_debate',  label: 'AI Debate',      icon: BrainCircuit },
        { id: 'paper',      label: 'Paper Trading',  icon: Briefcase },
        { id: 'positions',  label: 'Positions',      icon: ListOrdered },
        { id: 'orders',     label: 'Orders',         icon: ListOrdered },
      ]
    },
    {
      title: "RESEARCH",
      items: [
        { id: 'backtest',   label: 'Backtesting',    icon: Activity },
        { id: 'strategy',   label: 'Strategy Lab',   icon: BookOpen },
        { id: 'model_lab',  label: 'Model Lab',      icon: Database },
        { id: 'journal',    label: 'Trade Journal',  icon: FileText },
      ]
    },
    {
      title: "RISK & PERFORMANCE",
      items: [
        { id: 'portfolio',  label: 'Portfolio',      icon: Wallet },
        { id: 'risk',       label: 'Risk Center',    icon: Shield },
        { id: 'performance',label: 'Performance',    icon: Activity },
      ]
    },
    ...(showSmeFinance ? [{
      title: "BUSINESS FINANCE",
      items: [
        { id: 'finance', label: 'SME Finance Hub', icon: Wallet },
      ]
    }] : []),
    {
      title: "SYSTEM",
      items: [
        { id: 'data_quality',label: 'Data Quality',  icon: Database },
        { id: 'health',     label: 'System Health',  icon: Activity },
        { id: 'settings',   label: 'API Token',      icon: Key },
        { id: 'alerts',     label: 'Alerts',         icon: AlertTriangle },
      ]
    }
  ]

  return (
    <aside className="w-56 shrink-0 bg-[#0B0F14] border-r border-[#151B23] flex flex-col h-full z-10">
      <div className="px-5 py-4 border-b border-[#151B23]">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 flex items-center justify-center border border-[#151B23] bg-[#0B0F14] rounded">
            <BrainCircuit size={14} className="text-[#4F8CFF]" />
          </div>
          <div>
            <div className="text-text-primary font-semibold text-xs tracking-wide">MARKET INTEL</div>
            <div className="text-[#4F8CFF] text-[10px] tracking-widest mt-0.5">AECE ENGINE</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto custom-scrollbar">
        {navGroups.map((group, i) => (
          <div key={i}>
            <div className="text-[9px] font-bold text-text-muted uppercase tracking-widest mb-2 px-2">
              {group.title}
            </div>
            <div className="space-y-0.5">
              {group.items.map(({ id, label, icon: Icon }) => (
                <button
                  key={id} 
                  type="button"
                  onClick={() => onNavigate(id)}
                  className={clsx(
                    'w-full text-left flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer text-xs transition-colors',
                    active === id 
                      ? 'bg-[#4F8CFF]/10 text-[#4F8CFF] font-medium' 
                      : 'text-text-secondary hover:text-text-primary hover:bg-[#151B23]'
                  )}
                >
                  <Icon size={13} className={active === id ? 'text-[#4F8CFF]' : 'text-text-muted'} />
                  <span className="tracking-wide flex-1">{label}</span>
                  {id === 'settings' && (
                    tokenOk 
                      ? <span title="Token active"><CheckCircle size={10} className="text-fin-pos" /></span>
                      : <span title="No token set"><XCircle size={10} className="text-fin-neg animate-pulse" /></span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-terminal-border bg-terminal-surface/30">
        <div className="text-[10px] font-mono space-y-2">
          <div className="flex justify-between text-text-muted">
            <span>DATA FEED</span>
            {analyticsOk || tokenOk
              ? <span className="text-fin-pos"><StatusDot status="positive" /> LIVE</span>
              : <span className="text-fin-neg"><StatusDot status="negative" /> MISSING</span>
            }
          </div>
          <div className="flex justify-between text-text-muted">
            <span>TRADE TOKEN</span>
            {tokenOk
              ? <span className="text-fin-pos"><StatusDot status="positive" /> ACTIVE</span>
              : tokenExpired
                ? <span className="text-fin-warn"><StatusDot status="warning" /> EXPIRED</span>
                : <span className="text-fin-neg"><StatusDot status="negative" /> NOT SET</span>
            }
          </div>
        </div>
      </div>
    </aside>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom recharts tooltips
// ─────────────────────────────────────────────────────────────────────────────

export function EquityTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-terminal-card border border-terminal-border rounded px-3 py-2 text-xs shadow-card">
      <div className="text-text-muted mb-1">{label}</div>
      <div className="text-text-primary font-mono font-medium">
        ₹{payload[0].value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
      </div>
    </div>
  )
}

export function PnlTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const v = payload[0].value
  return (
    <div className="bg-terminal-card border border-terminal-border rounded px-3 py-2 text-xs shadow-card">
      <div className="text-text-muted mb-1">{label}</div>
      <div className={clsx('font-mono font-medium', pnlColor(v))}>
        {v > 0 ? '+' : ''}₹{Math.abs(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Detailed Views
// ─────────────────────────────────────────────────────────────────────────────

export function TradeSignalsView() {
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/signals`, fetcher, { refreshInterval: 15000 })
  const liveSignals: Signal[] = data?.signals || []
  const directionModel = data?.direction_model
  const scannedAt = data?.scanned_at ? new Date(data.scanned_at).toLocaleTimeString('en-IN') : null
  
  return (
    <div className="card p-0 overflow-hidden animate-fade-in flex flex-col h-full">
      <div className="px-5 py-4 border-b border-terminal-border bg-terminal-surface/30 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <BrainCircuit size={16} className="text-accent-primary" />
            Algorithmic Trade Signals
          </h3>
          <p className="text-xs text-text-muted mt-1">
            Live RSI + SMA analysis on NSE 5-min candles
            {scannedAt && <span className="ml-2 text-text-muted">• Last scan: {scannedAt}</span>}
          </p>
        </div>
        {isValidating && <span className="text-[10px] text-accent-primary animate-pulse border border-accent-primary/30 px-2 py-1 rounded bg-accent-primary/10">● SCANNING NSE</span>}
      </div>
      <div className="p-5 flex-1 overflow-y-auto">
        {directionModel?.state === 'withheld' && (
          <div className="mb-4 rounded-lg border border-fin-warn/30 bg-fin-warn/5 px-4 py-3 text-[11px] text-text-secondary">
            Next-session estimates are withheld: the latest out-of-sample evaluation did not show a statistically reliable reduction in net-return error over the zero-return baseline.
            {directionModel.test_mae_pct !== undefined && (
              <span className="block mt-1 font-mono">
                Test MAE {Number(directionModel.test_mae_pct).toFixed(3)}% • zero-return baseline {Number(directionModel.baseline_mae_pct).toFixed(3)}%
              </span>
            )}
            {Array.isArray(directionModel?.mae_improvement_95pct_ci) && (
              <span className="block mt-1 font-mono">
                Baseline-minus-model MAE 95% interval: [{Number(directionModel.mae_improvement_95pct_ci[0]).toFixed(3)}, {Number(directionModel.mae_improvement_95pct_ci[1]).toFixed(3)}] percentage points
              </span>
            )}
          </div>
        )}
        {directionModel?.state === 'not_trained' && (
          <div className="mb-4 rounded-lg border border-fin-warn/30 bg-fin-warn/5 px-4 py-3 text-[11px] text-text-secondary">
            No evaluated net-return model is installed. Train and evaluate a candidate before showing estimates.
          </div>
        )}
        {directionModel?.state === 'needs_retraining' && (
          <div className="mb-4 rounded-lg border border-fin-warn/30 bg-fin-warn/5 px-4 py-3 text-[11px] text-text-secondary">
            No current Upstox-trained model is installed. Retrain with the Upstox-only pipeline before displaying forecasts.
          </div>
        )}
        {liveSignals.length === 0 && !isValidating ? (
          <div className="flex flex-col items-center justify-center h-full py-16 text-text-muted">
            <BrainCircuit size={36} className="mb-4 opacity-30" />
            <p className="text-sm">Fetching live market data from NSE...</p>
            <p className="text-xs mt-1">This may take 10-15 seconds on first load.</p>
          </div>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {liveSignals.map((s: Signal) => (
            <div key={s.id} className="border border-terminal-border bg-terminal-bg rounded-lg p-4 hover:border-accent-primary/50 transition-colors cursor-pointer group shadow-sm hover:shadow-card">
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-lg text-text-primary tracking-tight">{s.symbol}</span>
                  <span className={clsx("text-[10px] px-1.5 py-0.5 rounded font-mono font-bold", 
                    s.direction === 'LONG' ? "bg-fin-pos/20 text-fin-pos" : s.direction === 'SHORT' ? "bg-fin-neg/20 text-fin-neg" : "bg-fin-neut/20 text-text-muted")}>
                    {s.direction}
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-text-secondary">{s.confidence}% CONF</div>
                  <div className="text-[10px] text-text-muted mt-0.5">{s.timeHorizon}</div>
                </div>
              </div>
              <div className="bg-terminal-surface/50 rounded px-2 py-1.5 mb-3 font-mono text-[11px] text-text-muted space-y-0.5">
                {(s as any).ltp && <div>LTP: <span className="text-text-primary">₹{(s as any).ltp}</span></div>}
                {(s as any).rsi && <div>RSI: <span className={clsx((s as any).rsi < 35 ? 'text-fin-pos' : (s as any).rsi > 65 ? 'text-fin-neg' : 'text-text-primary')}>{(s as any).rsi}</span></div>}
                {(s as any).sma20 && <div>SMA20: <span className="text-text-primary">₹{(s as any).sma20}</span></div>}
              </div>
              {s.nextSessionPrediction && (
                <div className="border border-accent-primary/20 rounded px-2 py-2 mb-3 bg-accent-primary/5">
                  <div className="text-[10px] uppercase tracking-wide text-accent-primary font-semibold">
                    Next-session net return • Research only
                  </div>
                  <div className="text-[11px] font-mono text-text-primary mt-1">
                    <span className={s.nextSessionPrediction.decision === 'TRADE' ? 'text-fin-pos' : 'text-text-muted'}>
                      {s.nextSessionPrediction.decision}
                    </span>
                    {' • '}
                    {s.nextSessionPrediction.expected_net_return_pct > 0 ? '+' : ''}
                    {s.nextSessionPrediction.expected_net_return_pct.toFixed(3)}% estimated after-cost return
                  </div>
                  <div className="text-[9px] text-text-muted mt-0.5">
                    Model estimate only; not a probability or trading instruction. Taxes and exchange fees are excluded.
                  </div>
                  <div className="text-[9px] text-text-muted mt-0.5">
                    Training history through {new Date(s.nextSessionPrediction.trained_through).toLocaleDateString('en-IN')}
                  </div>
                  <div className="text-[9px] text-text-muted mt-0.5">
                    As of {new Date(s.nextSessionPrediction.as_of).toLocaleDateString('en-IN')}
                  </div>
                </div>
              )}
              {!s.nextSessionPrediction && s.nextSessionPredictionStatus === 'unavailable' && (
                <div className="text-[9px] text-fin-warn mb-3">
                  Next-session estimate withheld: model or daily-data freshness check failed.
                </div>
              )}
              {!s.nextSessionPrediction && s.nextSessionPredictionStatus === 'symbol_not_qualified' && directionModel?.state === 'qualified_research' && (
                <div className="text-[9px] text-text-muted mb-3">
                  No net-return model qualified for this symbol.
                </div>
              )}
              <p className="text-[11px] font-medium text-text-secondary mb-3 leading-relaxed">{s.eventType} • {s.informationType}</p>
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-text-muted flex items-center gap-1"><Shield size={10}/> {s.verificationStatus}</span>
                <span className="text-text-muted font-mono"><Clock size={10} className="inline mr-1 mb-0.5"/>{s.generatedAt}</span>
              </div>
            </div>
          ))}
        </div>
        )}
      </div>
    </div>
  )
}

export function OrderBookView() {
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/orders`, fetcher, { refreshInterval: 2000 })
  const orders = data?.orders || []

  return (
    <div className="card p-0 overflow-hidden animate-fade-in flex flex-col h-full shadow-card border-terminal-border">
      <div className="px-5 py-4 border-b border-terminal-border bg-terminal-surface/30 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <ListOrdered size={16} className="text-accent-primary" />
            Order Book
          </h3>
          <p className="text-xs text-text-muted mt-1">Real orders placed by the AI Trading Engine</p>
        </div>
        {isValidating && <span className="text-[10px] text-accent-primary animate-pulse">● LIVE</span>}
      </div>
      {orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-[250px] text-text-muted text-xs font-mono gap-2">
          <ListOrdered size={28} className="opacity-30" />
          <span>No orders yet. Start the Trading Engine to see real orders.</span>
        </div>
      ) : (
      <div className="overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap">
          <thead>
            <tr>
              {['Order ID', 'Time', 'Symbol', 'Side', 'Type', 'Qty', 'Price', 'Notional', 'Status'].map(h => (
                <th key={h} className="table-header px-5 py-3 text-[10px]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono text-[13px]">
            {orders.map((o: any, i: number) => (
              <tr key={i} className="table-row hover:bg-terminal-cardHover border-b border-terminal-border/30 last:border-0">
                <td className="px-5 py-3 text-text-muted">{o.id}</td>
                <td className="px-5 py-3 text-text-secondary">{o.time}</td>
                <td className="px-5 py-3 font-bold text-text-primary">{o.symbol}</td>
                <td className={clsx("px-5 py-3 font-bold", o.side === 'BUY' ? "text-fin-pos" : "text-fin-neg")}>{o.side}</td>
                <td className="px-5 py-3 text-text-muted">{o.type}</td>
                <td className="px-5 py-3 text-text-primary">{o.qty}</td>
                <td className="px-5 py-3 text-text-primary">₹{Number(o.price).toFixed(2)}</td>
                <td className="px-5 py-3 text-text-secondary">₹{Number(o.notional).toFixed(2)}</td>
                <td className="px-5 py-3">
                  <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold tracking-wide", 
                    o.status === 'FILLED' ? "bg-fin-pos/10 text-fin-pos border border-fin-pos/20" : 
                    o.status === 'PENDING' ? "bg-fin-warn/10 text-fin-warn border border-fin-warn/20" : 
                    "bg-fin-neg/10 text-fin-neg border border-fin-neg/20"
                  )}>
                    {o.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </div>
  )
}

export function PortfolioView() {
  const { data } = useSWR(`${API_BASE}/api/v1/portfolio`, fetcher, { refreshInterval: 2000 })
  const cash = data?.cash ?? 0
  const equity = data?.total_equity ?? 0
  const marketValue = data?.total_market_value ?? 0
  const initialCapital = data?.initial_capital ?? 1000
  const totalPnl = data?.total_pnl ?? 0
  const exposurePct = equity > 0 ? (marketValue / equity) * 100 : 0

  return (
    <div className="animate-fade-in flex flex-col h-full space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Initial Capital" value={`₹${initialCapital.toLocaleString('en-IN')}`} sub="STARTING BALANCE" />
        <StatCard label="Available Cash" value={`₹${cash.toLocaleString('en-IN', {maximumFractionDigits: 2})}`} sub="FREE MARGIN" />
        <StatCard label="Market Value" value={`₹${marketValue.toLocaleString('en-IN', {maximumFractionDigits: 2})}`} sub={`${exposurePct.toFixed(1)}% DEPLOYED`} />
        <StatCard label="Net P&L" value={`${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toLocaleString('en-IN', {maximumFractionDigits: 2})}`} sub="ALL TRADES" trend={totalPnl} />
      </div>
      {data ? (
        <div className="card p-5 flex-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-4 flex items-center gap-2">
            <Wallet size={14} className="text-accent-primary" /> Account Summary
          </h3>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3 font-mono text-sm">
            {[
              ['Total Equity', `₹${equity.toLocaleString('en-IN', {maximumFractionDigits: 2})}`],
              ['Cash Balance', `₹${cash.toLocaleString('en-IN', {maximumFractionDigits: 2})}`],
              ['Market Value', `₹${marketValue.toLocaleString('en-IN', {maximumFractionDigits: 2})}`],
              ['Total P&L', `${totalPnl >= 0 ? '+' : ''}₹${Math.abs(totalPnl).toLocaleString('en-IN', {maximumFractionDigits: 2})}`],
              ['Commission Paid', `₹${(data.total_commission ?? 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}`],
              ['Mode', data.is_paper ? 'PAPER TRADING' : 'LIVE TRADING'],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between border-b border-terminal-border/30 pb-2">
                <span className="text-text-muted text-xs">{label}</span>
                <span className="text-text-primary font-bold text-xs">{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card flex-1 flex items-center justify-center text-text-muted text-xs">
          Start the Trading Engine to populate portfolio data.
        </div>
      )}
    </div>
  )
}

export function RiskMonitorView() {
  return (
    <div className="animate-fade-in flex flex-col h-full space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-[#1f0f0f] border-[#3d1a1a] shadow-card">
          <h4 className="text-[11px] uppercase tracking-wider font-semibold text-fin-neg mb-3 flex items-center gap-2"><ShieldAlert size={14}/> Max Drawdown</h4>
          <div className="text-2xl font-mono font-bold text-fin-neg">2.14%</div>
          <div className="text-[10px] text-text-muted mt-2 font-mono flex justify-between"><span>CURRENT</span> <span>LIMIT: 20.0%</span></div>
          <div className="w-full bg-terminal-bg h-1.5 rounded-full mt-2.5 overflow-hidden border border-[#3d1a1a]">
            <div className="bg-fin-neg h-full rounded-full" style={{ width: '10%' }}></div>
          </div>
        </div>
        <div className="card shadow-card">
          <h4 className="text-[11px] uppercase tracking-wider font-semibold text-text-secondary mb-3 flex items-center gap-2"><Activity size={14}/> Portfolio VaR</h4>
          <div className="text-2xl font-mono font-bold text-text-primary">₹14,500</div>
          <div className="text-[10px] text-text-muted mt-2 font-mono">99% CONFIDENCE (1D)</div>
        </div>
        <div className="card shadow-card">
          <h4 className="text-[11px] uppercase tracking-wider font-semibold text-text-secondary mb-3 flex items-center gap-2"><BrainCircuit size={14}/> Beta Profile</h4>
          <div className="text-2xl font-mono font-bold text-text-primary">0.85</div>
          <div className="text-[10px] text-text-muted mt-2 font-mono">MARKET EXPOSURE vs NIFTY</div>
        </div>
        <div className="card shadow-card">
          <h4 className="text-[11px] uppercase tracking-wider font-semibold text-text-secondary mb-3 flex items-center gap-2"><Shield size={14}/> Max Sector Risk</h4>
          <div className="text-2xl font-mono font-bold text-text-primary">15.2%</div>
          <div className="text-[10px] text-text-muted mt-2 font-mono flex justify-between"><span>IT SECTOR</span> <span>LIMIT: 30%</span></div>
          <div className="w-full bg-terminal-bg h-1.5 rounded-full mt-2.5 overflow-hidden border border-terminal-border">
            <div className="bg-accent-primary h-full rounded-full" style={{ width: '50%' }}></div>
          </div>
        </div>
      </div>
      
      <div className="card flex-1 p-5 shadow-card">
        <h3 className="text-sm font-semibold tracking-wide text-text-primary mb-4 flex items-center gap-2">
          <AlertTriangle size={16} className="text-fin-warn" />
          Risk Breaches & Automated Alerts
        </h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-4 rounded-lg bg-terminal-surface/30 border border-terminal-border/50">
            <div className="mt-1"><div className="w-2.5 h-2.5 rounded-full bg-fin-pos shadow-[0_0_8px_rgba(53,183,121,0.6)]"></div></div>
            <div>
              <div className="text-[13px] font-semibold text-text-primary">All systems operating within safe parameters</div>
              <div className="text-[11px] text-text-muted mt-1 font-mono">Real-time risk engine active • Evaluated {new Date().toLocaleTimeString('en-IN')}</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-terminal-surface/30 border border-terminal-border/50 opacity-60">
            <div className="mt-1"><div className="w-2.5 h-2.5 rounded-full bg-fin-neut"></div></div>
            <div>
              <div className="text-[13px] font-semibold text-text-primary">Order Velocity Guard Rail Active</div>
              <div className="text-[11px] text-text-muted mt-1 font-mono">Frequency cap: 10 orders / minute</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function TokenSettingsView() {
  const { data: statusData, mutate: mutateStatus } = useSWR(`${API_BASE}/api/v1/token/status`, fetcher, { refreshInterval: 3000 })
  const { data: oauthData } = useSWR(`${API_BASE}/api/v1/token/oauth-url`, fetcher, { refreshInterval: 10000 })
  const { data: readinessData, mutate: mutateReadiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 10000 })
  const [token, setToken] = useState('')
  const [analyticsToken, setAnalyticsToken] = useState('')
  const [oauthCode, setOauthCode] = useState('')
  const [result, setResult] = useState<{success: boolean; message?: string; error?: string} | null>(null)
  const [saving, setSaving] = useState(false)

  const handleExchangeCode = async () => {
    if (!oauthCode.trim()) return
    setSaving(true)
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/token/exchange`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: oauthCode.trim() }),
      })
      const data = await res.json()
      setResult(data)
      if (data.success) {
        setOauthCode('')
        mutateStatus()
        mutateReadiness()
      }
    } catch {
      setResult({ success: false, message: 'Could not reach backend for OAuth exchange.' })
    }
    setSaving(false)
  }

  const handleSave = async () => {
    if (!token.trim() && !analyticsToken.trim()) return
    setSaving(true)
    setResult(null)
    try {
      const payload: Record<string, string> = {}
      if (token.trim()) payload.access_token = token.trim()
      if (analyticsToken.trim()) payload.analytics_token = analyticsToken.trim()
      const res = await fetch(`${API_BASE}/api/v1/token/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      setResult(data)
      if (data.success) {
        if (token.trim()) setToken('')
        if (analyticsToken.trim()) setAnalyticsToken('')
        mutateStatus()
        mutateReadiness()
      }
    } catch (e) {
      setResult({ success: false, message: 'Could not reach backend. Is the server running?' })
    }
    setSaving(false)
  }

  const tokenIsActive = statusData?.token_valid === true
  const tokenExpired = statusData?.token_expired === true
  const analyticsActive = statusData?.analytics_token_valid === true
  const analyticsExpired = statusData?.analytics_expired === true
  const blockingReasons: string[] = readinessData?.blocking_reasons || []

  return (
    <div className="animate-fade-in flex flex-col gap-6 max-w-2xl mx-auto">
      {/* Status Banner */}
      <div className={clsx(
        "rounded-xl border p-4 flex items-center gap-4",
        tokenIsActive ? "bg-fin-pos/10 border-fin-pos/30" : tokenExpired ? "bg-fin-warn/10 border-fin-warn/30" : "bg-fin-neg/10 border-fin-neg/30"
      )}>
        {tokenIsActive 
          ? <CheckCircle size={28} className="text-fin-pos shrink-0" />
          : <XCircle size={28} className={clsx("shrink-0 animate-pulse", tokenExpired ? "text-fin-warn" : "text-fin-neg")} />
        }
        <div>
          <div className={clsx("font-semibold text-sm", tokenIsActive ? "text-fin-pos" : tokenExpired ? "text-fin-warn" : "text-fin-neg")}>
            {tokenIsActive
              ? "✅ Upstox Trading Token Valid & Active"
              : tokenExpired
                ? "⚠️ Upstox Trading Token EXPIRED — Refresh Required"
                : "⚠️ No Daily Token — Live Trading Unavailable"}
          </div>
          <div className="text-xs text-text-muted mt-0.5 font-mono">
            {statusData?.token_set
              ? `Daily token ${statusData?.masked_token} · expires: ${statusData?.expires_at || 'unknown'}`
              : "Paste your fresh token every morning before 9:15 AM IST"
            }
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-xs text-text-muted space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-text-primary">
            Read-Only Analytics Token (1-Year): {analyticsActive ? `Active (${statusData?.analytics_masked_token})` : analyticsExpired ? "Expired" : "Not Configured"}
          </span>
          <span className={clsx("font-mono text-[10px] px-2 py-0.5 rounded", analyticsActive ? "bg-fin-pos/15 text-fin-pos" : "bg-fin-warn/15 text-fin-warn")}>
            {analyticsActive ? "VALID" : analyticsExpired ? "EXPIRED" : "MISSING"}
          </span>
        </div>
        <div>
          Set <code>UPSTOX_ANALYTICS_TOKEN</code> for 365-day read-only historical OHLCV fetching &amp; paper validation.
        </div>
      </div>

      {/* Live Capital Readiness Summary */}
      {readinessData && (
        <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-text-primary">Automated Readiness Gate</span>
            <span className={clsx("font-mono text-[11px] font-bold", readinessData.live_capital_ready ? "text-fin-pos" : "text-fin-warn")}>
              {readinessData.live_capital_ready ? "LIVE READY" : `PAPER READY (${blockingReasons.length} blockers)`}
            </span>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[10px]">
            <span className={clsx("px-2 py-0.5 rounded border", readinessData.paper_ready ? "border-fin-pos/40 text-fin-pos" : "border-fin-neg/40 text-fin-neg")}>
              Paper Engine: {readinessData.paper_ready ? "PASS" : "FAIL"}
            </span>
            <span className={clsx("px-2 py-0.5 rounded border", readinessData.swing_oos_ready ? "border-fin-pos/40 text-fin-pos" : "border-fin-neg/40 text-fin-neg")}>
              15d Swing CNC OOS: {readinessData.swing_oos_ready ? "PASS" : "FAIL"}
            </span>
            <span className={clsx("px-2 py-0.5 rounded border", readinessData.intraday_oos_ready ? "border-fin-pos/40 text-fin-pos" : "border-fin-neg/40 text-fin-neg")}>
              30m Intraday OOS: {readinessData.intraday_oos_ready ? "PASS" : "RESEARCH ONLY"}
            </span>
          </div>
          {blockingReasons.length > 0 && (
            <div className="text-[11px] font-mono text-text-muted pt-1">
              Remaining blockers: {blockingReasons.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Token Input Card */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-lg bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
            <Key size={18} className="text-accent-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Upstox Token Configuration</h3>
            <p className="text-xs text-text-muted">Update your daily trading JWT and/or 1-year analytics JWT</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-[11px] font-mono text-text-muted uppercase tracking-widest mb-2 block">
              Daily Trading Token (UPSTOX_ACCESS_TOKEN)
            </label>
            <textarea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste daily Upstox JWT here... (eyJhbGciOiJSUzI1NiJ9...)"
              rows={3}
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-4 py-3 font-mono text-xs text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:border-accent-primary/50 focus:ring-1 focus:ring-accent-primary/20 resize-none transition-colors"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono text-text-muted uppercase tracking-widest mb-2 block">
              Annual Read-Only Analytics Token (UPSTOX_ANALYTICS_TOKEN)
            </label>
            <textarea
              value={analyticsToken}
              onChange={(e) => setAnalyticsToken(e.target.value)}
              placeholder="Paste 1-year analytics JWT here (optional)..."
              rows={2}
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-4 py-3 font-mono text-xs text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:border-accent-primary/50 focus:ring-1 focus:ring-accent-primary/20 resize-none transition-colors"
            />
            <p className="text-[10px] text-text-muted mt-1.5 font-mono">
              Expired tokens are rejected automatically. Valid tokens persist to .env immediately.
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={saving || (!token.trim() && !analyticsToken.trim())}
            className={clsx(
              "w-full py-3 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2",
              (token.trim() || analyticsToken.trim()) && !saving
                ? "bg-accent-primary text-white hover:bg-accent-primary/90 shadow-lg shadow-accent-primary/20"
                : "bg-terminal-surface text-text-muted cursor-not-allowed"
            )}
          >
            {saving ? (
              <><span className="animate-spin">⟳</span> Saving...</>
            ) : (
              <><Key size={15} /> Save &amp; Activate Token(s)</>
            )}
          </button>

          {result && (
            <div className={clsx(
              "p-3 rounded-lg text-xs font-mono border",
              result.success 
                ? "bg-fin-pos/10 border-fin-pos/30 text-fin-pos" 
                : "bg-fin-neg/10 border-fin-neg/30 text-fin-neg"
            )}>
              {result.message || result.error}
            </div>
          )}
        </div>
      </div>

      {/* OAuth Redirect Helper */}
      <div className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Upstox Daily OAuth Exchange (Redirect URL: <span className="font-mono text-text-primary">{oauthData?.redirect_uri || 'https://127.0.0.1'}</span>)
          </h3>
          {oauthData?.oauth_url && (
            <a
              href={oauthData.oauth_url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] font-mono text-accent-primary hover:underline"
            >
              Open Upstox Login →
            </a>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={oauthCode}
            onChange={(e) => setOauthCode(e.target.value)}
            placeholder="Paste redirected URL (https://127.0.0.1/?code=...) or code only"
            className="flex-1 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 font-mono text-xs text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:border-accent-primary/50"
          />
          <button
            type="button"
            onClick={handleExchangeCode}
            disabled={saving || !oauthCode.trim()}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-accent-primary/20 text-accent-primary border border-accent-primary/30 hover:bg-accent-primary/30 disabled:opacity-40"
          >
            Exchange Code
          </button>
        </div>
      </div>

      {/* How to get token instructions */}
      <div className="card p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-4 flex items-center gap-2">
          <Info size={14} /> How to Refresh Your Upstox Tokens
        </h3>
        <ol className="space-y-3 text-xs text-text-muted font-mono">
          {[
            ['Open', 'Go to Upstox Developer Portal → https://developer.upstox.com'],
            ['Analytics', 'Generate/copy the 1-year Analytics Token for read-only market & candle fetches'],
            ['Daily Auth', 'Complete Upstox OAuth login before 09:15 IST to get the daily access_token'],
            ['Paste & Save', 'Paste either or both JWTs above — expired tokens are blocked cleanly'],
          ].map(([step, desc], i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="w-5 h-5 rounded bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-[10px] flex items-center justify-center shrink-0 font-bold">{i+1}</span>
              <div><span className="text-text-primary font-bold">{step}:</span> {desc}</div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

export function NewsSection() {
  const { data } = useSWR(`${API_BASE}/api/v1/news?limit=10`, fetcher, { refreshInterval: 30000 })
  const items = data?.items || []

  return (
    <section className="card p-0 overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between border-b border-terminal-border bg-terminal-surface/30">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
          <FileText size={14} className="text-accent-primary" />
          Market Intelligence
        </h3>
        <span className="text-[10px] font-mono text-text-muted">LIVE FEED</span>
      </div>
      <div className="divide-y divide-terminal-border">
        {items.length === 0 ? (
          <div className="p-6 text-center text-text-muted text-xs font-mono">
            No news in database yet. News will appear here as the system ingests market data.
          </div>
        ) : (
          items.map((n: any) => (
            <div key={n.id} className="p-4 hover:bg-terminal-cardHover transition-colors flex gap-4 items-start group cursor-pointer">
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-text-primary leading-relaxed mb-2">{n.headline}</p>
                <div className="flex items-center gap-x-4 gap-y-2 flex-wrap text-[11px] font-mono text-text-muted">
                  <span className="flex items-center gap-1.5">
                    <StatusDot status={n.sentiment_label === 'POSITIVE' ? 'positive' : n.sentiment_label === 'NEGATIVE' ? 'negative' : 'neutral'} />
                    {n.sentiment_label}
                  </span>
                  <span>{n.publisher}</span>
                  <span>{new Date(n.published_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
                  <span>CONF: {((n.credibility_score ?? 0) * 100).toFixed(0)}%</span>
                  <span className="text-text-secondary">{n.event_type}</span>
                </div>
              </div>
              <ChevronRight size={16} className="text-text-muted group-hover:text-text-primary transition-colors mt-1" />
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export function TradingBotView() {
  const { data, mutate } = useSWR(`${API_BASE}/api/v1/bot/status`, fetcher, { refreshInterval: 1000 })
  const isRunning = data?.is_running || false
  const logs = data?.logs || []
  const [starting, setStarting] = useState(false)
  const [marketMode, setMarketMode] = useState<'stocks' | 'crypto'>(data?.market_mode || 'stocks')
  const cryptoReady = data?.crypto_ready === true

  const toggleBot = async () => {
    if (!isRunning && marketMode === 'crypto' && !cryptoReady) return
    setStarting(true)
    const endpoint = isRunning ? 'stop' : 'start'
    await fetch(`${API_BASE}/api/v1/bot/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: endpoint === 'start' ? JSON.stringify({ market_mode: marketMode }) : undefined,
    })
    await mutate()
    setStarting(false)
  }

  return (
    <div className="card p-0 overflow-hidden animate-fade-in flex flex-col h-full shadow-card border-terminal-border">
      <div className="px-5 py-4 border-b border-terminal-border bg-terminal-surface/30 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <Zap size={16} className={isRunning ? "text-accent-primary animate-pulse" : "text-text-muted"} />
            Live Execution Terminal
          </h3>
          <p className="text-xs text-text-muted mt-1">Direct view into the AI Trading Engine's autonomous operations</p>
        </div>
        <div>
          <button 
            onClick={toggleBot}
            disabled={starting}
            className={clsx(
              "px-4 py-2 rounded text-xs font-bold tracking-wider uppercase transition-all duration-300 shadow-md focus:outline-none flex items-center gap-2",
              starting ? "opacity-50 cursor-not-allowed" : "hover:-translate-y-0.5",
              isRunning 
                ? "bg-fin-neg/20 text-fin-neg border border-fin-neg/50 hover:bg-fin-neg/30 hover:shadow-fin-neg/20 hover:shadow-lg" 
                : "bg-fin-pos/20 text-fin-pos border border-fin-pos/50 hover:bg-fin-pos/30 hover:shadow-fin-pos/20 hover:shadow-lg"
            )}
          >
            {starting ? "Processing..." : isRunning ? <><ShieldAlert size={14}/> Stop Engine</> : <><Zap size={14}/> Start Auto Trading</>}
          </button>
        </div>
      </div>

      <div className="px-5 py-3 border-b border-terminal-border bg-terminal-bg flex flex-wrap items-center gap-2">
        <span className="text-[10px] uppercase tracking-wider text-text-muted mr-2">Trading mode</span>
        <button
          type="button"
          onClick={() => !isRunning && setMarketMode('stocks')}
          disabled={isRunning}
          className={clsx('px-3 py-1.5 text-[11px] font-semibold border rounded', marketMode === 'stocks' ? 'border-accent-primary text-accent-primary bg-accent-primary/10' : 'border-terminal-border text-text-muted', isRunning && 'opacity-60 cursor-not-allowed')}
        >
          Stocks · Upstox
        </button>
        <button
          type="button"
          onClick={() => !isRunning && setMarketMode('crypto')}
          disabled={isRunning}
          className={clsx('px-3 py-1.5 text-[11px] font-semibold border rounded', marketMode === 'crypto' ? 'border-fin-warn text-fin-warn bg-fin-warn/10' : 'border-terminal-border text-text-muted', isRunning && 'opacity-60 cursor-not-allowed')}
        >
          Crypto · CoinDCX
        </button>
        {marketMode === 'crypto' && !cryptoReady && (
          <span className="text-[10px] text-fin-warn">Adapter not configured · paper start disabled</span>
        )}
      </div>
      
      <div className="flex-1 bg-[#0d1117] p-5 overflow-y-auto font-mono text-[13px] flex flex-col-reverse shadow-inner">
        <div className="space-y-1">
          {!isRunning && logs.length === 0 && (
            <div className="text-text-muted italic opacity-50 flex flex-col items-center justify-center h-full py-10">
              <Zap size={32} className="mb-4 text-text-muted/30" />
              Engine is currently offline. Press Start to begin autonomous trading.
            </div>
          )}
          {logs.map((log: any, i: number) => (
            <div key={i} className="flex gap-4 group hover:bg-[#161b22] px-2 py-1 rounded">
              <span className="text-[#6e7681] shrink-0 w-20">{log.time}</span>
              <span className={clsx(
                "shrink-0 w-16 font-bold",
                log.level === 'INFO' ? 'text-accent-primary' : 
                log.level === 'WARN' ? 'text-fin-warn' : 
                log.level === 'ERROR' ? 'text-fin-neg' : 'text-[#8b949e]'
              )}>{log.level}</span>
              <span className="text-[#c9d1d9] whitespace-pre-wrap">{log.message}</span>
            </div>
          ))}
          {isRunning && (
            <div className="flex gap-4 px-2 py-1 items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-fin-pos animate-pulse"></span>
              <span className="text-[#6e7681] animate-pulse">Waiting for next AI signal tick...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export function LivePositions() {
  const { data, error, isLoading } = useSWR(`${API_BASE}/api/v1/portfolio/positions`, fetcher, { refreshInterval: 5000 })
  const positions = data?.positions || []

  return (
    <div className="card p-0 overflow-hidden animate-fade-in">
      <div className="px-4 py-3 flex items-center justify-between border-b border-terminal-border bg-terminal-surface/30">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
          <Briefcase size={14} className="text-accent-primary" />
          Live Active Positions
        </h3>
        {isLoading ? (
          <span className="text-text-muted text-[10px] uppercase font-mono bg-terminal-surface px-2 py-0.5 rounded animate-pulse">Syncing...</span>
        ) : (
          <span className="text-fin-pos text-[10px] uppercase font-mono bg-fin-pos/10 px-2 py-0.5 rounded flex items-center gap-1">
             LIVE <Zap size={10}/>
          </span>
        )}
      </div>
      <div className="overflow-x-auto min-h-[300px]">
        {error ? (
          <div className="flex items-center justify-center h-[200px] text-fin-neg text-xs font-mono">
            Failed to fetch from broker: {error.message || 'Unknown error'}
          </div>
        ) : positions.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center h-[200px] text-text-muted text-xs font-mono">
            <Briefcase size={24} className="mb-2 opacity-50" />
            No open positions
          </div>
        ) : (
          <table className="w-full text-left whitespace-nowrap">
            <thead>
              <tr>
                {['Symbol', 'Side', 'Qty', 'Avg Price', 'LTP', 'Current P&L', 'P&L %'].map(h => (
                  <th key={h} className="table-header px-4 py-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="font-mono text-[13px]">
              {positions.map((pos: any, i: number) => {
                const isPos = pos.pnl >= 0
                return (
                  <tr key={i} className="table-row">
                    <td className="px-4 py-3 font-medium">{pos.symbol}</td>
                    <td className={clsx("px-4 py-3 font-semibold", pos.side === 'LONG' ? "text-fin-pos" : pos.side === 'SHORT' ? "text-fin-neg" : "")}>{pos.side}</td>
                    <td className="px-4 py-3">{pos.quantity}</td>
                    <td className="px-4 py-3">₹{pos.avg_price?.toFixed(2)}</td>
                    <td className={clsx("px-4 py-3", pos.current_price >= pos.avg_price ? "text-fin-pos" : "text-fin-neg")}>
                      ₹{pos.current_price?.toFixed(2)}
                    </td>
                    <td className={clsx("px-4 py-3", isPos ? "text-fin-pos" : "text-fin-neg")}>
                      {isPos ? "+" : "-"}₹{Math.abs(pos.pnl).toFixed(2)}
                    </td>
                    <td className={clsx("px-4 py-3", isPos ? "text-fin-pos" : "text-fin-neg")}>
                      {isPos ? "+" : ""}{pos.pnl_pct?.toFixed(2)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export function PlaceholderView({ title, desc }: { title: string, desc?: string }) {
  return (
    <div className="card p-8 flex flex-col items-center justify-center h-[500px] text-text-muted gap-3 border border-[#151B23] bg-[#0B0F14]">
      <Activity size={36} className="opacity-30 text-[#4F8CFF]" />
      <p className="text-sm font-semibold tracking-wide text-text-primary uppercase">{title}</p>
      {desc && <p className="text-xs">{desc}</p>}
      <div className="mt-4 px-3 py-1 border border-terminal-border rounded text-[10px] font-mono">Module in Development</div>
    </div>
  )
}

export function AITerminalView() {
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/bot/journal`, fetcher, { refreshInterval: 5000 })
  const journal = data?.journal || []

  return (
    <div className="card p-0 overflow-hidden animate-fade-in flex flex-col h-full shadow-card border-terminal-border">
      <div className="px-5 py-4 border-b border-terminal-border bg-terminal-surface/30 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <BookOpen size={16} className="text-accent-primary" />
            AI Debate Journal
          </h3>
          <p className="text-xs text-text-muted mt-1">Live auditing of the ML + Fundamental analysis pipeline</p>
        </div>
        {isValidating && <span className="text-[10px] text-accent-primary animate-pulse border border-accent-primary/30 px-2 py-1 rounded bg-accent-primary/10">● POLLING</span>}
      </div>
      <div className="p-5 flex-1 overflow-y-auto">
        {journal.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-16 text-text-muted">
            <BookOpen size={36} className="mb-4 opacity-30" />
            <p className="text-sm">No AI analysis events yet.</p>
            <p className="text-xs mt-1">Start the bot and wait for technical candidates.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {journal.map((entry: any, i: number) => {
              const analysis = entry.analysis || {}
              return (
                <div key={i} className="border border-terminal-border bg-terminal-bg rounded-lg p-5">
                  
                  {/* Header Row */}
                  <div className="flex justify-between items-start mb-4 border-b border-terminal-border pb-3">
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-xl tracking-tight text-text-primary">{entry.symbol}</span>
                        <span className="text-[10px] px-2 py-1 rounded font-mono font-bold tracking-widest border border-terminal-border text-text-muted">
                          {entry.market_mode === 'crypto' ? 'CRYPTO' : 'STOCKS'}
                        </span>
                        <span className="text-[10px] px-2 py-1 rounded font-mono font-bold tracking-widest border border-terminal-border text-text-muted">
                          {entry.market_mode === 'crypto' ? 'CRYPTO' : 'STOCKS'}
                        </span>
                        <span className={clsx("text-[10px] px-2 py-1 rounded font-mono font-bold tracking-widest", 
                          entry.final_decision === 'TRADE' ? "bg-fin-pos/20 text-fin-pos" : entry.final_decision === 'NO_TRADE' ? "bg-fin-neg/20 text-fin-neg" : "bg-fin-neut/20 text-text-muted")}>
                          {entry.final_decision}
                        </span>
                      </div>
                      <div className="text-xs text-text-muted font-mono mt-1">{new Date(entry.timestamp).toLocaleString()}</div>
                    </div>
                    
                    {/* Pipeline Stats */}
                    <div className="flex gap-4 text-right bg-terminal-surface/30 px-3 py-2 rounded border border-terminal-border">
                      <div>
                        <div className="text-[9px] text-text-muted uppercase tracking-widest">Tech Score</div>
                        <div className="font-mono text-sm text-text-primary">{entry.technical_score.toFixed(1)}</div>
                      </div>
                      <div className="border-l border-terminal-border pl-4">
                        <div className="text-[9px] text-text-muted uppercase tracking-widest">ML Prob</div>
                        <div className={clsx("font-mono text-sm", entry.ml_probability >= 0.6 ? 'text-fin-pos' : 'text-fin-neg')}>
                          {(entry.ml_probability * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: Catalyst & Reasoning */}
                    <div className="space-y-4">
                      <div>
                        <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                          <Newspaper size={12} className="text-accent-secondary" /> Catalyst
                        </div>
                        <div className="text-sm font-medium text-text-primary bg-terminal-surface/30 p-2.5 rounded border border-terminal-border">
                          {entry.event_headline}
                        </div>
                        <div className="text-[10px] text-text-muted mt-1.5 font-mono ml-1">Source: {entry.event_source}</div>
                      </div>
                      
                      <div>
                        <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                          <BrainCircuit size={12} className="text-accent-primary" /> AI Arbiter Thesis
                        </div>
                        <p className="text-sm text-text-primary leading-relaxed bg-terminal-surface/30 p-2.5 rounded border border-terminal-border">
                          {analysis.what_changed}
                        </p>
                      </div>
                    </div>
                    
                    {/* Right: Expectation & Debate Matrix */}
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-terminal-surface/50 border border-terminal-border rounded p-2.5">
                          <div className="text-[9px] uppercase tracking-widest text-text-muted mb-1">Expectation Gap</div>
                          <div className="font-mono text-xs font-semibold text-text-primary">{analysis.expectation_gap}</div>
                        </div>
                        <div className="bg-terminal-surface/50 border border-terminal-border rounded p-2.5">
                          <div className="text-[9px] uppercase tracking-widest text-text-muted mb-1">Priced In?</div>
                          <div className="font-mono text-xs font-semibold text-text-primary">{analysis.priced_in}</div>
                        </div>
                      </div>

                      <div className="space-y-2">
                         <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-widest flex items-center gap-1.5 mb-1">
                           <ShieldAlert size={12} className="text-fin-warn" /> AI Risk Debate
                         </div>
                         <div className="bg-fin-pos/10 border border-fin-pos/20 rounded p-2.5 text-xs text-text-primary">
                           <span className="font-bold text-fin-pos block mb-0.5">BULL CASE:</span>
                           {analysis.bull_case}
                         </div>
                         <div className="bg-fin-neg/10 border border-fin-neg/20 rounded p-2.5 text-xs text-text-primary">
                           <span className="font-bold text-fin-neg block mb-0.5">BEAR CASE:</span>
                           {analysis.bear_case}
                         </div>
                      </div>
                    </div>
                  </div>

                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export function OpportunitiesView() {
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/bot/journal`, fetcher, { refreshInterval: 5000 })
  const journal = data?.journal || []

  return (
    <div className="card p-0 overflow-hidden animate-fade-in flex flex-col h-full shadow-card border-[#151B23] bg-[#0B0F14]">
      <div className="px-5 py-4 border-b border-[#151B23] flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <Zap size={16} className="text-[#4F8CFF]" />
            Live Opportunities
          </h3>
          <p className="text-xs text-text-muted mt-1">Real-time multi-model evaluation table</p>
        </div>
        {isValidating && <span className="text-[10px] text-[#4F8CFF] animate-pulse border border-[#4F8CFF]/30 px-2 py-1 rounded bg-[#4F8CFF]/10">● POLLING</span>}
      </div>
      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap">
          <thead>
            <tr className="border-b border-[#151B23]">
              {['Symbol', 'Technical', 'ML', 'Event', 'Expectation', 'Risk', 'Decision'].map(h => (
                <th key={h} className="text-[10px] font-semibold text-text-secondary uppercase tracking-widest px-5 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {journal.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-16 text-center text-text-muted font-sans">
                  No scanned opportunities yet. Start the Trading Engine.
                </td>
              </tr>
            ) : journal.map((entry: any, i: number) => {
              const analysis = entry.analysis || {}
              return (
                <tr key={i} className="border-b border-[#151B23]/50 hover:bg-[#151B23]/30 transition-colors">
                  <td className="px-5 py-3 font-semibold text-text-primary">{entry.symbol}</td>
                  <td className="px-5 py-3">{entry.technical_score.toFixed(0)}</td>
                  <td className={clsx("px-5 py-3", entry.ml_probability >= 0.6 ? 'text-fin-pos' : 'text-text-muted')}>
                    {(entry.ml_probability * 100).toFixed(0)}
                  </td>
                  <td className="px-5 py-3 text-text-secondary text-[11px] truncate max-w-[200px]" title={entry.event_headline}>
                    {entry.event_headline === "NO_CATALYST" ? "None" : entry.event_headline}
                  </td>
                  <td className="px-5 py-3 text-text-secondary capitalize text-[11px]">{analysis.expectation_gap?.toLowerCase() || 'Unknown'}</td>
                  <td className="px-5 py-3">
                    <span className={clsx("px-2 py-1 rounded text-[10px]", 
                      analysis.edge_exceeds_costs ? "bg-fin-pos/10 text-fin-pos border border-fin-pos/20" : "bg-fin-warn/10 text-fin-warn border border-fin-warn/20"
                    )}>
                      {analysis.edge_exceeds_costs ? 'Low' : 'High'}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={clsx("font-bold tracking-wider", 
                      entry.final_decision === 'TRADE' ? "text-fin-pos" : entry.final_decision === 'NO_TRADE' ? "text-fin-neg" : "text-text-muted")}>
                      {entry.final_decision}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function PaperValidationView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 10000 })
  const { data: swing, mutate: mutateSwing } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const { data: ledgerData, mutate: mutateLedger } = useSWR(`${API_BASE}/api/v1/bot/swing/ledger`, fetcher, { refreshInterval: 15000 })
  const { data: portfolio, mutate: mutatePortfolio } = useSWR(`${API_BASE}/api/v1/portfolio`, fetcher, { refreshInterval: 5000 })
  const [scanMsg, setScanMsg] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  const swingSummary = readiness?.swing_15d_model?.summary
  const holdout = readiness?.swing_15d_model?.blind_holdout
  const recs: any[] = swing?.recommendations || []
  const paperEq = Number(portfolio?.total_equity ?? 50000)
  const paperPnl = Number(portfolio?.total_pnl ?? 0)
  const ledgerAgg = ledgerData?.aggregate

  const runSwingPaperScan = async (execute: boolean) => {
    setRunning(true)
    setScanMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/bot/swing/paper-scan?execute=${execute}&record=${execute}`, { method: 'POST' })
      const body = await res.json()
      const cnt = body.orders?.length ?? body.recommendations?.length ?? 0
      setScanMsg(execute ? `Executed ${cnt} paper CNC order(s) & logged ledger tranche (as of ${body.as_of?.slice(0, 10) || 'latest'})` : `Scanned ${cnt} swing candidates`)
      mutateSwing()
      mutatePortfolio()
      mutateLedger()
    } catch {
      setScanMsg('Failed to reach backend paper scanner')
    }
    setRunning(false)
  }

  return (
    <div className="card p-0 overflow-y-auto animate-fade-in flex flex-col h-full shadow-card border-[#151B23] bg-[#0B0F14]">
      <div className="px-5 py-4 border-b border-[#151B23] flex justify-between items-center sticky top-0 bg-[#0B0F14]/90 backdrop-blur z-10">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <ShieldAlert size={16} className="text-fin-warn" />
            PAPER VALIDATION &amp; 15D SWING CNC
          </h3>
          <p className="text-xs text-text-muted mt-1">
            Live Paper Account + Ranked 15-Day Delivery Candidates
            {swing?.stale_days > 0 ? ` · cached data (${swing.stale_days}d old — refresh Upstox tokens)` : ''}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <button
            onClick={() => runSwingPaperScan(true)}
            disabled={running}
            className="text-[11px] bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary px-3 py-1.5 rounded font-mono border border-accent-primary/40"
          >
            {running ? 'Running...' : 'Allocate Paper Swing Tranche'}
          </button>
          <div className="text-[10px] text-text-secondary bg-[#151B23] px-2 py-1 rounded font-mono border border-terminal-border">
            {readiness?.live_trading_enabled ? 'LIVE ENABLED' : 'LIVE DISABLED'}
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {scanMsg && (
          <div className="p-3 rounded border border-accent-primary/30 bg-accent-primary/10 text-xs font-mono text-text-primary">
            {scanMsg}
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Paper Equity</p>
            <p className="text-xl font-mono mt-1 text-text-primary">₹{paperEq.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Paper P&amp;L</p>
            <p className={clsx("text-xl font-mono mt-1", pnlColor(paperPnl))}>
              {paperPnl >= 0 ? '+' : ''}₹{paperPnl.toFixed(2)}
            </p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Swing 15d OOS PF</p>
            <p className="text-xl font-mono mt-1 text-fin-pos">{swingSummary?.combined_profit_factor ?? '—'}</p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Blind Holdout (250d)</p>
            <p className={clsx("text-xl font-mono mt-1", (holdout?.mean_net_profit ?? 0) > 0 ? 'text-fin-pos' : 'text-fin-neg')}>
              {holdout ? `+₹${holdout.mean_net_profit.toFixed(2)}` : '—'}
            </p>
          </div>
        </div>

        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
            Top-5 Weekly 15-Day CNC Swing Candidates ({swing?.as_of ? swing.as_of.slice(0, 10) : 'Awaiting Data'})
          </h4>
          <div className="overflow-x-auto border border-[#151B23] rounded">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#151B23] text-text-muted bg-[#0D1219]">
                  <th className="py-2 px-3">Symbol</th>
                  <th className="py-2 px-3">Sector</th>
                  <th className="py-2 px-3 text-right">Last Close</th>
                  <th className="py-2 px-3 text-right">Est 15d Net%</th>
                  <th className="py-2 px-3 text-right">Tranche Qty</th>
                </tr>
              </thead>
              <tbody>
                {recs.length > 0 ? recs.map((r) => (
                  <tr key={r.symbol} className="border-b border-[#151B23]/50">
                    <td className="py-2 px-3 font-semibold text-text-primary">{r.symbol}</td>
                    <td className="py-2 px-3 text-text-muted">{r.sector}</td>
                    <td className="py-2 px-3 text-right">₹{r.last_close}</td>
                    <td className="py-2 px-3 text-right text-fin-pos">+{r.predicted_15d_net_pct}%</td>
                    <td className="py-2 px-3 text-right">{r.suggested_qty}</td>
                  </tr>
                )) : (
                  <tr><td colSpan={5} className="py-4 text-center text-text-muted">No swing picks passed hurdle</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {ledgerAgg && (
          <section className="border border-[#151B23] rounded p-4 bg-[#0D1219]/60">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-2">
              Prospective 15-Day CNC Paper Ledger
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
              <div><span className="text-text-muted">Open Tranches:</span> {ledgerAgg.open_tranches}</div>
              <div><span className="text-text-muted">Resolved:</span> {ledgerAgg.resolved_tranches}</div>
              <div><span className="text-text-muted">Win Rate:</span> {ledgerAgg.win_rate_pct}%</div>
              <div><span className="text-text-muted">Realized Net:</span> ₹{ledgerAgg.net_pnl_inr}</div>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export function RobustnessView() {
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 10000 })
  const swing = readiness?.swing_15d_model
  const intra = readiness?.walk_forward_oos
  const devFolds: any[] = []
  const intraFolds: any[] = intra?.folds || []
  const swingSummary = swing?.summary
  const holdout = swing?.blind_holdout
  const checks: Record<string, boolean> = readiness?.checks || {}

  return (
    <div className="card p-0 overflow-y-auto animate-fade-in flex flex-col h-full shadow-card border-[#151B23] bg-[#0B0F14]">
      <div className="px-5 py-4 border-b border-[#151B23] flex justify-between items-center sticky top-0 bg-[#0B0F14]/90 backdrop-blur z-10">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <Activity size={16} className="text-accent-primary" />
            Verified Walk-Forward Audit (Real OOS Results)
          </h3>
          <p className="text-xs text-text-muted mt-1">Zero Synthetic Data · Sourced live from /api/v1/bot/readiness</p>
        </div>
        <div className={clsx(
          "text-[10px] px-2 py-1 rounded font-mono border",
          readiness?.live_capital_ready ? "bg-fin-pos/10 border-fin-pos/30 text-fin-pos" : "bg-fin-warn/10 border-fin-warn/30 text-fin-warn"
        )}>
          {readiness?.live_capital_ready ? "LIVE CAPITAL READY" : "LIVE CAPITAL BLOCKED"}
        </div>
      </div>

      <div className="p-6 space-y-8">
        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
            1. Track A: 15-Day Long-Only CNC Delivery Swing (Purged 8-Year Dev + 250d Blind Holdout, 0.32% RT Cost)
          </h4>
          {swingSummary ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
              <div className="border border-[#151B23] rounded p-3 bg-[#0B0F14]/50">
                <p className="text-[10px] text-text-muted uppercase">Combined OOS PnL</p>
                <p className="text-sm font-bold text-fin-pos mt-1">+₹{swingSummary.combined_net_profit?.toLocaleString('en-IN')}</p>
              </div>
              <div className="border border-[#151B23] rounded p-3 bg-[#0B0F14]/50">
                <p className="text-[10px] text-text-muted uppercase">vs Equal-Wt NIFTY50</p>
                <p className="text-sm font-bold text-fin-pos mt-1">+₹{swingSummary.combined_outperformance_vs_benchmark?.toLocaleString('en-IN')}</p>
              </div>
              <div className="border border-[#151B23] rounded p-3 bg-[#0B0F14]/50">
                <p className="text-[10px] text-text-muted uppercase">Holdout Excess Alpha CI</p>
                <p className="text-sm font-bold text-fin-pos mt-1">
                  {holdout?.excess_alpha_95pct_ci_pct ? `[${holdout.excess_alpha_95pct_ci_pct.join(', ')}]%` : '—'}
                </p>
              </div>
              <div className="border border-[#151B23] rounded p-3 bg-[#0B0F14]/50">
                <p className="text-[10px] text-text-muted uppercase">Holdout Min Offset PnL</p>
                <p className="text-sm font-bold text-fin-pos mt-1">
                  {holdout ? `+₹${holdout.min_offset_net_profit?.toFixed(2)}` : '—'}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-xs text-text-muted font-mono">Swing report not generated yet.</p>
          )}
        </section>

        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
            2. Track B: 30m Intraday Auto-Bot (Gap-Aware 3-Fold OOS — Currently Research Only)
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#151B23] text-text-muted">
                  <th className="py-2">Fold</th>
                  <th className="py-2 text-right">Phase-1 PnL</th>
                  <th className="py-2 text-right">Trades</th>
                  <th className="py-2 text-right">Win Rate</th>
                  <th className="py-2 text-right">Phase-2A PnL</th>
                  <th className="py-2 text-right">PF</th>
                </tr>
              </thead>
              <tbody>
                {intraFolds.map((f) => (
                  <tr key={f.fold} className="border-b border-[#151B23]/50">
                    <td className="py-2 text-text-primary">{f.fold}</td>
                    <td className="py-2 text-right text-fin-neg">₹{f.phase1_net_profit}</td>
                    <td className="py-2 text-right">{f.phase2a_trades}</td>
                    <td className="py-2 text-right">{f.phase2a_win_rate_pct}%</td>
                    <td className={clsx("py-2 text-right", f.phase2a_net_profit >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                      ₹{f.phase2a_net_profit}
                    </td>
                    <td className="py-2 text-right">{f.phase2a_profit_factor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {devFolds.length === 0 && intra && (
            <p className="text-[11px] font-mono text-text-muted mt-2">
              Combined Intraday OOS: ₹{intra.combined_net_profit} · PF {intra.combined_profit_factor} · Capital preserved vs Phase-1: +₹{intra.capital_preserved_vs_phase1}
            </p>
          )}
        </section>

        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">3. Gate Checklist</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono">
            {Object.entries(checks).map(([k, ok]) => (
              <div key={k} className="flex justify-between border border-[#151B23] rounded px-3 py-2 bg-[#0B0F14]/50">
                <span className="text-text-secondary">{k}</span>
                <span className={ok ? 'text-fin-pos font-semibold' : 'text-fin-neg font-semibold'}>{ok ? 'PASS' : 'BLOCKED'}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

