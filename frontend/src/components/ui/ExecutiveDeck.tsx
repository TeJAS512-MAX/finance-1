"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import confetti from "canvas-confetti";
import {
  Send,
  Camera,
  Mic,
  Activity,
  AlertTriangle,
  Sparkles,
  TrendingUp,
  Shield,
  Scissors,
  Cpu,
  CheckCircle2,
  Copy,
  Check,
  Sliders,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Calculator,
  FileText,
  Building2,
  PieChart,
  Users,
  AlertCircle,
} from "lucide-react";
import { useAetherStore } from "@/lib/store";
import {
  fetchForecastApi,
  fetchGstPlanApi,
  fetchLedgerApi,
  fetchEmiApi,
  fetchGstCalcApi,
  fetchProfitModelApi,
} from "@/lib/api";
import {
  ForecastResponse,
  GstPlanResponse,
  LedgerResponse,
  EmiResponse,
  GstCalcResponse,
  ProfitModelResponse,
  ForecastDayItem,
  ForecastEventItem,
  GstStepItem,
  LedgerDebtorItem,
  LedgerCreditorItem,
} from "@/lib/types";
import { playUiSound } from "./AudioController";

// Helper for Indian Currency formatting
function fmtInr(num: number | undefined | null): string {
  if (num === undefined || num === null || isNaN(num)) return "₹0.00";
  return "₹" + Number(num).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function fmtCompact(num: number | undefined | null): string {
  if (num === undefined || num === null || isNaN(num)) return "₹0";
  const abs = Math.abs(num);
  const sign = num < 0 ? "-" : "";
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
  if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(0)}k`;
  return `${sign}₹${abs.toFixed(0)}`;
}

export default function ExecutiveDeck() {
  const init = useAetherStore((s) => s.init);
  const businessKey = useAetherStore((s) => s.businessKey);
  const state = useAetherStore((s) => s.state);
  const singularity = useAetherStore((s) => s.singularity);
  const messages = useAetherStore((s) => s.messages);
  const isThinking = useAetherStore((s) => s.isThinking);

  const switchBusiness = useAetherStore((s) => s.switchBusiness);
  const sendMessage = useAetherStore((s) => s.sendMessage);
  const activateWormhole = useAetherStore((s) => s.activateWormhole);
  const uploadInvoice = useAetherStore((s) => s.uploadInvoice);

  // Active Tool Tab on Right
  const [activeTab, setActiveTab] = useState<"forecast" | "gst" | "ledger" | "profit">("forecast");

  // Chat input
  const [inputText, setInputText] = useState("");
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);
  const [copiedDraftId, setCopiedDraftId] = useState<string | null>(null);

  // Tab 1: Forecast State
  const [delayDays, setDelayDays] = useState(0);
  const [discountPct, setDiscountPct] = useState(0);
  const [expenseCutPct, setExpenseCutPct] = useState(0);
  const [plannedSpend, setPlannedSpend] = useState(0);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [isForecastLoading, setIsForecastLoading] = useState(false);

  // Tab 2: GST Plan State
  const [gstPlanData, setGstPlanData] = useState<GstPlanResponse | null>(null);
  const [calcAmount, setCalcAmount] = useState(118000);
  const [calcRate, setCalcRate] = useState(18);
  const [calcMode, setCalcMode] = useState<"gross" | "net">("gross");
  const [calcResult, setCalcResult] = useState<GstCalcResponse | null>(null);

  // Tab 3: Ledger State
  const [ledgerSubTab, setLedgerSubTab] = useState<"debtors" | "creditors">("debtors");
  const [ledgerData, setLedgerData] = useState<LedgerResponse | null>(null);

  // Tab 4: Profit & Loan State
  const [loanPrincipal, setLoanPrincipal] = useState(1000000);
  const [loanRate, setLoanRate] = useState(11.0);
  const [loanTenure, setLoanTenure] = useState(36);
  const [emiResult, setEmiResult] = useState<EmiResponse | null>(null);
  const [profitData, setProfitData] = useState<ProfitModelResponse | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initial load
  useEffect(() => {
    init();
  }, [init]);

  // --- API LOADERS ---
  const loadForecast = useCallback(async () => {
    setIsForecastLoading(true);
    try {
      const data = await fetchForecastApi({
        delay_days: delayDays,
        discount_pct: discountPct,
        expense_cut_pct: expenseCutPct,
        planned_spend: plannedSpend,
      });
      setForecastData(data);
    } catch {
      // Graceful fallback if backend starting
    } finally {
      setIsForecastLoading(false);
    }
  }, [delayDays, discountPct, expenseCutPct, plannedSpend]);

  const loadGstPlan = useCallback(async () => {
    try {
      const data = await fetchGstPlanApi();
      setGstPlanData(data);
    } catch {
      // Graceful fallback
    }
  }, []);

  const loadLedger = useCallback(async () => {
    try {
      const data = await fetchLedgerApi();
      setLedgerData(data);
    } catch {
      // Graceful fallback
    }
  }, []);

  const loadProfitModel = useCallback(async () => {
    try {
      const defaults = {
        STEEL_TRADER: { sales: 2400000, cogs: 82.0, fixed: 190000, emi: 48000 },
        VASTRAKALA: { sales: 1850000, cogs: 68.0, fixed: 240000, emi: 35000 },
        NEXUS_PULSE: { sales: 3200000, cogs: 45.0, fixed: 850000, emi: 72000 },
      }[businessKey] || { sales: 2400000, cogs: 82.0, fixed: 190000, emi: 48000 };

      const data = await fetchProfitModelApi(defaults.sales, defaults.cogs, defaults.fixed, defaults.emi);
      setProfitData(data);
    } catch {
      // Graceful fallback
    }
  }, [businessKey]);

  const loadEmi = useCallback(async () => {
    try {
      const data = await fetchEmiApi(loanPrincipal, loanRate, loanTenure);
      setEmiResult(data);
    } catch {
      // Local math fallback if backend busy
      const monthlyRate = loanRate / 1200.0;
      const emi = (loanPrincipal * monthlyRate * Math.pow(1 + monthlyRate, loanTenure)) / (Math.pow(1 + monthlyRate, loanTenure) - 1);
      const totalPay = emi * loanTenure;
      setEmiResult({
        principal: loanPrincipal,
        rate_annual: loanRate,
        tenure_months: loanTenure,
        monthly_emi: Math.round(emi),
        total_interest: Math.round(totalPay - loanPrincipal),
        total_payment: Math.round(totalPay),
        verdict: {
          verdict: emi < 50000 ? "comfortable" : "stretched",
          text: `Monthly EMI is ${fmtInr(emi)}.`,
        },
      });
    }
  }, [loanPrincipal, loanRate, loanTenure]);

  const loadGstCalc = useCallback(async () => {
    try {
      const data = await fetchGstCalcApi(calcAmount, calcRate, calcMode);
      setCalcResult(data);
    } catch {
      // Local fallback
      let base: number;
      let gst: number;
      if (calcMode === "gross") {
        base = calcAmount / (1 + calcRate / 100.0);
        gst = calcAmount - base;
      } else {
        base = calcAmount;
        gst = calcAmount * (calcRate / 100.0);
      }
      setCalcResult({
        base: Math.round(base),
        gst: Math.round(gst),
        cgst: Math.round(gst / 2),
        sgst: Math.round(gst / 2),
        total: Math.round(base + gst),
      });
    }
  }, [calcAmount, calcRate, calcMode]);

  // Load right-hand tool data whenever business changes
  useEffect(() => {
    loadForecast();
    loadGstPlan();
    loadLedger();
    loadProfitModel();
    loadEmi();
    loadGstCalc();
  }, [businessKey, loadForecast, loadGstPlan, loadLedger, loadProfitModel, loadEmi, loadGstCalc]);

  // Reactive updates on forecast sliders
  useEffect(() => {
    const t = setTimeout(() => {
      loadForecast();
    }, 250);
    return () => clearTimeout(t);
  }, [delayDays, discountPct, expenseCutPct, plannedSpend, loadForecast]);

  // Reactive updates on EMI sliders
  useEffect(() => {
    loadEmi();
  }, [loanPrincipal, loanRate, loanTenure, loadEmi]);

  // Reactive updates on GST Calculator
  useEffect(() => {
    loadGstCalc();
  }, [calcAmount, calcRate, calcMode, loadGstCalc]);

  // Auto-scroll chat
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollTop = chatEndRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  // --- ACTIONS ---
  const handleSendMessage = async (textToSend?: string) => {
    const q = (textToSend || inputText).trim();
    if (!q) return;
    if (!textToSend) setInputText("");
    playUiSound("click");
    await sendMessage(q);
  };

  const handleVoiceSimulation = () => {
    playUiSound("click");
    setIsVoiceRecording(true);
    setTimeout(() => {
      setIsVoiceRecording(false);
      handleSendMessage("How is my cash runway and what GST do I owe this month?");
    }, 2400);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    playUiSound("click");
    uploadInvoice(file);
  };

  const handleLiquidityBridge = async () => {
    playUiSound("wormhole");
    confetti({
      particleCount: 120,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#10b981", "#22d3ee", "#f59e0b"],
    });
    await activateWormhole();
    loadForecast();
    loadGstPlan();
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDraftId(id);
    setTimeout(() => setCopiedDraftId(null), 2500);
  };

  // Top alert conditions
  const hasDeficit = singularity && singularity.severity !== "LOW" && singularity.days_to_event_horizon <= 10;
  const deficitAmount = singularity?.tax_vault_deficit || 152915;

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-brand-500/30">
      
      {/* 1. TOP COMMAND BAR */}
      <header className="h-16 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between shrink-0 z-30">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-500 to-accentcyan flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-brand-500/20">
            AP
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-base tracking-tight">AetherPravah</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-brand-500/15 border border-brand-500/30 text-brand-400">
                Finance AI
              </span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono hidden sm:block">
              Intelligent Cash Flow & Tax Twin for MSMEs
            </span>
          </div>
        </div>

        {/* MSME Archetype Switcher */}
        <div className="flex items-center bg-black/60 rounded-xl p-1 border border-slate-800 text-xs">
          <button
            onClick={() => switchBusiness("STEEL_TRADER")}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
              businessKey === "STEEL_TRADER"
                ? "bg-brand-600 text-white font-semibold shadow"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Bharat Steel</span>
            <span className="md:hidden">Steel</span>
          </button>
          <button
            onClick={() => switchBusiness("VASTRAKALA")}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
              businessKey === "VASTRAKALA"
                ? "bg-brand-600 text-white font-semibold shadow"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Scissors className="w-3.5 h-3.5" />
            <span className="hidden md:inline">VastraKala</span>
            <span className="md:hidden">Textiles</span>
          </button>
          <button
            onClick={() => switchBusiness("NEXUS_PULSE")}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
              businessKey === "NEXUS_PULSE"
                ? "bg-brand-600 text-white font-semibold shadow"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span className="hidden md:inline">NexusPulse</span>
            <span className="md:hidden">Agency</span>
          </button>
        </div>

        {/* Live Metrics Pill Strip */}
        <div className="flex items-center gap-3">
          {state && (
            <div className="hidden xl:flex items-center gap-4 text-xs font-mono pr-2">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Bank Cash</span>
                <span className="text-white font-bold">{fmtCompact(state.physics_state.bank_cash)}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Tax Vault</span>
                <span className="text-accentcyan font-bold">{fmtCompact(state.physics_state.tax_vault_balance)}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Runway</span>
                <span className="text-brand-400 font-bold">{state.physics_state.estimated_runway_days.toFixed(1)}d</span>
              </div>
            </div>
          )}

          {/* Health Score */}
          {state && (
            <div
              className={`px-3 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono ${
                state.genome.overall_score >= 70
                  ? "bg-brand-500/10 border-brand-500/30 text-brand-400"
                  : state.genome.overall_score >= 50
                  ? "bg-warningamber/10 border-warningamber/30 text-warningamber"
                  : "bg-dangerrose/10 border-dangerrose/30 text-dangerrose"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
              <span className="font-bold">Health: {state.genome.overall_score}/100</span>
            </div>
          )}
        </div>

      </header>

      {/* 2. PROMINENT GST ALERT STRIP (Clean & Plain Language) */}
      {hasDeficit && (
        <div className="bg-gradient-to-r from-dangerrose/20 via-warningamber/15 to-transparent border-b border-dangerrose/30 px-4 sm:px-6 py-2.5 flex items-center justify-between text-xs sm:text-sm">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-dangerrose animate-ping" />
            <AlertTriangle className="w-4 h-4 text-dangerrose shrink-0" />
            <span className="text-slate-200">
              <strong className="text-white font-semibold">GST Payment Alert:</strong>{" "}
              {fmtInr(deficitAmount)} cash shortfall due in{" "}
              <strong className="text-white font-semibold">{singularity?.days_to_event_horizon || 4} days</strong> (20 Nov).
              Unpaid customer invoices hold GST liability that must be settled in cash.
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setActiveTab("gst")}
              className="px-3 py-1 rounded-lg bg-dangerrose/20 hover:bg-dangerrose/30 text-dangerrose border border-dangerrose/40 text-xs font-semibold transition"
            >
              View GST Planner
            </button>
            <button
              onClick={handleLiquidityBridge}
              className="px-3 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition shadow-sm"
            >
              Bridge Cash
            </button>
          </div>
        </div>
      )}

      {/* 3. MAIN SPLIT STUDIO: LEFT AI CHAT (45%) | RIGHT ADVANCED FEATURES (55%) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden h-[calc(100vh-64px)]">
        
        {/* ============================================================== */}
        {/* LEFT COLUMN: FULL-HEIGHT AI FINANCE ASSISTANT (5 of 12 cols) */}
        {/* ============================================================== */}
        <section className="lg:col-span-5 flex flex-col border-r border-slate-800/80 bg-slate-950/60 relative h-full overflow-hidden">
          
          {/* Assistant Sub-Header */}
          <div className="h-12 px-4 border-b border-slate-800/80 bg-slate-950/90 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-400 animate-pulse" />
              <span className="text-xs font-semibold text-white">AI Finance Assistant</span>
              <span className="text-[10px] text-slate-400 font-mono">
                {state?.business?.gstin ? `GST: ${state.business.gstin}` : "GST Active"}
              </span>
            </div>
            <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1.5">
              <Building2 className="w-3 h-3 text-accentcyan" />
              <span>{state?.business?.city || "Navi Mumbai"}</span>
            </div>
          </div>

          {/* Quick Prompt Chips */}
          <div className="p-2.5 border-b border-slate-800/60 bg-slate-900/40 flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0 text-xs">
            <button
              onClick={() => handleSendMessage("How is my money?")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>📊</span>
              <span>How is my money?</span>
            </button>
            <button
              onClick={() => handleSendMessage("Who owes me money?")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>💰</span>
              <span>Who owes me?</span>
            </button>
            <button
              onClick={() => handleSendMessage("Can I buy machinery for 500000?")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>🚜</span>
              <span>Can I spend ₹5L?</span>
            </button>
            <button
              onClick={() => handleSendMessage("What is my GST breakdown?")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>📑</span>
              <span>GST breakdown</span>
            </button>
            <button
              onClick={() => handleSendMessage("Calculate EMI for 10 lakhs at 11% for 3 years")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>💳</span>
              <span>Calculate EMI</span>
            </button>
            <button
              onClick={() => handleSendMessage("Draft payment reminder for Reliance")}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition flex items-center gap-1"
            >
              <span>✉️</span>
              <span>Draft reminder</span>
            </button>
          </div>

          {/* Chat Message Scroll */}
          <div
            ref={chatEndRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
          >
            {/* Welcome Message if empty */}
            {messages.length === 0 && (
              <div className="p-4 rounded-xl glass-card border border-slate-800 text-xs text-slate-300 space-y-2">
                <div className="flex items-center gap-2 text-brand-400 font-semibold">
                  <Sparkles className="w-4 h-4" />
                  <span>Namaste! Your AI Finance Assistant is Active.</span>
                </div>
                <p>
                  I monitor all cash flows, unpaid customer bills, statutory GST filings, and supplier liabilities in real time. Ask me anything about your finances or pick one of the quick chips above.
                </p>
              </div>
            )}

            {/* Messages Stream */}
            {messages.map((m) => {
              const isAi = m.sender === "ai";
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isAi ? "items-start" : "items-end"} gap-1`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 px-1 font-mono">
                    <span>{isAi ? "AetherPravah AI" : "You"}</span>
                    <span>•</span>
                    <span>{m.timestamp}</span>
                  </div>

                  <div
                    className={`max-w-[92%] rounded-2xl p-3.5 text-xs sm:text-sm leading-relaxed ${
                      isAi
                        ? "bg-slate-900/90 text-slate-200 border border-slate-800/80 shadow-md"
                        : "bg-brand-600 text-white font-medium shadow-md shadow-brand-600/20"
                    }`}
                  >
                    {/* Main text content */}
                    <div className="whitespace-pre-line space-y-2">
                      {m.text}
                    </div>

                    {/* Rich Mini-Cards Rendering */}
                    {isAi && m.cards && m.cards.length > 0 && (
                      <div className="mt-3 space-y-2 pt-2 border-t border-slate-800">
                        {m.cards.map((card, cIdx) => {
                          if (card.type === "kpis" && card.items) {
                            return (
                              <div key={cIdx} className="grid grid-cols-2 gap-2 my-2">
                                {card.items.map((it, iIdx) => (
                                  <div
                                    key={iIdx}
                                    className="p-2 rounded-lg bg-black/40 border border-slate-800 flex flex-col"
                                  >
                                    <span className="text-[10px] text-slate-400 uppercase tracking-wide">
                                      {it.label}
                                    </span>
                                    <span
                                      className={`text-xs font-bold font-mono mt-0.5 ${
                                        it.tone === "danger"
                                          ? "text-dangerrose"
                                          : it.tone === "good"
                                          ? "text-brand-400"
                                          : it.tone === "accent"
                                          ? "text-accentcyan"
                                          : "text-white"
                                      }`}
                                    >
                                      {it.value}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            );
                          }

                          if (card.type === "verdict") {
                            const isGood = card.tone === "good";
                            return (
                              <div
                                key={cIdx}
                                className={`p-3 rounded-xl border my-2 ${
                                  isGood
                                    ? "bg-brand-500/10 border-brand-500/30 text-slate-200"
                                    : "bg-dangerrose/10 border-dangerrose/30 text-slate-200"
                                }`}
                              >
                                <div className="flex items-center gap-2 font-bold text-xs">
                                  {isGood ? (
                                    <CheckCircle2 className="w-4 h-4 text-brand-400" />
                                  ) : (
                                    <AlertTriangle className="w-4 h-4 text-dangerrose" />
                                  )}
                                  <span className={isGood ? "text-brand-400" : "text-dangerrose"}>
                                    {card.title}
                                  </span>
                                </div>
                                {card.text && (
                                  <p className="mt-1 text-xs text-slate-300">{card.text}</p>
                                )}
                              </div>
                            );
                          }

                          if (card.type === "table" && card.headers && card.rows) {
                            return (
                              <div key={cIdx} className="my-2 overflow-x-auto rounded-lg border border-slate-800">
                                {card.title && (
                                  <div className="bg-slate-800/60 px-2.5 py-1 text-[11px] font-semibold text-slate-200">
                                    {card.title}
                                  </div>
                                )}
                                <table className="w-full text-left text-[11px] font-mono">
                                  <thead className="bg-black/60 text-slate-400 border-b border-slate-800">
                                    <tr>
                                      {card.headers.map((h, hIdx) => (
                                        <th key={hIdx} className="p-2 font-medium">
                                          {h}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-800/60">
                                    {card.rows.map((row, rIdx) => (
                                      <tr key={rIdx} className="hover:bg-slate-800/30">
                                        {row.map((cell, cellIdx) => (
                                          <td key={cellIdx} className="p-2 text-slate-300">
                                            {cell}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            );
                          }

                          if (card.type === "draft") {
                            const draftMsg = card.whatsapp_text || card.message || "";
                            return (
                              <div
                                key={cIdx}
                                className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 my-2 space-y-2 text-xs"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-accentcyan flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5" />
                                    <span>Draft Reminder for {card.customer || "Client"}</span>
                                  </span>
                                  {card.amount && (
                                    <span className="font-mono font-bold text-white">
                                      {card.amount}
                                    </span>
                                  )}
                                </div>
                                {card.subject && (
                                  <div className="text-[11px] text-slate-400 font-mono">
                                    <strong>Subject:</strong> {card.subject}
                                  </div>
                                )}
                                <div className="p-2.5 rounded-lg bg-black/60 font-mono text-[11px] text-slate-300 whitespace-pre-wrap border border-slate-800/60">
                                  {draftMsg}
                                </div>
                                <div className="flex items-center justify-end gap-2 pt-1">
                                  <button
                                    onClick={() => copyToClipboard(`draft-${cIdx}`, draftMsg)}
                                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 flex items-center gap-1 transition"
                                  >
                                    {copiedDraftId === `draft-${cIdx}` ? (
                                      <>
                                        <Check className="w-3 h-3 text-brand-400" />
                                        <span>Copied!</span>
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="w-3 h-3" />
                                        <span>Copy WhatsApp</span>
                                      </>
                                    )}
                                  </button>
                                </div>
                              </div>
                            );
                          }

                          return null;
                        })}
                      </div>
                    )}

                    {/* Key numbers / causal box */}
                    {isAi && (m.numbers || m.causalExplanation) && (
                      <div className="mt-2.5 pt-2 border-t border-slate-800/60 text-xs space-y-2 font-mono">
                        {m.numbers && (
                          <div className="p-2 rounded bg-black/30 border border-slate-800/40 text-slate-300 whitespace-pre-line text-[11px]">
                            {m.numbers}
                          </div>
                        )}
                        {m.causalExplanation && (
                          <div className="text-[11px] text-slate-400">
                            <strong className="text-accentcyan">Root Cause:</strong> {m.causalExplanation}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Recommendations checklist */}
                    {isAi && m.recommendations && m.recommendations.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-slate-800/60 space-y-1.5 text-xs">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-brand-400 block">
                          Recommended Actions:
                        </span>
                        {m.recommendations.map((rec, rIdx) => (
                          <div key={rIdx} className="flex items-start gap-1.5 text-slate-300 text-xs">
                            <CheckCircle2 className="w-3.5 h-3.5 text-brand-400 shrink-0 mt-0.5" />
                            <span>{rec}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Suggestion prompt chips */}
                    {isAi && m.suggestions && m.suggestions.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-slate-800/60 flex flex-wrap gap-1.5">
                        {m.suggestions.map((sug, sIdx) => (
                          <button
                            key={sIdx}
                            onClick={() => handleSendMessage(sug)}
                            className="px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700 transition"
                          >
                            {sug}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Thinking indicator */}
            {isThinking && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 w-fit">
                <div className="w-4 h-4 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
                <span>AI analyzing cash flow & tax twin...</span>
              </div>
            )}
          </div>

          {/* Bottom Chat Command Bar */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-950/90 shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2 bg-slate-900/90 rounded-xl p-1.5 border border-slate-800 focus-within:border-brand-500 transition"
            >
              {/* Document / Camera upload */}
              <label className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 cursor-pointer transition">
                <Camera className="w-4 h-4" />
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </label>

              {/* Voice Note Simulation */}
              <button
                type="button"
                onClick={handleVoiceSimulation}
                className={`p-2 rounded-lg transition ${
                  isVoiceRecording
                    ? "bg-dangerrose text-white animate-pulse"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
                title="Simulate Voice Prompt"
              >
                <Mic className="w-4 h-4" />
              </button>

              {/* Main Text Input */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask about cash runway, GST due, loans, or invoices..."
                className="flex-1 bg-transparent border-none text-xs sm:text-sm text-white focus:outline-none placeholder:text-slate-500"
              />

              {/* Send Button */}
              <button
                type="submit"
                disabled={!inputText.trim()}
                className={`p-2 rounded-lg transition flex items-center justify-center ${
                  inputText.trim()
                    ? "bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-600/30"
                    : "bg-slate-800 text-slate-500 cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-500 px-1 font-mono">
              <span>Strict Rupee Conservation Active</span>
              <span>100% Indian MSME Compliant</span>
            </div>
          </div>

        </section>

        {/* ============================================================== */}
        {/* RIGHT COLUMN: 4 ADVANCED FINANCIAL TOOL TABS (7 of 12 cols)    */}
        {/* ============================================================== */}
        <section className="lg:col-span-7 flex flex-col bg-slate-950/40 relative h-full overflow-hidden">
          
          {/* Tab Bar Header */}
          <div className="h-12 px-4 border-b border-slate-800/80 bg-slate-950/90 flex items-center justify-between shrink-0 overflow-x-auto no-scrollbar">
            <div className="flex items-center gap-1.5 text-xs">
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("forecast");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === "forecast"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5 text-brand-400" />
                <span>Cash-Flow Forecast & What-If</span>
              </button>

              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("gst");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === "gst"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5 text-warningamber" />
                <span>GST & Tax Planner</span>
              </button>

              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("ledger");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === "ledger"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Users className="w-3.5 h-3.5 text-accentcyan" />
                <span>Who Owes Me / Who I Owe</span>
              </button>

              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("profit");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === "profit"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Calculator className="w-3.5 h-3.5 text-purple-400" />
                <span>Profit & Loan/EMI Tools</span>
              </button>
            </div>
          </div>

          {/* Tab Content Body */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            
            {/* ------------------------------------------------------------ */}
            {/* TAB 1: CASH-FLOW FORECAST & WHAT-IF                          */}
            {/* ------------------------------------------------------------ */}
            {activeTab === "forecast" && (
              <div className="space-y-6">
                
                {/* KPI Overview Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl glass-card border border-slate-800">
                    <span className="text-[11px] text-slate-400 block uppercase font-mono">
                      Lowest Projected Dip
                    </span>
                    <span
                      className={`text-lg sm:text-xl font-bold font-mono mt-1 block ${
                        (forecastData?.summary?.lowest_balance || -192915) < 0
                          ? "text-dangerrose"
                          : "text-brand-400"
                      }`}
                    >
                      {fmtInr(forecastData?.summary?.lowest_balance ?? -192915)}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5 block">
                      on {forecastData?.summary?.lowest_date_label || "20 Nov 2026"}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl glass-card border border-slate-800">
                    <span className="text-[11px] text-slate-400 block uppercase font-mono">
                      Estimated Runway
                    </span>
                    <span className="text-lg sm:text-xl font-bold font-mono text-warningamber mt-1 block">
                      {forecastData?.summary?.estimated_runway_days ?? 4.0} Days
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5 block">
                      Before negative cash dip
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl glass-card border border-slate-800">
                    <span className="text-[11px] text-slate-400 block uppercase font-mono">
                      Current Bank Cash
                    </span>
                    <span className="text-lg sm:text-xl font-bold font-mono text-white mt-1 block">
                      {fmtInr(forecastData?.summary?.starting_cash ?? 185000)}
                    </span>
                    <span className="text-[10px] text-brand-400 font-mono mt-0.5 block">
                      Liquid reserves
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl glass-card border border-slate-800">
                    <span className="text-[11px] text-slate-400 block uppercase font-mono">
                      Daily Operating Burn
                    </span>
                    <span className="text-lg sm:text-xl font-bold font-mono text-slate-200 mt-1 block">
                      {fmtInr(forecastData?.summary?.daily_burn_rate ?? 8000)}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5 block">
                      Fixed rent + payroll
                    </span>
                  </div>
                </div>

                {/* Interactive Sliders: What-If Simulator */}
                <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-brand-400" />
                      <h3 className="font-semibold text-sm text-white">
                        Dynamic What-If Scenario Levers
                      </h3>
                    </div>
                    <button
                      onClick={() => {
                        setDelayDays(0);
                        setDiscountPct(0);
                        setExpenseCutPct(0);
                        setPlannedSpend(0);
                      }}
                      className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Reset</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Slider 1: Customer Delay */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Customer Payment Delay</span>
                        <span className="font-mono text-brand-400 font-bold">
                          {delayDays > 0 ? `+${delayDays} Days` : `${delayDays} Days`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-10"
                        max="30"
                        value={delayDays}
                        onChange={(e) => setDelayDays(Number(e.target.value))}
                        className="w-full accent-brand-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                      <span className="text-[10px] text-slate-500">
                        Models buyers paying faster (-10d) or defaulting/lagging (+30d)
                      </span>
                    </div>

                    {/* Slider 2: Prompt Settlement Discount */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Prompt Discount Offered</span>
                        <span className="font-mono text-accentcyan font-bold">{discountPct}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="5"
                        step="0.5"
                        value={discountPct}
                        onChange={(e) => setDiscountPct(Number(e.target.value))}
                        className="w-full accent-accentcyan h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                      <span className="text-[10px] text-slate-500">
                        Offers 2% rebate to accelerate collections within 48 hours
                      </span>
                    </div>

                    {/* Slider 3: Expense Reduction */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Cut Operating Expenses</span>
                        <span className="font-mono text-warningamber font-bold">{expenseCutPct}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="30"
                        step="5"
                        value={expenseCutPct}
                        onChange={(e) => setExpenseCutPct(Number(e.target.value))}
                        className="w-full accent-warningamber h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                      <span className="text-[10px] text-slate-500">
                        Reduces discretionary burn to stretch cash runway
                      </span>
                    </div>

                    {/* Slider 4: Planned Capex Purchase */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Planned Capex / Spend</span>
                        <span className="font-mono text-purple-400 font-bold">
                          {fmtInr(plannedSpend)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1000000"
                        step="50000"
                        value={plannedSpend}
                        onChange={(e) => setPlannedSpend(Number(e.target.value))}
                        className="w-full accent-purple-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                      <span className="text-[10px] text-slate-500">
                        Tests if you can afford to buy equipment or hire immediately
                      </span>
                    </div>
                  </div>
                </div>

                {/* 45-Day Cash Flow Trajectory Visual */}
                <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                      <Activity className="w-4 h-4 text-accentcyan" />
                      <span>45-Day Day-by-Day Cash Balance Trajectory</span>
                    </h3>
                    <span className="text-xs text-slate-400 font-mono">
                      {isForecastLoading ? "Simulating..." : "Real-time Pearlian Engine"}
                    </span>
                  </div>

                  {/* Daily Balance Bar Chart Representation */}
                  <div className="h-40 flex items-end gap-1 pt-4 pb-2 border-b border-slate-800/80 overflow-x-auto">
                    {forecastData?.daily?.map((d: ForecastDayItem, idx: number) => {
                      const isNegative = d.balance < 0;
                      // Height scaling between 0 and 100%
                      const maxAbs = 600000;
                      const heightPct = Math.min(100, Math.max(12, (Math.abs(d.balance) / maxAbs) * 100));

                      return (
                        <div
                          key={idx}
                          className="flex-1 min-w-[14px] flex flex-col items-center justify-end group relative"
                        >
                          {/* Tooltip on Hover */}
                          <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center bg-black/90 text-white text-[10px] font-mono p-2 rounded border border-slate-700 whitespace-nowrap z-20 shadow-xl">
                            <span className="font-bold text-accentcyan">{d.date}</span>
                            <span>Balance: {fmtInr(d.balance)}</span>
                            {d.inflow > 0 && <span className="text-brand-400">+In: {fmtInr(d.inflow)}</span>}
                            {d.outflow > 0 && <span className="text-dangerrose">-Out: {fmtInr(d.outflow)}</span>}
                          </div>

                          <div
                            style={{ height: `${heightPct}%` }}
                            className={`w-full rounded-t transition-all ${
                              isNegative
                                ? "bg-dangerrose/80 group-hover:bg-dangerrose"
                                : d.balance < 100000
                                ? "bg-warningamber/80 group-hover:bg-warningamber"
                                : "bg-brand-500/80 group-hover:bg-brand-400"
                            }`}
                          />
                          {idx % 7 === 0 && (
                            <span className="text-[9px] text-slate-500 font-mono mt-1">
                              {d.date.split(" ")[0]}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Landmark Events Table */}
                  <div className="space-y-2 pt-2">
                    <span className="text-xs font-semibold text-slate-300 block">
                      Critical Cash Milestones:
                    </span>
                    <div className="space-y-1.5 text-xs font-mono">
                      {forecastData?.events?.slice(0, 5).map((ev: ForecastEventItem, idx: number) => (
                        <div
                          key={idx}
                          className={`p-2 rounded-lg border flex items-center justify-between ${
                            ev.is_negative
                              ? "bg-dangerrose/10 border-dangerrose/30 text-slate-200"
                              : "bg-black/30 border-slate-800 text-slate-300"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            <strong className="text-white">{ev.date}:</strong>
                            <span>{ev.description}</span>
                          </div>
                          <span className={`font-bold ${ev.is_negative ? "text-dangerrose" : "text-brand-400"}`}>
                            Bal: {fmtInr(ev.balance)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Action Bridge Button */}
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={handleLiquidityBridge}
                      className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 transition shadow-lg shadow-brand-600/30"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>Activate Cash Bridge (Unlock Receivables)</span>
                    </button>
                  </div>
                </div>

              </div>
            )}

            {/* ------------------------------------------------------------ */}
            {/* TAB 2: GST & TAX PLANNER                                     */}
            {/* ------------------------------------------------------------ */}
            {activeTab === "gst" && (
              <div className="space-y-6">
                
                {/* Countdown Banner */}
                <div className="p-4 rounded-2xl bg-gradient-to-r from-dangerrose/15 via-black/40 to-black/40 border border-dangerrose/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-dangerrose/20 border border-dangerrose/40 flex items-center justify-center font-bold text-dangerrose">
                      3B
                    </div>
                    <div>
                      <h3 className="font-bold text-sm text-white">
                        GSTR-3B Statutory Filing Due in {gstPlanData?.days_left ?? 4} Days
                      </h3>
                      <span className="text-xs text-slate-400 font-mono">
                        Mandatory settlement deadline: {gstPlanData?.due_label || "20 Nov 2026"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">
                      Cash Shortfall
                    </span>
                    <span className="text-lg font-bold font-mono text-dangerrose">
                      {fmtInr(gstPlanData?.still_to_arrange ?? 152915)}
                    </span>
                  </div>
                </div>

                {/* Statutory Ledger Cards Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-3 rounded-xl glass-card border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-mono">
                      Output GST
                    </span>
                    <span className="text-sm sm:text-base font-bold font-mono text-white mt-1 block">
                      {fmtInr(gstPlanData?.output_gst ?? 445215)}
                    </span>
                    <span className="text-[9px] text-slate-500 mt-0.5 block">Accrued on sales</span>
                  </div>

                  <div className="p-3 rounded-xl glass-card border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-mono">
                      Eligible ITC
                    </span>
                    <span className="text-sm sm:text-base font-bold font-mono text-accentcyan mt-1 block">
                      {fmtInr(gstPlanData?.itc_claimed ?? 160300)}
                    </span>
                    <span className="text-[9px] text-slate-500 mt-0.5 block">Input tax credit</span>
                  </div>

                  <div className="p-3 rounded-xl glass-card border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-mono">
                      Net Cash Due
                    </span>
                    <span className="text-sm sm:text-base font-bold font-mono text-white mt-1 block">
                      {fmtInr(gstPlanData?.net_payable ?? 284915)}
                    </span>
                    <span className="text-[9px] text-dangerrose mt-0.5 block">Legal mandate</span>
                  </div>

                  <div className="p-3 rounded-xl glass-card border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-mono">
                      Tax Vault
                    </span>
                    <span className="text-sm sm:text-base font-bold font-mono text-brand-400 mt-1 block">
                      {fmtInr(gstPlanData?.in_vault ?? 35000)}
                    </span>
                    <span className="text-[9px] text-slate-500 mt-0.5 block">Reserved cash</span>
                  </div>

                  <div className="p-3 rounded-xl glass-card border border-slate-800">
                    <span className="text-[10px] text-slate-400 block uppercase font-mono">
                      Deficit Gap
                    </span>
                    <span className="text-sm sm:text-base font-bold font-mono text-dangerrose mt-1 block">
                      {fmtInr(gstPlanData?.still_to_arrange ?? 152915)}
                    </span>
                    <span className="text-[9px] text-dangerrose mt-0.5 block">Urgent to fund</span>
                  </div>
                </div>

                {/* Accrual Trap Explanation */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-2">
                  <div className="flex items-center gap-2 text-warningamber font-semibold">
                    <AlertCircle className="w-4 h-4" />
                    <span>The GST Accrual Trap (CGST Act Section 39)</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    Under Indian GST law, tax liability occurs on invoice issuance date, not when the buyer pays. Currently,{" "}
                    <strong className="text-white font-mono">{fmtInr(gstPlanData?.gst_on_unpaid ?? 369915)}</strong> of your tax liability is locked in invoices whose customers have delayed payment. You must arrange liquid funds to pay the government by 20 Nov.
                  </p>
                  <div className="flex justify-end pt-1">
                    <button
                      onClick={() => handleSendMessage("Draft payment reminder for Reliance to clear GST shortfall")}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium border border-slate-700 transition"
                    >
                      Follow up on Trapped GST Invoices →
                    </button>
                  </div>
                </div>

                {/* Instant GST Split Calculator */}
                <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-4">
                  <div className="flex items-center gap-2">
                    <Calculator className="w-4 h-4 text-accentcyan" />
                    <h3 className="font-semibold text-sm text-white">
                      Instant GST Split & Tax Calculator
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Invoice Amount (₹)</label>
                      <input
                        type="number"
                        value={calcAmount}
                        onChange={(e) => setCalcAmount(Number(e.target.value))}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs font-mono text-white"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">GST Slab Rate</label>
                      <select
                        value={calcRate}
                        onChange={(e) => setCalcRate(Number(e.target.value))}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs font-mono text-white"
                      >
                        <option value={5}>5% (Basic Goods)</option>
                        <option value={12}>12% (Processed Goods)</option>
                        <option value={18}>18% (Standard B2B / Services)</option>
                        <option value={28}>28% (Luxury / Automobiles)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Mode</label>
                      <div className="flex rounded-lg overflow-hidden border border-slate-700">
                        <button
                          type="button"
                          onClick={() => setCalcMode("gross")}
                          className={`flex-1 py-2 text-xs font-medium transition ${
                            calcMode === "gross" ? "bg-brand-600 text-white" : "bg-slate-900 text-slate-400"
                          }`}
                        >
                          Inclusive
                        </button>
                        <button
                          type="button"
                          onClick={() => setCalcMode("net")}
                          className={`flex-1 py-2 text-xs font-medium transition ${
                            calcMode === "net" ? "bg-brand-600 text-white" : "bg-slate-900 text-slate-400"
                          }`}
                        >
                          Exclusive
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Calculator Breakdown Results */}
                  {calcResult && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800 text-xs font-mono">
                      <div className="p-2.5 rounded bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block">Base Price</span>
                        <span className="font-bold text-white text-sm">{fmtInr(calcResult.base)}</span>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block">Total GST ({calcRate}%)</span>
                        <span className="font-bold text-accentcyan text-sm">{fmtInr(calcResult.gst)}</span>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block">CGST + SGST</span>
                        <span className="font-bold text-slate-300 text-sm">
                          {fmtInr(calcResult.cgst)} each
                        </span>
                      </div>
                      <div className="p-2.5 rounded bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block">Total Invoice Value</span>
                        <span className="font-bold text-brand-400 text-sm">{fmtInr(calcResult.total)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Compliance Steps Checklist */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">Statutory Compliance Action Plan</h4>
                  <div className="space-y-1.5 text-xs">
                    {gstPlanData?.steps?.map((st: GstStepItem, sIdx: number) => (
                      <div key={sIdx} className="p-3 rounded-xl bg-black/30 border border-slate-800 flex items-start gap-2.5">
                        <CheckCircle2 className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-white block">{st.title}</strong>
                          <span className="text-slate-400 text-xs">{st.detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            )}

            {/* ------------------------------------------------------------ */}
            {/* TAB 3: WHO OWES ME / WHO I OWE                               */}
            {/* ------------------------------------------------------------ */}
            {activeTab === "ledger" && (
              <div className="space-y-6">
                
                {/* Sub-tab toggle */}
                <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                  <button
                    onClick={() => setLedgerSubTab("debtors")}
                    className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 ${
                      ledgerSubTab === "debtors"
                        ? "bg-brand-600 text-white"
                        : "bg-slate-900 text-slate-400 hover:text-white"
                    }`}
                  >
                    <ArrowDownRight className="w-4 h-4 text-brand-300" />
                    <span>Who Owes Me (Debtors & Invoices)</span>
                  </button>
                  <button
                    onClick={() => setLedgerSubTab("creditors")}
                    className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 ${
                      ledgerSubTab === "creditors"
                        ? "bg-brand-600 text-white"
                        : "bg-slate-900 text-slate-400 hover:text-white"
                    }`}
                  >
                    <ArrowUpRight className="w-4 h-4 text-dangerrose" />
                    <span>Who I Owe (Creditors, Taxes & EMIs)</span>
                  </button>
                </div>

                {/* DEBTORS VIEW */}
                {ledgerSubTab === "debtors" && (
                  <div className="space-y-4">
                    {/* Summary row */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Total Pending Receivables
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-white mt-1 block">
                          {fmtInr(ledgerData?.debtors?.summary?.total_pending ?? 2845000)}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Already Overdue
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-dangerrose mt-1 block">
                          {fmtInr(ledgerData?.debtors?.summary?.overdue_amount ?? 420000)}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Expected in 30 Days
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-brand-400 mt-1 block">
                          {fmtInr(ledgerData?.debtors?.summary?.expected_30_days ?? 1250000)}
                        </span>
                      </div>
                    </div>

                    {/* Invoices List */}
                    <div className="space-y-2.5">
                      <span className="text-xs font-semibold text-slate-300 block">
                        Open Customer Invoices:
                      </span>
                      {ledgerData?.debtors?.invoices?.map((inv: LedgerDebtorItem) => {
                        const isOverdue = inv.days_overdue > 0;
                        return (
                          <div
                            key={inv.id}
                            className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                              isOverdue
                                ? "bg-dangerrose/10 border-dangerrose/30"
                                : "bg-black/30 border-slate-800"
                            }`}
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-sm text-white">{inv.customer_name}</span>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                                  #{inv.invoice_number}
                                </span>
                                {isOverdue ? (
                                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-dangerrose/20 text-dangerrose">
                                    {inv.days_overdue}d Overdue
                                  </span>
                                ) : (
                                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-500/15 text-brand-400">
                                    Due in {inv.due_label}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-400 font-mono">
                                <span>Total: {fmtInr(inv.amount)}</span>
                                <span className="mx-2">•</span>
                                <span>Accrued GST: {fmtInr(inv.gst_amount)}</span>
                                <span className="mx-2">•</span>
                                <span>Expected: {inv.expected_label}</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleSendMessage(`Draft payment reminder for ${inv.customer_name} for invoice ${inv.invoice_number}`)}
                                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white border border-slate-700 transition"
                              >
                                Draft Reminder
                              </button>
                              <button
                                onClick={() => handleSendMessage(`Offer 2% prompt discount to ${inv.customer_name} to clear today`)}
                                className="px-3 py-1.5 rounded-lg bg-brand-600/30 hover:bg-brand-600/40 text-brand-300 text-xs font-medium border border-brand-500/40 transition"
                              >
                                Offer 2% Discount
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* CREDITORS VIEW */}
                {ledgerSubTab === "creditors" && (
                  <div className="space-y-4">
                    {/* Summary row */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Total Payables
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-white mt-1 block">
                          {fmtInr(ledgerData?.creditors?.summary?.total_payables ?? 625000)}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Available Liquid Cash
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-brand-400 mt-1 block">
                          {fmtInr(ledgerData?.creditors?.summary?.bank_cash ?? 185000)}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl glass-card border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">
                          Coverage Deficit
                        </span>
                        <span className="text-base sm:text-lg font-bold font-mono text-dangerrose mt-1 block">
                          {fmtInr(ledgerData?.creditors?.summary?.coverage_deficit ?? 440000)}
                        </span>
                      </div>
                    </div>

                    {/* Liabilities List */}
                    <div className="space-y-2.5">
                      <span className="text-xs font-semibold text-slate-300 block">
                        Mandatory Obligations & Debts:
                      </span>
                      {ledgerData?.creditors?.liabilities?.map((lib: LedgerCreditorItem) => (
                        <div
                          key={lib.id}
                          className="p-3.5 rounded-xl bg-black/30 border border-slate-800 flex items-center justify-between"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm text-white">{lib.name}</span>
                              <span
                                className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                                  lib.priority === 1
                                    ? "bg-dangerrose/20 text-dangerrose"
                                    : "bg-warningamber/20 text-warningamber"
                                }`}
                              >
                                {lib.priority_label}
                              </span>
                            </div>
                            <div className="text-xs text-slate-400 font-mono">
                              <span>Due on: {lib.due_label} ({lib.days_left}d left)</span>
                              <span className="mx-2">•</span>
                              <span>Category: {lib.category}</span>
                            </div>
                          </div>

                          <span className="font-bold font-mono text-sm text-white">
                            {fmtInr(lib.amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}

            {/* ------------------------------------------------------------ */}
            {/* TAB 4: PROFIT, EXPENSES & LOAN/EMI TOOLS                     */}
            {/* ------------------------------------------------------------ */}
            {activeTab === "profit" && (
              <div className="space-y-6">
                
                {/* Business Model & Profit Breakdown */}
                <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-4">
                  <div className="flex items-center gap-2">
                    <PieChart className="w-4 h-4 text-brand-400" />
                    <h3 className="font-semibold text-sm text-white">
                      Monthly Profit & Break-Even Model
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Monthly Sales</span>
                      <span className="text-base font-bold text-white mt-1 block">
                        {fmtInr(profitData?.monthly_sales ?? 2400000)}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">COGS (Direct Costs)</span>
                      <span className="text-base font-bold text-slate-300 mt-1 block">
                        {profitData?.cogs_percentage ?? 82}%
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Operating Profit</span>
                      <span className="text-base font-bold text-brand-400 mt-1 block">
                        {fmtInr(profitData?.operating_profit ?? 242000)}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Net Profit</span>
                      <span className="text-base font-bold text-white mt-1 block">
                        {fmtInr(profitData?.net_profit ?? 194000)}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-xs flex items-center justify-between">
                    <span className="text-slate-300">
                      Monthly Break-Even Sales Volume required to cover all fixed costs:
                    </span>
                    <strong className="text-accentcyan font-mono text-sm">
                      {fmtInr(profitData?.break_even_sales ?? 1322222)}
                    </strong>
                  </div>
                </div>

                {/* Interactive Loan EMI Calculator */}
                <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-4">
                  <div className="flex items-center gap-2">
                    <Calculator className="w-4 h-4 text-purple-400" />
                    <h3 className="font-semibold text-sm text-white">
                      Loan EMI & Debt Serviceability Calculator
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Principal */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Loan Amount (Principal)</span>
                        <span className="font-mono text-purple-400 font-bold">{fmtInr(loanPrincipal)}</span>
                      </div>
                      <input
                        type="range"
                        min="100000"
                        max="5000000"
                        step="50000"
                        value={loanPrincipal}
                        onChange={(e) => setLoanPrincipal(Number(e.target.value))}
                        className="w-full accent-purple-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                    </div>

                    {/* Interest Rate */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Annual Interest Rate</span>
                        <span className="font-mono text-brand-400 font-bold">{loanRate}% p.a.</span>
                      </div>
                      <input
                        type="range"
                        min="8"
                        max="18"
                        step="0.5"
                        value={loanRate}
                        onChange={(e) => setLoanRate(Number(e.target.value))}
                        className="w-full accent-brand-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                    </div>

                    {/* Tenure */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">Tenure (Months)</span>
                        <span className="font-mono text-accentcyan font-bold">{loanTenure} Mo ({(loanTenure/12).toFixed(1)} Yrs)</span>
                      </div>
                      <input
                        type="range"
                        min="6"
                        max="60"
                        step="6"
                        value={loanTenure}
                        onChange={(e) => setLoanTenure(Number(e.target.value))}
                        className="w-full accent-accentcyan h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* EMI Results Grid */}
                  {emiResult && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t border-slate-800 text-xs font-mono">
                      <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/30">
                        <span className="text-[10px] text-purple-300 block uppercase">Monthly EMI</span>
                        <span className="text-base sm:text-lg font-bold text-white mt-1 block">
                          {fmtInr(emiResult.monthly_emi)}
                        </span>
                      </div>

                      <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Total Interest</span>
                        <span className="text-base sm:text-lg font-bold text-warningamber mt-1 block">
                          {fmtInr(emiResult.total_interest)}
                        </span>
                      </div>

                      <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Total Repayment</span>
                        <span className="text-base sm:text-lg font-bold text-slate-200 mt-1 block">
                          {fmtInr(emiResult.total_payment)}
                        </span>
                      </div>

                      <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block uppercase">Debt Verdict</span>
                        <span
                          className={`text-sm font-bold mt-1 block uppercase ${
                            emiResult.verdict?.verdict === "comfortable"
                              ? "text-brand-400"
                              : emiResult.verdict?.verdict === "stretched"
                              ? "text-warningamber"
                              : "text-dangerrose"
                          }`}
                        >
                          {emiResult.verdict?.verdict || "Comfortable"}
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-slate-400">
                      {emiResult?.verdict?.text || "Based on reducing balance amortization method."}
                    </span>
                    <button
                      onClick={() => handleSendMessage(`Can I afford a loan of ${fmtCompact(loanPrincipal)} at ${loanRate}% for ${loanTenure} months?`)}
                      className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium border border-slate-700 transition"
                    >
                      Ask AI About This Loan →
                    </button>
                  </div>
                </div>

              </div>
            )}

          </div>

        </section>

      </div>

    </div>
  );
}
