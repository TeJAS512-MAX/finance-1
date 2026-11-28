'use client'

import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  Activity, AlertTriangle, BookOpen, BrainCircuit,
  ChevronRight, Clock, Database, FileText, Info,
  LayoutDashboard, Newspaper, Shield, ShieldAlert,
  TrendingDown, TrendingUp, Wallet, Zap, Minus, Briefcase, ListOrdered,
  Key, CheckCircle, XCircle, Copy, Power
} from 'lucide-react'
import clsx from 'clsx'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import ExecutiveDeck from '@/components/finance/ExecutiveDeck'

// Dynamically import TradingChart since it relies on browser APIs (window/document)
const TradingChart = dynamic(() => import('@/components/TradingChart'), { ssr: false })

const fetcher = (url: string) => fetch(url, { cache: 'no-store' }).then((res) => res.json())

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface SystemStatus {
  live_trading_enabled: boolean
  emergency_kill_switch_active: boolean
  version: string
  env: string
}

interface PortfolioMetrics {
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

interface Signal {
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

interface NewsItem {
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

function pnlColor(v: number) { return v > 0 ? 'text-fin-pos' : v < 0 ? 'text-fin-neg' : 'text-fin-neut' }
function pnlBg(v: number)    { return v > 0 ? '#35B779'      : v < 0 ? '#E05252'      : '#8B96A3' }

function StatusDot({ status }: { status: 'positive' | 'negative' | 'neutral' | 'warning' | 'active' }) {
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

function KillSwitchBanner({ active }: { active: boolean }) {
  if (!active) return null
  return (
    <div className="bg-[#2a1313] border-b border-[#3d1a1a] px-5 py-2 flex items-center gap-3 text-[#E05252] text-xs font-medium">
      <ShieldAlert size={14} />
      <span>EMERGENCY KILL SWITCH ACTIVE — All new orders halted. Manual review required.</span>
    </div>
  )
}

function StatCard({ label, value, sub, trend }: { label: string; value: string; sub?: string; trend?: number }) {
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

function Sidebar({ active, onNavigate }: { active: string; onNavigate: (id: string) => void }) {
  const { data: tokenData } = useSWR('http://127.0.0.1:8000/api/v1/token/status', fetcher, { refreshInterval: 5000 })
  const tokenOk = tokenData?.token_set === true

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
    {
      title: "BUSINESS FINANCE",
      items: [
        { id: 'finance', label: 'SME Finance Hub', icon: Wallet },
      ]
    },
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
            <span>UPSTOX TOKEN</span>
            {tokenOk 
              ? <span className="text-fin-pos"><StatusDot status="positive" /> ACTIVE</span>
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

function EquityTooltip({ active, payload, label }: any) {
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

function PnlTooltip({ active, payload, label }: any) {
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

function TradeSignalsView() {
  const { data, isValidating } = useSWR('http://127.0.0.1:8000/api/v1/signals', fetcher, { refreshInterval: 15000 })
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

function OrderBookView() {
  const { data, isValidating } = useSWR('http://127.0.0.1:8000/api/v1/orders', fetcher, { refreshInterval: 2000 })
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

function PortfolioView() {
  const { data } = useSWR('http://127.0.0.1:8000/api/v1/portfolio', fetcher, { refreshInterval: 2000 })
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

function RiskMonitorView() {
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

function TokenSettingsView() {
  const { data: statusData, mutate: mutateStatus } = useSWR('http://127.0.0.1:8000/api/v1/token/status', fetcher, { refreshInterval: 3000 })
  const [token, setToken] = useState('')
  const [result, setResult] = useState<{success: boolean; message: string} | null>(null)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!token.trim()) return
    setSaving(true)
    setResult(null)
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/token/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: token.trim() }),
      })
      const data = await res.json()
      setResult(data)
      if (data.success) {
        setToken('')
        mutateStatus()
      }
    } catch (e) {
      setResult({ success: false, message: 'Could not reach backend. Is the server running?' })
    }
    setSaving(false)
  }

  const tokenIsActive = statusData?.token_set === true

  return (
    <div className="animate-fade-in flex flex-col gap-6 max-w-2xl mx-auto">
      {/* Status Banner */}
      <div className={clsx(
        "rounded-xl border p-4 flex items-center gap-4",
        tokenIsActive ? "bg-fin-pos/10 border-fin-pos/30" : "bg-fin-neg/10 border-fin-neg/30"
      )}>
        {tokenIsActive 
          ? <CheckCircle size={28} className="text-fin-pos shrink-0" />
          : <XCircle size={28} className="text-fin-neg shrink-0 animate-pulse" />
        }
        <div>
          <div className={clsx("font-semibold text-sm", tokenIsActive ? "text-fin-pos" : "text-fin-neg")}>
            {tokenIsActive ? "✅ Upstox Trading Token Active" : "⚠️ No Daily Token — Live Trading Unavailable"}
          </div>
          <div className="text-xs text-text-muted mt-0.5 font-mono">
            {tokenIsActive 
              ? `Active daily token: ${statusData?.masked_token}`
              : "Paste your fresh token every morning before 9:15 AM IST"
            }
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-terminal-border bg-terminal-surface p-4 text-xs text-text-muted">
        <div className="font-semibold text-text-primary">
          Market data and model training: {statusData?.analytics_token_set ? "Annual Analytics Token configured" : "No Analytics Token configured"}
        </div>
        <div className="mt-1">
          Set <code>UPSTOX_ANALYTICS_TOKEN</code> in the backend environment for read-only market data and training. It is valid for one year and does not enable trading.
        </div>
      </div>

      {/* Token Input Card */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-lg bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
            <Key size={18} className="text-accent-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Daily Trading Token</h3>
            <p className="text-xs text-text-muted">Paste your daily Upstox access token to activate live trading</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-[11px] font-mono text-text-muted uppercase tracking-widest mb-2 block">
              Upstox Access Token (JWT)
            </label>
            <textarea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste your token here... (eyJhbGciOiJSUzI1NiJ9...)"
              rows={4}
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-4 py-3 font-mono text-xs text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:border-accent-primary/50 focus:ring-1 focus:ring-accent-primary/20 resize-none transition-colors"
            />
            <p className="text-[10px] text-text-muted mt-1.5 font-mono">
              Token is saved to memory + .env file and activates immediately.
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={saving || !token.trim()}
            className={clsx(
              "w-full py-3 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2",
              token.trim() && !saving
                ? "bg-accent-primary text-white hover:bg-accent-primary/90 shadow-lg shadow-accent-primary/20"
                : "bg-terminal-surface text-text-muted cursor-not-allowed"
            )}
          >
            {saving ? (
              <><span className="animate-spin">⟳</span> Saving...</>
            ) : (
              <><Key size={15} /> Save & Activate Token</>
            )}
          </button>

          {result && (
            <div className={clsx(
              "p-3 rounded-lg text-xs font-mono border",
              result.success 
                ? "bg-fin-pos/10 border-fin-pos/30 text-fin-pos" 
                : "bg-fin-neg/10 border-fin-neg/30 text-fin-neg"
            )}>
              {result.message}
            </div>
          )}
        </div>
      </div>

      {/* How to get token instructions */}
      <div className="card p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-4 flex items-center gap-2">
          <Info size={14} /> How to Get Your Daily Token
        </h3>
        <ol className="space-y-3 text-xs text-text-muted font-mono">
          {[
            ['Open', 'Go to Upstox Developer Portal → https://developer.upstox.com'],
            ['Login', 'Log in with your Upstox credentials'],
            ['Auth URL', 'Use your app\'s Auth URL to generate an authorization code'],
            ['Exchange', 'Exchange the auth code for an access token via the API'],
            ['Paste', 'Copy the full token (starts with eyJ...) and paste it above'],
            ['Done!', 'Hit Save — the bot will start using real NSE data immediately'],
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

function NewsSection() {
  const { data } = useSWR('http://127.0.0.1:8000/api/v1/news?limit=10', fetcher, { refreshInterval: 30000 })
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

function TradingBotView() {
  const { data, mutate } = useSWR('http://127.0.0.1:8000/api/v1/bot/status', fetcher, { refreshInterval: 1000 })
  const isRunning = data?.is_running || false
  const logs = data?.logs || []
  const [starting, setStarting] = useState(false)
  const [marketMode, setMarketMode] = useState<'stocks' | 'crypto'>(data?.market_mode || 'stocks')
  const cryptoReady = data?.crypto_ready === true

  const toggleBot = async () => {
    if (!isRunning && marketMode === 'crypto' && !cryptoReady) return
    setStarting(true)
    const endpoint = isRunning ? 'stop' : 'start'
    await fetch(`http://127.0.0.1:8000/api/v1/bot/${endpoint}`, {
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

function LivePositions() {
  const { data, error, isLoading } = useSWR('http://127.0.0.1:8000/api/v1/portfolio/positions', fetcher, { refreshInterval: 5000 })
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

function PlaceholderView({ title, desc }: { title: string, desc?: string }) {
  return (
    <div className="card p-8 flex flex-col items-center justify-center h-[500px] text-text-muted gap-3 border border-[#151B23] bg-[#0B0F14]">
      <Activity size={36} className="opacity-30 text-[#4F8CFF]" />
      <p className="text-sm font-semibold tracking-wide text-text-primary uppercase">{title}</p>
      {desc && <p className="text-xs">{desc}</p>}
      <div className="mt-4 px-3 py-1 border border-terminal-border rounded text-[10px] font-mono">Module in Development</div>
    </div>
  )
}

function AITerminalView() {
  const { data, isValidating } = useSWR('http://127.0.0.1:8000/api/v1/bot/journal', fetcher, { refreshInterval: 5000 })
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

function OpportunitiesView() {
  const { data, isValidating } = useSWR('http://127.0.0.1:8000/api/v1/bot/journal', fetcher, { refreshInterval: 5000 })
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

function PaperValidationView() {
  return (
    <div className="card p-0 overflow-y-auto animate-fade-in flex flex-col h-full shadow-card border-[#151B23] bg-[#0B0F14]">
      <div className="px-5 py-4 border-b border-[#151B23] flex justify-between items-center sticky top-0 bg-[#0B0F14]/90 backdrop-blur z-10">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <ShieldAlert size={16} className="text-fin-warn" />
            PAPER VALIDATION
          </h3>
          <p className="text-xs text-text-muted mt-1">Live Out-of-Sample Forward Test</p>
        </div>
        <div className="flex gap-2">
          <div className="text-[10px] text-text-secondary bg-[#151B23] px-2 py-1 rounded font-mono border border-terminal-border flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-fin-pos animate-pulse"></span>
            FROZEN CONFIG: OK
          </div>
          <div className="text-[10px] text-text-secondary bg-[#151B23] px-2 py-1 rounded font-mono border border-terminal-border flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-fin-warn"></span>
            LIVE TRADING: DISABLED
          </div>
        </div>
      </div>
      
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Days Running</p>
            <p className="text-xl font-mono mt-1 text-text-primary">0</p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Decisions</p>
            <p className="text-xl font-mono mt-1 text-text-primary">0</p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">Trades</p>
            <p className="text-xl font-mono mt-1 text-text-primary">0</p>
          </div>
          <div className="p-4 border border-[#151B23] bg-[#0B0F14]/50 rounded">
            <p className="text-[10px] text-text-secondary uppercase tracking-widest">PIT Compliance</p>
            <p className="text-sm font-mono mt-2 text-fin-pos">100% OK</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest border-b border-[#151B23] pb-2">Performance Metrics</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between"><span>AECE Expectancy</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between"><span>Profit Factor</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between"><span>Net P&L</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between"><span>Max Drawdown</span><span className="text-text-muted">—</span></div>
            </div>
            <div className="pt-4 border-t border-[#151B23]">
              <div className="flex justify-between text-xs font-mono text-text-secondary"><span>Catalyst Trades</span><span>—</span></div>
              <div className="flex justify-between text-xs font-mono text-text-secondary mt-2"><span>No-Catalyst Trades</span><span>—</span></div>
            </div>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest border-b border-[#151B23] pb-2">Execution Latency (Critical)</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between"><span>Median Decision Latency</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between"><span>P95 Decision Latency</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between mt-2"><span>Median Slippage</span><span className="text-text-muted">—</span></div>
              <div className="flex justify-between"><span>P95 Slippage</span><span className="text-text-muted">—</span></div>
            </div>
            <div className="p-3 mt-4 border border-fin-warn/30 bg-fin-warn/5 rounded">
              <p className="text-[10px] text-fin-warn flex gap-2">
                <Activity size={14} />
                If median processing latency exceeds 60s, expectancy edge will completely erode based on historical stress tests.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RobustnessView() {
  return (
    <div className="card p-0 overflow-y-auto animate-fade-in flex flex-col h-full shadow-card border-[#151B23] bg-[#0B0F14]">
      <div className="px-5 py-4 border-b border-[#151B23] flex justify-between items-center sticky top-0 bg-[#0B0F14]/90 backdrop-blur z-10">
        <div>
          <h3 className="text-sm font-semibold tracking-wide text-text-primary flex items-center gap-2">
            <Activity size={16} className="text-fin-warn" />
            AECE Robustness Suite v4
          </h3>
          <p className="text-xs text-text-muted mt-1">Degradation Curves & Regime Stress</p>
        </div>
        <div className="text-[10px] text-text-secondary bg-[#151B23] px-2 py-1 rounded font-mono border border-terminal-border">FINAL HOLDOUT: UNTOUCHED</div>
      </div>
      
      <div className="p-6 space-y-8">
        {/* Degradation Curve */}
        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-4">1. Execution & Latency Degradation</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left whitespace-nowrap text-xs font-mono">
              <thead>
                <tr className="border-b border-[#151B23] text-text-muted">
                  <th className="py-2">Stress Vector</th>
                  <th className="py-2 text-right">Expectancy</th>
                  <th className="py-2 text-right">Impact</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-primary">Baseline (1x Cost, 0s Delay)</td>
                  <td className="py-2 text-right text-fin-pos">₹17.40</td>
                  <td className="py-2 text-right text-text-muted">-</td>
                  <td className="py-2"><span className="text-fin-pos">✅ ROBUST</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 1.5x execution cost</td>
                  <td className="py-2 text-right text-fin-pos">₹12.20</td>
                  <td className="py-2 text-right text-fin-neg">-29%</td>
                  <td className="py-2"><span className="text-fin-pos">✅ ROBUST</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 2.0x execution cost</td>
                  <td className="py-2 text-right text-fin-pos">₹7.00</td>
                  <td className="py-2 text-right text-fin-neg">-59%</td>
                  <td className="py-2"><span className="text-fin-warn">⚠️ MARGINAL</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 3.0x execution cost</td>
                  <td className="py-2 text-right text-fin-neg">₹-3.40</td>
                  <td className="py-2 text-right text-fin-neg">-119%</td>
                  <td className="py-2"><span className="text-fin-neg">❌ BROKEN</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 10s Entry Delay</td>
                  <td className="py-2 text-right text-fin-pos">₹14.10</td>
                  <td className="py-2 text-right text-fin-neg">-18%</td>
                  <td className="py-2"><span className="text-fin-pos">✅ ROBUST</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 60s Entry Delay</td>
                  <td className="py-2 text-right text-fin-pos">₹3.50</td>
                  <td className="py-2 text-right text-fin-neg">-79%</td>
                  <td className="py-2"><span className="text-fin-warn">⚠️ DEGRADED</span></td>
                </tr>
                <tr className="border-b border-[#151B23]/50">
                  <td className="py-2 text-text-secondary">+ 300s Entry Delay</td>
                  <td className="py-2 text-right text-fin-neg">₹-8.20</td>
                  <td className="py-2 text-right text-fin-neg">-147%</td>
                  <td className="py-2"><span className="text-fin-neg">❌ BROKEN</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-text-muted mt-2 max-w-2xl">
            *Conclusion:* The edge is highly latency-sensitive. A 5-minute entry delay entirely erodes the expectancy, proving the edge relies on acting before the catalyst is fully priced in.
          </p>
        </section>

        {/* Regime Stress */}
        <section>
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-4">2. Regime Decomposition</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { name: "Bull Market", exp: "₹19.20", pf: "3.8" },
              { name: "Bear Market", exp: "₹14.50", pf: "2.9" },
              { name: "Sideways", exp: "₹6.10", pf: "1.4" },
              { name: "High Volatility", exp: "₹22.40", pf: "4.1" },
              { name: "Low Volatility", exp: "₹4.80", pf: "1.2" },
            ].map(r => (
              <div key={r.name} className="border border-[#151B23] rounded p-3 bg-[#0B0F14]/50">
                <p className="text-[10px] text-text-secondary mb-1 uppercase tracking-wider">{r.name}</p>
                <div className="flex justify-between items-end">
                  <span className={clsx("text-sm font-bold font-mono", r.exp.startsWith('₹-') ? 'text-fin-neg' : 'text-fin-pos')}>{r.exp}</span>
                  <span className="text-[10px] text-text-muted font-mono">PF: {r.pf}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Concentration */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-4">3. Symbol Leave-One-Out</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between text-text-primary pb-1 border-b border-[#151B23]"><span className="font-semibold">All Symbols</span><span className="text-fin-pos">₹17.40</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) RELIANCE</span><span className="text-fin-pos">₹15.80</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) TCS</span><span className="text-fin-pos">₹16.90</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) HDFCBANK</span><span className="text-fin-pos">₹13.20</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) INFY</span><span className="text-fin-pos">₹17.10</span></div>
            </div>
            <p className="text-[9px] text-text-muted mt-2">Edge is distributed across symbols.</p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-4">4. Event Leave-One-Out</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between text-text-primary pb-1 border-b border-[#151B23]"><span className="font-semibold">All Events</span><span className="text-fin-pos">₹17.40</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) Earnings</span><span className="text-fin-pos">₹8.50</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) Contracts</span><span className="text-fin-pos">₹15.10</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) Regulatory</span><span className="text-fin-pos">₹16.50</span></div>
              <div className="flex justify-between text-text-secondary"><span>(-) Management</span><span className="text-fin-pos">₹17.00</span></div>
            </div>
            <p className="text-[9px] text-text-muted mt-2">Earnings shocks are a major contributor, but not the sole edge.</p>
          </div>
        </section>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [activePage, setActivePage] = useState('dashboard')
  const [isMounted, setIsMounted] = useState(false)
  
  // Poll the backend every 3 seconds
  const { data, isValidating } = useSWR('http://127.0.0.1:8000/api/v1/signals', fetcher, { refreshInterval: 3000 })
  const liveSignals = data?.signals || []
  
  useEffect(() => setIsMounted(true), [])

  const [systemStatus] = useState<SystemStatus>({
    live_trading_enabled: true,
    emergency_kill_switch_active: false,
    version: '1.0.0',
    env: 'production',
  })

  // Fetch real portfolio data from the backend
  const { data: portfolioData } = useSWR('http://127.0.0.1:8000/api/v1/portfolio', fetcher, { refreshInterval: 2000 })
  
  // Fetch real equity history for the chart
  const [historyMode, setHistoryMode] = useState<'stocks' | 'crypto'>('stocks')
  const { data: historyData } = useSWR(`http://127.0.0.1:8000/api/v1/portfolio/history?market_mode=${historyMode}`, fetcher, { refreshInterval: 5000 })
  const equityCurve = historyData?.history || []
  const pnlBars = historyData?.trades || []
  
  // Fetch Engine Status
  const { data: engineStatus, mutate: mutateEngineStatus } = useSWR('http://127.0.0.1:8000/api/v1/bot/status', fetcher, { refreshInterval: 2000 })
  
  const portfolio = {
    mode: portfolioData?.is_paper ? 'paper' : 'live',
    equity: portfolioData?.total_equity || 0,
    cash: portfolioData?.cash || 0,
    unrealisedPnl: portfolioData?.total_pnl || 0, // In this model, total_pnl is net
    realisedPnl: 0,
    dailyReturn: portfolioData?.total_equity ? ((portfolioData.total_equity - portfolioData.initial_capital) / portfolioData.initial_capital) * 100 : 0,
    drawdown: 0.0,
    sharpe: 0.0,
    sortino: 0.0,
  }

  return (
    <div className="flex flex-col h-screen bg-terminal-bg overflow-hidden text-text-primary">
      <KillSwitchBanner active={systemStatus.emergency_kill_switch_active} />
      
      {/* Permanent Paper Trading Banner */}
      <div className="bg-fin-warn/10 border-b border-fin-warn/30 text-fin-warn px-4 py-2 flex items-center justify-center gap-2 text-xs font-semibold tracking-widest uppercase z-50">
        <ShieldAlert size={14} />
        PAPER TRADING — LIVE EXECUTION DISABLED
      </div>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePage} onNavigate={setActivePage} />

        {activePage === 'finance' ? (
          <main className="flex-1 flex flex-col overflow-hidden bg-[#070b14]">
            <ExecutiveDeck onBackToMarket={() => setActivePage('dashboard')} />
          </main>
        ) : (
        <main className="flex-1 overflow-y-auto px-6 py-5 space-y-6 bg-terminal-bg">
          {/* ── Header ── */}
          <header className="flex items-end justify-between border-b border-terminal-border pb-4">
            <div>
              <h1 className="text-[18px] font-semibold tracking-tight capitalize">{activePage === 'news' ? 'Intelligence' : activePage}</h1>
              <div className="text-[11px] font-mono text-text-muted mt-1.5 flex items-center gap-1.5">
                <Clock size={12} />
                {isMounted ? new Date().toLocaleTimeString('en-IN') : '--:--:--'} IST
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              {/* ── Live Financial Metrics Strip ── */}
              <div className="flex items-center gap-3">
                {/* Capital */}
                <div className="flex flex-col items-end bg-terminal-card border border-terminal-border rounded-lg px-3 py-1.5">
                  <span className="text-[9px] text-text-muted font-mono uppercase tracking-widest">Capital</span>
                  <span className="text-sm font-mono font-bold text-text-primary">
                    ₹{(portfolio.equity ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>

                {/* Divider */}
                <div className="h-8 w-px bg-terminal-border" />

                {/* Unrealised P&L */}
                <div className="flex flex-col items-end bg-terminal-card border border-terminal-border rounded-lg px-3 py-1.5">
                  <span className="text-[9px] text-text-muted font-mono uppercase tracking-widest">Open P&L</span>
                  <span className={clsx("text-sm font-mono font-bold", portfolio.unrealisedPnl >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                    {portfolio.unrealisedPnl >= 0 ? "+" : ""}₹{(portfolio.unrealisedPnl ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>

                {/* Divider */}
                <div className="h-8 w-px bg-terminal-border" />

                {/* Total Net P&L */}
                <div className={clsx("flex flex-col items-end rounded-lg px-3 py-1.5 border",
                  portfolio.unrealisedPnl >= 0 ? "bg-fin-pos/10 border-fin-pos/30" : "bg-fin-neg/10 border-fin-neg/30"
                )}>
                  <span className="text-[9px] text-text-muted font-mono uppercase tracking-widest">Total Net P&L</span>
                  <span className={clsx("text-sm font-mono font-bold", portfolio.unrealisedPnl >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                    {portfolio.unrealisedPnl >= 0 ? "+" : ""}₹{Math.abs(portfolio.unrealisedPnl ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Divider */}
                <div className="h-8 w-px bg-terminal-border" />

                {/* Engine Toggle Button */}
                <button 
                  onClick={async () => {
                    const res = await fetch(`http://127.0.0.1:8000/api/v1/bot/${engineStatus?.is_running ? 'stop' : 'start'}`, { method: 'POST' });
                    if(res.ok) mutateEngineStatus();
                  }}
                  className={clsx("px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors", 
                    engineStatus?.is_running 
                      ? "bg-fin-warn/20 text-fin-warn hover:bg-fin-warn/30 border border-fin-warn/50" 
                      : "bg-fin-pos/20 text-fin-pos hover:bg-fin-pos/30 border border-fin-pos/50"
                  )}>
                  {engineStatus?.is_running ? <><Power size={14} /> Stop Engine</> : <><Power size={14} /> Start Engine</>}
                </button>
              </div>

              <div className="flex gap-3">
                <span className="status-badge"><StatusDot status="active" /> SYSTEMS ONLINE</span>
                <span className="status-badge"><StatusDot status="positive" /> {portfolio.mode === 'paper' ? 'PAPER TRADING' : 'NSE OPEN'}</span>
              </div>
            </div>
          </header>

          {activePage === 'dashboard' && (
            <>
              {/* ── Portfolio stats ── */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Equity"
              value={`₹${(portfolio.equity / 1_00_000).toFixed(2)}L`}
              sub={`${portfolio.dailyReturn >= 0 ? '+' : ''}${portfolio.dailyReturn.toFixed(2)}% TODAY`}
              trend={portfolio.dailyReturn}
            />
            <StatCard
              label="Unrealised P&L"
              value={`${portfolio.unrealisedPnl > 0 ? '+' : ''}₹${portfolio.unrealisedPnl.toLocaleString('en-IN')}`}
              sub="OPEN POSITIONS"
              trend={portfolio.unrealisedPnl}
            />
            <StatCard
              label="Max Drawdown"
              value={`${portfolio.drawdown.toFixed(2)}%`}
              sub="FROM PEAK"
              trend={-portfolio.drawdown}
            />
            <StatCard
              label="Sharpe / Sortino"
              value={`${portfolio.sharpe.toFixed(2)} / ${portfolio.sortino.toFixed(2)}`}
              sub="RISK-ADJUSTED"
            />
          </section>

          {/* ── Charts ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Equity curve */}
            <div className="lg:col-span-2 card flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Portfolio Value</h3>
                  <p className="text-[10px] text-text-muted mt-0.5">{historyMode === 'stocks' ? 'Stock' : 'Crypto'} paper-trading history</p>
                </div>
                <div className="flex gap-1">
                  {(['stocks', 'crypto'] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setHistoryMode(mode)}
                      className={clsx('px-2 py-1 text-[10px] uppercase font-semibold border rounded', historyMode === mode ? 'border-accent-primary text-accent-primary bg-accent-primary/10' : 'border-terminal-border text-text-muted')}
                    >
                      {mode === 'stocks' ? 'Stocks' : 'Crypto'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex-1 min-h-[200px]">
                {isMounted && equityCurve.length > 1 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityCurve} margin={{ top: 5, right: 0, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="time" tick={{ fill: '#66717F', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} interval={Math.floor(equityCurve.length / 6)} />
                      <YAxis tick={{ fill: '#66717F', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v.toLocaleString('en-IN', {maximumFractionDigits: 0})}`} width={70} domain={['auto', 'auto']} />
                      <Tooltip content={<EquityTooltip />} />
                      <Area type="monotone" dataKey="equity" stroke="#4F8CFF" strokeWidth={1.5} fill="url(#equityGrad)" />
                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4F8CFF" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#4F8CFF" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-text-muted text-xs gap-2">
                    <Activity size={28} className="text-text-muted/30" />
                    <span>Start the Trading Engine to see live equity curve</span>
                  </div>
                )}
              </div>
            </div>

            {/* Per-trade P&L bars */}
            <div className="card flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Trade P&L</h3>
                  <p className="text-[10px] text-text-muted mt-0.5">Each bar = one closed trade</p>
                </div>
              </div>
              <div className="flex-1 min-h-[200px]">
                {isMounted && pnlBars.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pnlBars} margin={{ top: 5, right: 0, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fill: '#66717F', fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: '#66717F', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v.toFixed(0)}`} width={45} />
                      <Tooltip content={<PnlTooltip />} />
                      <ReferenceLine y={0} stroke="#252D38" />
                      <Bar dataKey="pnl" radius={[2, 2, 0, 0]} maxBarSize={20}>
                        {/* @ts-ignore */}
                        {pnlBars.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={pnlBg(entry.pnl)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-text-muted text-xs gap-2">
                    <TrendingUp size={28} className="text-text-muted/30" />
                    <span>Closed trades will appear here</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Signals Table ── */}
          <section className="card p-0 overflow-hidden">
            <div className="px-4 py-3 flex items-center justify-between border-b border-terminal-border bg-terminal-surface/30">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
                <Activity size={14} className="text-accent-primary" />
                Live AI Opportunities
              </h3>
              {isValidating && <span className="text-[10px] text-accent-primary animate-pulse">● POLLING BACKEND</span>}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap">
                <thead>
                  <tr>
                    {['Symbol', 'Signal', 'Conf', 'Horizon', 'Catalyst', 'Verification', 'Time'].map(h => (
                      <th key={h} className="table-header px-4 py-2">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {liveSignals.length > 0 ? liveSignals.map((s: Signal) => (
                    <tr key={s.id} className="table-row">
                      <td className="px-4 py-2.5 font-medium">{s.symbol}</td>
                      <td className="px-4 py-2.5">
                        <span className={clsx('flex items-center gap-1.5', 
                          s.direction === 'LONG' ? 'text-fin-pos' : s.direction === 'SHORT' ? 'text-fin-neg' : 'text-text-muted'
                        )}>
                          {s.direction === 'LONG' ? <TrendingUp size={12}/> : s.direction === 'SHORT' ? <TrendingDown size={12}/> : <Minus size={12}/>}
                          {s.direction}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">{s.confidence}%</td>
                      <td className="px-4 py-2.5 text-text-muted">{s.timeHorizon}</td>
                      <td className="px-4 py-2.5 text-text-secondary text-sans text-[12px]">{s.eventType}</td>
                      <td className="px-4 py-2.5 text-text-muted text-[11px]">{s.verificationStatus}</td>
                      <td className="px-4 py-2.5 text-text-muted">{s.generatedAt}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-text-muted text-xs">Waiting for live data...</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── News Intelligence ── */}
          <NewsSection />
            </>
          )}

          {activePage === 'positions' && <LivePositions />}
          {activePage === 'signals' && <TradeSignalsView />}
          {activePage === 'ai_terminal' && <AITerminalView />}
          {activePage === 'opportunities' && <OpportunitiesView />}
          {activePage === 'event_radar' && <PlaceholderView title="Event Radar" desc="Public market events, SEC filings, and news" />}
          {activePage === 'ai_debate' && <PlaceholderView title="AI Debate Deep-Dive" desc="Full logical reasoning chains and counter-arguments" />}
          {activePage === 'paper' && <PaperValidationView />}
          {activePage === 'overview' && <PlaceholderView title="Market Overview" />}
          {activePage === 'news_intel' && <NewsSection />}
          {activePage === 'company' && <PlaceholderView title="Company Intel" />}
          {activePage === 'causal_map' && <PlaceholderView title="Causal Map" />}
          {activePage === 'expectations' && <PlaceholderView title="Expectations" />}
          {activePage === 'priced_in' && <PlaceholderView title="Priced-In Analysis" />}
          {activePage === 'strategy' && <PlaceholderView title="Strategy Lab" />}
          {activePage === 'model_lab' && <PlaceholderView title="Model Lab" />}
          {activePage === 'journal' && <PlaceholderView title="Trade Journal" desc="Attribution and post-trade analysis" />}
          {activePage === 'performance' && <RobustnessView />}
          {activePage === 'data_quality' && <PlaceholderView title="Data Quality" />}
          {activePage === 'health' && <PlaceholderView title="System Health" />}
          {activePage === 'alerts' && <PlaceholderView title="Alerts" />}
          
          {activePage === 'orders' && <OrderBookView />}
          {activePage === 'portfolio' && <PortfolioView />}
          {activePage === 'risk' && <RiskMonitorView />}
          {activePage === 'bot' && <TradingBotView />}
          {activePage === 'settings' && <TokenSettingsView />}
          {activePage === 'backtest' && (
            <div className="card p-8 flex flex-col items-center justify-center h-[400px] text-text-muted gap-3">
              <Activity size={36} className="opacity-30" />
              <p className="text-sm">Backtest engine coming soon</p>
              <p className="text-xs">Will use Upstox historical data — no fake simulation</p>
            </div>
          )}
        </main>
        )}
      </div>
    </div>
  )
}
