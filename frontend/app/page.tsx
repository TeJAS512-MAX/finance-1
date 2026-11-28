'use client'

import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  Activity, Clock, Power, ShieldAlert, TrendingDown, TrendingUp, Minus
} from 'lucide-react'
import clsx from 'clsx'
import useSWR from 'swr'
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

export default function DashboardPage() {
  const [activePage, setActivePage] = useState('dashboard')
  const [isMounted, setIsMounted] = useState(false)
  
  // Poll the backend every 3 seconds
  const { data, isValidating } = useSWR(`${API_BASE}/api/v1/signals`, fetcher, { refreshInterval: 3000 })
  const liveSignals = data?.signals || []
  
  useEffect(() => setIsMounted(true), [])

  const { data: healthDetail } = useSWR(`${API_BASE}/health/detail`, fetcher, { refreshInterval: 10000 })
  const systemStatus: SystemStatus = {
    live_trading_enabled: Boolean(healthDetail?.safety_flags?.live_trading_enabled ?? false),
    emergency_kill_switch_active: Boolean(healthDetail?.safety_flags?.emergency_kill_switch_active ?? false),
    version: healthDetail?.version || '1.0.0',
    env: healthDetail?.env || 'development',
  }

  // Fetch real portfolio data from the backend
  const { data: portfolioData } = useSWR(`${API_BASE}/api/v1/portfolio`, fetcher, { refreshInterval: 2000 })
  
  // Fetch real equity history for the chart
  const [historyMode, setHistoryMode] = useState<'stocks' | 'crypto'>('stocks')
  const { data: historyData } = useSWR(`${API_BASE}/api/v1/portfolio/history?market_mode=${historyMode}`, fetcher, { refreshInterval: 5000 })
  const equityCurve = historyData?.history || []
  const pnlBars = historyData?.trades || []
  
  // Fetch Engine Status & Verified Readiness / Swing Top-5
  const { data: engineStatus, mutate: mutateEngineStatus } = useSWR(`${API_BASE}/api/v1/bot/status`, fetcher, { refreshInterval: 2000 })
  const { data: readiness } = useSWR(`${API_BASE}/api/v1/bot/readiness`, fetcher, { refreshInterval: 15000 })
  const { data: swingData } = useSWR(`${API_BASE}/api/v1/signals/swing`, fetcher, { refreshInterval: 15000 })

  const swingSummary = readiness?.swing_15d_model?.summary
  const holdout = readiness?.swing_15d_model?.blind_holdout
  const swingRecs = swingData?.recommendations || []
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
      
      {/* Permanent Paper Trading Banner */}
      <div className="bg-fin-warn/10 border-b border-fin-warn/30 text-fin-warn px-4 py-2 flex items-center justify-center gap-2 text-xs font-semibold tracking-widest uppercase z-50">
        <ShieldAlert size={14} />
        {systemStatus.live_trading_enabled
          ? 'LIVE TRADING ENABLED — HARD RISK LIMITS ACTIVE'
          : 'PAPER TRADING — LIVE EXECUTION DISABLED'}
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
                  <span className="text-[9px] text-text-muted font-mono uppercase tracking-widest">Total Net P&amp;L</span>
                  <span className={clsx("text-sm font-mono font-bold", portfolio.unrealisedPnl >= 0 ? "text-fin-pos" : "text-fin-neg")}>
                    {portfolio.unrealisedPnl >= 0 ? "+" : "-"}₹{Math.abs(portfolio.unrealisedPnl ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Divider */}
                <div className="h-8 w-px bg-terminal-border" />

                {/* Engine Toggle Button */}
                <button 
                  onClick={async () => {
                    const res = await fetch(`${API_BASE}/api/v1/bot/${engineStatus?.is_running ? 'stop' : 'start'}`, { method: 'POST' });
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
              <div className="px-4 py-3 flex items-center justify-between border-b border-terminal-border bg-terminal-surface/30">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary flex items-center gap-2">
                  <TrendingUp size={14} className="text-fin-pos" />
                  Validated 15-Day CNC Swing Top-5 ({swingData?.as_of?.slice(0, 10) || '--'})
                </h3>
                <button
                  type="button"
                  onClick={() => setActivePage('paper')}
                  className="text-[10px] font-mono px-2.5 py-1 rounded border border-accent-primary/40 text-accent-primary bg-accent-primary/10 hover:bg-accent-primary/20"
                >
                  Open Paper Swing Ledger →
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left whitespace-nowrap">
                  <thead>
                    <tr>
                      {['Rank', 'Symbol', 'Sector', 'Last Close', 'Est 15d Net%', 'RSI(14)', 'Suggested Qty'].map(h => (
                        <th key={h} className="table-header px-4 py-2">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="font-mono">
                    {swingRecs.map((r: any) => (
                      <tr key={r.symbol} className="table-row">
                        <td className="px-4 py-2 text-text-muted">#{r.rank}</td>
                        <td className="px-4 py-2 font-bold">{r.symbol}</td>
                        <td className="px-4 py-2 text-text-secondary">{r.sector}</td>
                        <td className="px-4 py-2">₹{r.last_close}</td>
                        <td className="px-4 py-2 text-fin-pos font-semibold">+{r.predicted_15d_net_pct}%</td>
                        <td className="px-4 py-2">{r.rsi14}</td>
                        <td className="px-4 py-2">{r.suggested_qty} sh</td>
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
          {activePage === 'event_radar' && <EventRadarView />}
          {activePage === 'ai_debate' && <AITerminalView />}
          {activePage === 'paper' && <PaperValidationView />}
          {activePage === 'overview' && <MarketOverviewView />}
          {activePage === 'news_intel' && <NewsSection />}
          {activePage === 'company' && <CompanyIntelView />}
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
        </main>
        )}
      </div>
    </div>
  )
}
