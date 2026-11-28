'use client'

import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  Activity, CheckCircle, Clock, Power, Search, ShieldAlert, Sparkles, TrendingDown, TrendingUp, Minus
} from 'lucide-react'
import clsx from 'clsx'
import useSWR, { mutate } from 'swr'
import ExecutiveDeck from '@/components/finance/ExecutiveDeck'
import { API_BASE } from '@/lib/config'
import {
  fetcher, pnlColor, pnlBg,
  SystemStatus, Signal,
  StatusDot, KillSwitchBanner, StatCard, Sidebar,
  EquityTooltip, PnlTooltip,
  TradeSignalsView, OrderBookView, PortfolioView, RiskMonitorView,
  TokenSettingsView, NewsSection, TradingBotView, LivePositions,
  AITerminalView, OpportunitiesView,
  PaperValidationView, RobustnessView,
} from '@/components/market/MarketViews'
import {
  MarketOverviewView, EventRadarView, CompanyIntelView, CausalMapView,
  ExpectationsView, PricedInView, BacktestingView, StrategyLabView,
  ModelLabView, TradeJournalView, DataQualityView, SystemHealthView,
  AlertsView,
} from '@/components/market/ExtendedViews'
import {
  HeroSlidesCarousel, MarketTickerTape, Sparkline, QuickOrderModal, CommandPaletteModal
} from '@/components/market/HeroSlidesCarousel'

const QUICK_NAV_ITEMS = [
  { id: 'dashboard', label: 'Overview & Hero Desk' },
  { id: 'overview', label: 'NSE Market Screener (67 Stocks)' },
  { id: 'opportunities', label: 'AI Swing Opportunities' },
  { id: 'signals', label: 'Trade Signals Feed' },
  { id: 'positions', label: 'Live Paper Positions' },
  { id: 'orders', label: 'Order Book & Paper Fills' },
  { id: 'portfolio', label: 'Portfolio & Allocations' },
  { id: 'company', label: 'Company Deep Intel' },
  { id: 'paper', label: 'Paper Swing Validation' },
  { id: 'backtest', label: 'Walk-Forward Backtest' },
  { id: 'strategy', label: 'Strategy Gate Matrix' },
  { id: 'bot', label: 'Autonomous Engine Logs' },
  { id: 'risk', label: 'Risk & Drawdown Limits' },
  { id: 'settings', label: 'Upstox Token & API Keys' },
]

export default function DashboardPage() {
  const [activePage, setActivePage] = useState('dashboard')
  const [isMounted, setIsMounted] = useState(false)
  const [selectedSymbol, setSelectedSymbol] = useState('TECHM')
  const [quickTradeSymbol, setQuickTradeSymbol] = useState<string | null>(null)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  
  // Poll the backend every 3 seconds
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/signals`, fetcher, { refreshInterval: 3000 })
  const liveSignals = data?.signals || []
  
  useEffect(() => {
    setIsMounted(true)
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCmdOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    if (!toastMsg) return
    const timer = setTimeout(() => setToastMsg(null), 4000)
    return () => clearTimeout(timer)
  }, [toastMsg])

  const { data: healthDetail } = useSWR(`${API_BASE}/health/detail`, fetcher, { refreshInterval: 10000 })
  const systemStatus: SystemStatus = {
    live_trading_enabled: Boolean(healthDetail?.safety_flags?.live_trading_enabled ?? false),
    emergency_kill_switch_active: Boolean(healthDetail?.safety_flags?.emergency_kill_switch_active ?? false),
    version: healthDetail?.version || '1.0.0',
    env: healthDetail?.env || 'development',
  }

  // Fetch real portfolio data from the backend
  const { data: portfolioData, mutate: mutatePortfolio } = useSWR(`${API_BASE}/api/v1/portfolio`, fetcher, { refreshInterval: 2000 })
  
  // Fetch real equity history for the chart
  const [historyMode, setHistoryMode] = useState<'stocks' | 'crypto'>('stocks')
  const { data: historyData } = useSWR(`${API_BASE}/api/v1/portfolio/history?market_mode=${historyMode}`, fetcher, { refreshInterval: 5000 })
  const equityCurve = historyData?.history || []
  const pnlBars = historyData?.trades || []
  
  // Fetch Engine Status, Positions, Token Status & Verified Readiness / Swing Top-5
  const { data: engineStatus, mutate: mutateEngineStatus } = useSWR(`${API_BASE}/api/v1/bot/status`, fetcher, { refreshInterval: 2000 })
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const { data: swingData } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })
  const { data: posData, mutate: mutatePositions } = useSWR(`${API_BASE}/api/v1/portfolio/positions`, fetcher, { refreshInterval: 5000 })
  const { data: tokenStatus } = useSWR(`${API_BASE}/api/v1/token/status`, fetcher, { refreshInterval: 10000 })

  const handleInspectSymbol = (sym: string) => {
    setSelectedSymbol(sym)
    setActivePage('company')
  }

  const handleOrderFilled = (msg: string) => {
    setToastMsg(msg)
    mutatePortfolio()
    mutatePositions()
    mutate((key) => typeof key === 'string' && key.includes('/api/v1/orders'))
  }

  const swingSummary = readiness?.swing_15d_model?.summary
  const holdout = readiness?.swing_15d_model?.blind_holdout
  const swingRecs = swingData?.recommendations || []
  const swingRanked = swingData?.all_ranked || []
  const positionsList = posData?.positions || []
  const deployedPct = portfolioData?.total_equity ? ((portfolioData.total_market_value || 0) / portfolioData.total_equity) * 100 : 0

  const portfolio = {
    mode: portfolioData?.is_paper ? 'paper' : 'live',
    equity: portfolioData?.total_equity || 0,
    cash: portfolioData?.cash || 0,
    marketValue: portfolioData?.total_market_value || 0,
    unrealisedPnl: portfolioData?.total_pnl || 0,
    realisedPnl: 0,
    dailyReturn: portfolioData?.initial_capital ? ((portfolioData.total_equity - portfolioData.initial_capital) / portfolioData.initial_capital) * 100 : 0,
    drawdown: holdout?.worst_offset_max_drawdown_pct ?? 0.0,
    pf: swingSummary?.combined_profit_factor ?? 0.0,
    holdoutNet: holdout?.mean_net_profit ?? 0.0,
  }

  return (
    <div className="flex flex-col h-screen bg-terminal-bg overflow-hidden text-text-primary">
      <KillSwitchBanner active={systemStatus.emergency_kill_switch_active} />

      {/* Live Execution Mode Banner + Scrolling NSE Ticker */}
      <div className={clsx(
        'border-b px-4 py-1.5 flex items-center justify-center gap-2 text-[11px] font-mono font-semibold tracking-widest uppercase z-40',
        systemStatus.live_trading_enabled
          ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
          : 'bg-amber-50 border-amber-200 text-amber-800'
      )}>
        <ShieldAlert size={13} />
        {systemStatus.live_trading_enabled
          ? 'LIVE EXECUTION ACTIVE — HARD RISK LIMITS ARMED'
          : 'PAPER TRADING MODE — DIRECT UPSTOX QUOTES · ZERO REAL CAPITAL RISK'}
      </div>
      <MarketTickerTape items={swingRanked} onSelectSymbol={handleInspectSymbol} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePage} onNavigate={setActivePage} />

        {activePage === 'finance' ? (
          <main className="flex-1 flex flex-col overflow-hidden bg-[#070b14]">
            <ExecutiveDeck onBackToMarket={() => setActivePage('dashboard')} />
          </main>
        ) : (
        <main className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* ── Header ── */}
          <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-blue-600 font-semibold mb-1">
                AECE NSE QUANT DESK
              </div>
              <h1 className="text-xl font-bold tracking-tight capitalize text-slate-900">
                {activePage === 'news' ? 'Intelligence' : activePage.replace(/_/g, ' ')}
              </h1>
              <div className="text-[11px] font-mono text-slate-500 mt-1 flex items-center gap-1.5">
                <Clock size={12} />
                {isMounted ? new Date().toLocaleTimeString('en-IN') : '--:--:--'} IST
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              {/* ── Live Financial Metrics Strip ── */}
              <div className="flex flex-wrap items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setCmdOpen(true)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-slate-200 hover:border-blue-300 text-xs text-slate-500 hover:text-slate-900 shadow-sm transition-colors"
                >
                  <Search size={13} className="text-slate-400" />
                  <span>Search stocks &amp; views</span>
                  <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-100 border border-slate-200 text-slate-500">
                    Ctrl K
                  </kbd>
                </button>

                <button
                  type="button"
                  onClick={() => setQuickTradeSymbol(selectedSymbol)}
                  className="px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors"
                >
                  <Sparkles size={13} />
                  Quick Order
                </button>

                {/* Capital */}
                <div className="flex flex-col items-end bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
                  <span className="text-[9px] text-slate-500 font-mono uppercase tracking-widest">Capital</span>
                  <span className="text-sm font-mono font-bold text-slate-900 tabular-nums">
                    ₹{(portfolio.equity ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>

                {/* Unrealised P&L */}
                <div className="flex flex-col items-end bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
                  <span className="text-[9px] text-slate-500 font-mono uppercase tracking-widest">Open P&amp;L</span>
                  <span className={clsx("text-sm font-mono font-bold tabular-nums", portfolio.unrealisedPnl >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                    {portfolio.unrealisedPnl >= 0 ? "+" : ""}₹{(portfolio.unrealisedPnl ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>

                {/* Total Net P&L */}
                <div className={clsx("flex flex-col items-end rounded-lg px-3 py-1.5 border shadow-sm",
                  portfolio.unrealisedPnl >= 0 ? "bg-emerald-50 border-emerald-200" : "bg-rose-50 border-rose-200"
                )}>
                  <span className="text-[9px] text-slate-500 font-mono uppercase tracking-widest">Total Net P&amp;L</span>
                  <span className={clsx("text-sm font-mono font-bold tabular-nums", portfolio.unrealisedPnl >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                    {portfolio.unrealisedPnl >= 0 ? "+" : "-"}₹{Math.abs(portfolio.unrealisedPnl ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Engine Toggle Button */}
                <button 
                  onClick={async () => {
                    const res = await fetch(`${API_BASE}/api/v1/bot/${engineStatus?.is_running ? 'stop' : 'start'}`, { method: 'POST' });
                    if(res.ok) mutateEngineStatus();
                  }}
                  className={clsx("px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors border shadow-sm", 
                    engineStatus?.is_running 
                      ? "bg-amber-50 text-amber-700 hover:bg-amber-100 border-amber-200" 
                      : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-200"
                  )}>
                  {engineStatus?.is_running ? <><Power size={14} /> Stop Engine</> : <><Power size={14} /> Start Engine</>}
                </button>
              </div>

              <div className="flex gap-2">
                <span className="status-badge"><StatusDot status="active" /> SYSTEMS ONLINE</span>
                <span className="status-badge"><StatusDot status="positive" /> {portfolio.mode === 'paper' ? 'PAPER TRADING' : 'NSE OPEN'}</span>
              </div>
            </div>
          </header>

          <div key={activePage} className="animate-page-slide space-y-6">
          {activePage === 'dashboard' && (
            <>
              <HeroSlidesCarousel
                equity={portfolio.equity}
                cash={portfolio.cash}
                marketValue={portfolio.marketValue}
                netPnl={portfolio.unrealisedPnl}
                positionsCount={positionsList.length}
                swingRecs={swingRecs}
                readiness={readiness}
                tokenStatus={tokenStatus}
                onNavigate={setActivePage}
                onInspectSymbol={handleInspectSymbol}
                onQuickTrade={(sym) => setQuickTradeSymbol(sym || selectedSymbol)}
              />

              {/* ── Portfolio stats ── */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Paper Equity"
              value={`₹${portfolio.equity.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
              sub={`${deployedPct.toFixed(1)}% DEPLOYED · CASH ₹${portfolio.cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
              trend={portfolio.dailyReturn}
            />
            <StatCard
              label="Net Paper P&L"
              value={`${portfolio.unrealisedPnl >= 0 ? '+' : '-'}₹${Math.abs(portfolio.unrealisedPnl).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
              sub={`INVESTED ₹${portfolio.marketValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
              trend={portfolio.unrealisedPnl}
            />
            <StatCard
              label="Holdout Max Drawdown"
              value={`${portfolio.drawdown.toFixed(2)}%`}
              sub="250D BLIND HOLDOUT (CAP 10%)"
              trend={portfolio.drawdown <= 10 ? 1 : -1}
            />
            <StatCard
              label="Swing OOS PF / 250d"
              value={`${portfolio.pf.toFixed(2)} / +₹${portfolio.holdoutNet.toFixed(0)}`}
              sub={readiness?.swing_oos_ready ? '8/8 GATES VALIDATED' : 'RESEARCH ONLY'}
              trend={portfolio.holdoutNet}
            />
          </section>

          {/* ── Active Strategy: Top-5 15d CNC Swing Picks ── */}
          {swingRecs.length > 0 && (
            <section className="card p-0 overflow-hidden">
              <div className="px-4 py-3 flex items-center justify-between border-b border-slate-200 bg-slate-50/80">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                  <TrendingUp size={14} className="text-fin-pos" />
                  Validated 15-Day CNC Swing Top-5 ({swingData?.as_of?.slice(0, 10) || '--'})
                </h3>
                <button
                  type="button"
                  onClick={() => setActivePage('paper')}
                  className="text-[11px] font-mono font-semibold px-3 py-1 rounded-lg border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors"
                >
                  Open Paper Swing Ledger →
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left whitespace-nowrap">
                  <thead>
                    <tr>
                      {['Rank', 'Symbol', 'Sector', '15D Trend', 'Last Close', 'Est 15d Net%', 'RSI(14)', 'Suggested Qty', 'Action'].map(h => (
                        <th key={h} className="table-header px-4 py-2">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="font-mono">
                    {swingRecs.map((r: any) => (
                      <tr
                        key={r.symbol}
                        onClick={() => handleInspectSymbol(r.symbol)}
                        className="table-row cursor-pointer"
                      >
                        <td className="px-4 py-2.5 text-text-muted">#{r.rank}</td>
                        <td className="px-4 py-2.5 font-bold text-slate-900">{r.symbol}</td>
                        <td className="px-4 py-2.5 text-text-secondary">{r.sector}</td>
                        <td className="px-4 py-1.5">
                          <Sparkline
                            values={r.sparkline_15d}
                            positive={Number(r.predicted_15d_net_pct ?? 0) >= 0}
                            height={22}
                            width={74}
                          />
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">₹{r.last_close}</td>
                        <td className="px-4 py-2.5 text-fin-pos font-semibold tabular-nums">+{r.predicted_15d_net_pct}%</td>
                        <td className="px-4 py-2.5 tabular-nums">{r.rsi14}</td>
                        <td className="px-4 py-2.5 tabular-nums">{r.suggested_qty} sh</td>
                        <td className="px-4 py-2.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setQuickTradeSymbol(r.symbol)
                            }}
                            className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-[10px] font-semibold transition-colors"
                          >
                            Order
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

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
                      <XAxis dataKey="time" tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} interval={Math.floor(equityCurve.length / 6)} />
                      <YAxis tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v.toLocaleString('en-IN', {maximumFractionDigits: 0})}`} width={70} domain={['auto', 'auto']} />
                      <Tooltip content={<EquityTooltip />} />
                      <Area type="monotone" dataKey="equity" stroke="#2563EB" strokeWidth={2} fill="url(#equityGrad)" />
                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18}/>
                          <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
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
                      <XAxis dataKey="label" tick={{ fill: '#64748B', fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v.toFixed(0)}`} width={45} />
                      <Tooltip content={<PnlTooltip />} />
                      <ReferenceLine y={0} stroke="#CBD5E1" />
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
          {activePage === 'event_radar' && <EventRadarView />}
          {activePage === 'ai_debate' && <AITerminalView />}
          {activePage === 'paper' && <PaperValidationView />}
          {activePage === 'overview' && (
            <MarketOverviewView
              onInspectSymbol={handleInspectSymbol}
              onQuickTrade={(sym) => setQuickTradeSymbol(sym)}
            />
          )}
          {activePage === 'news_intel' && <NewsSection />}
          {activePage === 'company' && (
            <CompanyIntelView
              selectedSymbol={selectedSymbol}
              onQuickTrade={(sym) => setQuickTradeSymbol(sym)}
            />
          )}
          {activePage === 'causal_map' && <CausalMapView />}
          {activePage === 'expectations' && <ExpectationsView />}
          {activePage === 'priced_in' && <PricedInView />}
          {activePage === 'strategy' && <StrategyLabView />}
          {activePage === 'model_lab' && <ModelLabView />}
          {activePage === 'journal' && <TradeJournalView />}
          {activePage === 'performance' && <RobustnessView />}
          {activePage === 'data_quality' && <DataQualityView />}
          {activePage === 'health' && <SystemHealthView />}
          {activePage === 'alerts' && <AlertsView />}
          
          {activePage === 'orders' && <OrderBookView />}
          {activePage === 'portfolio' && <PortfolioView />}
          {activePage === 'risk' && <RiskMonitorView />}
          {activePage === 'bot' && <TradingBotView />}
          {activePage === 'settings' && <TokenSettingsView />}
          {activePage === 'backtest' && <BacktestingView />}
          </div>
        </main>
        )}
      </div>

      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2.5 bg-white border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl shadow-[0_14px_32px_-8px_rgba(5,150,105,0.28)] animate-page-slide">
          <CheckCircle size={16} className="text-emerald-600 shrink-0" />
          <span className="text-xs font-semibold">{toastMsg}</span>
        </div>
      )}

      {quickTradeSymbol && (
        <QuickOrderModal
          symbol={quickTradeSymbol}
          symbols={swingData?.universe_symbols || ['TECHM', 'RELIANCE', 'TCS', 'COALINDIA', 'WIPRO', 'ADANIPORTS', 'NESTLEIND']}
          cash={portfolio.cash}
          onClose={() => setQuickTradeSymbol(null)}
          onOrderFilled={handleOrderFilled}
        />
      )}

      {cmdOpen && (
        <CommandPaletteModal
          symbols={swingData?.universe_symbols || ['TECHM', 'RELIANCE', 'TCS', 'COALINDIA', 'WIPRO', 'ADANIPORTS', 'NESTLEIND']}
          navItems={QUICK_NAV_ITEMS}
          onSelectPage={setActivePage}
          onSelectSymbol={handleInspectSymbol}
          onClose={() => setCmdOpen(false)}
        />
      )}
    </div>
  )
}
