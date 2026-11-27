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
  Edit3,
  X,
  Plus,
  LogOut,
  ExternalLink,
} from "lucide-react";
import { UserAuthData } from "./LoginPage";
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

const MARKET_APP_URL =
  process.env.NEXT_PUBLIC_MARKET_APP_URL || "http://localhost:3000";

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

interface ExecutiveDeckProps {
  user?: UserAuthData | null;
  onLogout?: () => void;
}

export default function ExecutiveDeck({ user, onLogout }: ExecutiveDeckProps) {
  const init = useAetherStore((s) => s.init);
  const state = useAetherStore((s) => s.state);
  const singularity = useAetherStore((s) => s.singularity);
  const messages = useAetherStore((s) => s.messages);
  const isThinking = useAetherStore((s) => s.isThinking);

  const sendMessage = useAetherStore((s) => s.sendMessage);
  const activateWormhole = useAetherStore((s) => s.activateWormhole);
  const uploadInvoice = useAetherStore((s) => s.uploadInvoice);
  const saveUserProfile = useAetherStore((s) => s.saveUserProfile);

  // Profile Modal State
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profCompany, setProfCompany] = useState("");
  const [profOwner, setProfOwner] = useState("");
  const [profType, setProfType] = useState("Trading & Services");
  const [profCity, setProfCity] = useState("Mumbai, Maharashtra");
  const [profGstin, setProfGstin] = useState("27AAACU1234M1Z5");
  const [profCash, setProfCash] = useState(350000);
  const [profVault, setProfVault] = useState(35000);
  const [profBurn, setProfBurn] = useState(80000);

  // Mobile view toggle (between Chat and Tools on small screens)
  const [mobileTab, setMobileTab] = useState<"chat" | "tools">("chat");
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

  // Sync profile fields from state when state updates
  useEffect(() => {
    if (state?.business) {
      setProfCompany(state.business.name || "");
      setProfOwner((state.business as any).owner_name || "Business Owner");
      setProfType(state.business.archetype || "Trading & Services");
      setProfCity(state.business.city || "Mumbai, Maharashtra");
      setProfGstin(state.business.gstin || "27AAACU1234M1Z5");
      setProfCash(state.physics_state?.bank_cash || 350000);
      setProfVault(state.physics_state?.tax_vault_balance || 35000);
    }
  }, [state]);

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
      // Graceful fallback
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
      const sales = (state?.physics_state?.bank_cash || 300000) * 6;
      const data = await fetchProfitModelApi(sales, 70.0, profBurn, 25000);
      setProfitData(data);
    } catch {
      // Graceful fallback
    }
  }, [state, profBurn]);

  const loadEmi = useCallback(async () => {
    try {
      const data = await fetchEmiApi(loanPrincipal, loanRate, loanTenure);
      setEmiResult(data);
    } catch {
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

  useEffect(() => {
    loadForecast();
    loadGstPlan();
    loadLedger();
    loadProfitModel();
    loadEmi();
    loadGstCalc();
  }, [state, loadForecast, loadGstPlan, loadLedger, loadProfitModel, loadEmi, loadGstCalc]);

  useEffect(() => {
    const t = setTimeout(() => {
      loadForecast();
    }, 250);
    return () => clearTimeout(t);
  }, [delayDays, discountPct, expenseCutPct, plannedSpend, loadForecast]);

  useEffect(() => {
    loadEmi();
  }, [loanPrincipal, loanRate, loanTenure, loadEmi]);

  useEffect(() => {
    loadGstCalc();
  }, [calcAmount, calcRate, calcMode, loadGstCalc]);

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
    loadForecast();
    loadGstPlan();
    loadLedger();
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profCompany.trim()) return;
    playUiSound("click");
    await saveUserProfile({
      company_name: profCompany.trim(),
      owner_name: profOwner.trim() || "Business Owner",
      business_type: profType.trim() || "Trading & Services",
      city: profCity.trim() || "Mumbai, Maharashtra",
      gstin: profGstin.trim() || "27AAACU1234M1Z5",
      bank_cash: Number(profCash) || 300000,
      tax_vault: Number(profVault) || 30000,
      monthly_burn: Number(profBurn) || 80000,
    });
    setShowProfileModal(false);
    loadForecast();
    loadGstPlan();
    loadLedger();
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

  const handleResetBusiness = async () => {
    if (!confirm("Are you sure you want to reset to a clean slate? This will clear all sample transactions.")) return;
    try {
      const res = await fetch("/api/profile/reset", { method: "POST" });
      if (res.ok) {
        init();
        loadForecast();
        loadGstPlan();
        loadLedger();
        loadProfitModel();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDraftId(id);
    setTimeout(() => setCopiedDraftId(null), 2500);
  };

  // Financial aggregates
  const totalReceivables = state?.invoices?.reduce((sum, i) => sum + (i.unpaid_cash || 0), 0) || 0;
  const totalPayables = state?.obligations?.reduce((sum, o) => sum + (o.amount || 0), 0) || 0;
  const bankCash = state?.physics_state?.bank_cash || 0;
  const taxDue = state?.gst_snapshot?.net_gst_cash_payable || 0;
  const runwayDays = state?.physics_state?.estimated_runway_days || 0;

  const hasDeficit = singularity && singularity.severity !== "LOW" && singularity.days_to_event_horizon <= 10;
  const deficitAmount = singularity?.tax_vault_deficit || 0;

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-brand-500/30">
      
      {/* 1. TOP COMMAND BAR */}
      <header className="h-16 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between shrink-0 z-30">
        
        {/* Brand & User Company Profile */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-500 to-accentcyan flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-brand-500/20">
            AP
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-base tracking-tight">
                {state?.business?.name || "My Business Enterprise"}
              </span>
              <button
                onClick={() => setShowProfileModal(true)}
                className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 flex items-center gap-1 transition"
                title="Edit Company Profile"
              >
                <Edit3 className="w-3 h-3 text-accentcyan" />
                <span>Edit Profile</span>
              </button>
              <button
                onClick={handleResetBusiness}
                className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 hover:bg-rose-950/40 text-slate-400 hover:text-rose-300 border border-slate-800 hover:border-rose-800/40 flex items-center gap-1 transition"
                title="Reset to Clean Slate"
              >
                <RefreshCw className="w-3 h-3" />
                <span className="hidden sm:inline">Reset</span>
              </button>
            </div>
            <span className="text-[11px] text-slate-400 font-mono hidden sm:block">
              {(state?.business as any)?.owner_name || "Owner"} • {state?.business?.city || "India"} • GST: {state?.business?.gstin || "Active"}
            </span>
          </div>
        </div>

        {/* Live Business KPI Badges */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-3 text-xs font-mono">
            <div className="px-3 py-1 rounded-lg bg-black/40 border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">Bank Cash</span>
              <span className="text-white font-bold">{fmtCompact(bankCash)}</span>
            </div>
            <div className="px-3 py-1 rounded-lg bg-black/40 border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">Receivables</span>
              <span className="text-accentcyan font-bold">{fmtCompact(totalReceivables)}</span>
            </div>
            <div className="px-3 py-1 rounded-lg bg-black/40 border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">Payables</span>
              <span className="text-purple-400 font-bold">{fmtCompact(totalPayables)}</span>
            </div>
            <div className="px-3 py-1 rounded-lg bg-black/40 border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">GST Due (20th)</span>
              <span className="text-warningamber font-bold">{fmtCompact(taxDue)}</span>
            </div>
            <div className="px-3 py-1 rounded-lg bg-black/40 border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">Runway</span>
              <span className="text-brand-400 font-bold">{runwayDays.toFixed(1)}d</span>
            </div>
          </div>

          {/* Mobile Screen Toggle (Chat vs Tools) */}
          <div className="lg:hidden flex items-center bg-black/60 rounded-xl p-0.5 border border-slate-800 text-xs">
            <button
              onClick={() => {
                playUiSound("click");
                setMobileTab("chat");
              }}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                mobileTab === "chat" ? "bg-brand-600 text-white font-semibold" : "text-slate-400"
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => {
                playUiSound("click");
                setMobileTab("tools");
              }}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                mobileTab === "tools" ? "bg-brand-600 text-white font-semibold" : "text-slate-400"
              }`}
            >
              Tools
            </button>
          </div>

          {/* User Badge & Logout */}
          <div className="flex items-center gap-2 pl-2 sm:border-l border-slate-800">
            <a
              href={MARKET_APP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1.5 rounded-xl bg-slate-900 hover:bg-cyan-950/40 text-slate-300 hover:text-accentcyan text-xs font-medium border border-slate-800 hover:border-cyan-800/40 transition flex items-center gap-1.5"
              title="Open Market Intelligence"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Market Intelligence</span>
            </a>
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-xl bg-slate-800/80 border border-slate-700/80 text-xs">
              <div className="w-5 h-5 rounded-full bg-brand-500/20 text-brand-400 font-bold flex items-center justify-center text-[10px]">
                {(user?.name || (state?.business as any)?.owner_name || "BO").slice(0, 2).toUpperCase()}
              </div>
              <span className="text-slate-200 font-medium">
                {user?.name || (state?.business as any)?.owner_name || "Business Owner"}
              </span>
            </div>
            {onLogout && (
              <button
                onClick={onLogout}
                className="px-2.5 py-1.5 rounded-xl bg-slate-900 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 text-xs font-medium border border-slate-800 hover:border-rose-800/40 transition flex items-center gap-1.5"
                title="Sign Out of Account"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Sign Out</span>
              </button>
            )}
          </div>
        </div>

      </header>

      {/* 2. PROMINENT GST ALERT STRIP (Only if tax deficit exists) */}
      {hasDeficit && deficitAmount > 0 && (
        <div className="bg-gradient-to-r from-dangerrose/20 via-warningamber/15 to-transparent border-b border-dangerrose/30 px-4 sm:px-6 py-2 flex items-center justify-between text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-dangerrose animate-ping" />
            <AlertTriangle className="w-4 h-4 text-dangerrose shrink-0" />
            <span className="text-slate-200">
              <strong className="text-white font-semibold">GST Alert:</strong>{" "}
              {fmtInr(deficitAmount)} cash shortfall due on 20 Nov. Unpaid customer bills hold GST liability that must be paid in cash.
            </span>
          </div>
          <button
            onClick={handleLiquidityBridge}
            className="px-3 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition shrink-0"
          >
            Bridge Cash
          </button>
        </div>
      )}

      {/* 3. MAIN WORKSPACE: DUAL-PANE (LEFT: AI CHAT ASSISTANT, RIGHT: ADVANCED FINANCE TOOLS) */}
      <div className="flex-1 flex overflow-hidden h-[calc(100vh-64px)] relative">
        
        {/* ============================================================== */}
        {/* PRIMARY CHAT EXPERIENCE: USER & AI FINANCE ASSISTANT (PLAIN)   */}
        {/* ============================================================== */}
        <main className={`w-full lg:w-[48%] xl:w-[45%] flex flex-col bg-slate-950/80 border-r border-slate-800/80 h-full overflow-hidden shrink-0 ${
          mobileTab === "tools" ? "hidden lg:flex" : "flex"
        }`}>
          
          {/* Top Quick Actions Bar: User enters information directly into chat */}
          <div className="p-3 border-b border-slate-800/80 bg-slate-900/60 flex items-center gap-2 overflow-x-auto no-scrollbar shrink-0 text-xs">
            <button
              onClick={() => setInputText("Add invoice for Reliance Infra ₹2,50,000 with 18% GST due in 30 days")}
              className="px-3 py-1.5 rounded-lg bg-brand-500/15 hover:bg-brand-500/25 text-brand-300 border border-brand-500/30 whitespace-nowrap transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Invoice</span>
            </button>
            <button
              onClick={() => setInputText("Add expense monthly office rent ₹35,000 due in 10 days")}
              className="px-3 py-1.5 rounded-lg bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 whitespace-nowrap transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Expense</span>
            </button>
            <button
              onClick={() => setInputText("Received payment of ₹1,50,000 from Reliance")}
              className="px-3 py-1.5 rounded-lg bg-accentcyan/15 hover:bg-accentcyan/25 text-accentcyan border border-accentcyan/30 whitespace-nowrap transition flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Record Payment</span>
            </button>
            <button
              onClick={() => setInputText("My bank balance is ₹5,00,000")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition"
            >
              Update Bank Balance
            </button>
            <button
              onClick={() => handleSendMessage("How is my money?")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition"
            >
              How is my money?
            </button>
            <button
              onClick={() => handleSendMessage("Who owes me money?")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition"
            >
              Who owes me?
            </button>
            <button
              onClick={() => handleSendMessage("What GST do I owe this month?")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition"
            >
              What GST do I owe?
            </button>
            <button
              onClick={() => setInputText("Can I afford to buy new equipment for ₹2,00,000?")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition"
            >
              Can I afford spend?
            </button>
          </div>

          {/* Chat Message Scroll */}
          <div
            ref={chatEndRef}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 scroll-smooth"
          >
            {/* Welcome banner if no messages */}
            {messages.length === 0 && (
              <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-3">
                <div className="flex items-center gap-2 text-brand-400 font-semibold text-sm">
                  <Sparkles className="w-5 h-5" />
                  <span>Welcome to your Dedicated Finance AI Assistant</span>
                </div>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  I track all money movements for <strong>{state?.business?.name || "your company"}</strong>. Tell me in plain words whenever you:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 text-slate-300">
                    <strong className="text-brand-400 block mb-0.5">1. Issue an Invoice:</strong>
                    &quot;Add invoice for Tata ₹2,50,000 18% GST due in 30 days&quot;
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 text-slate-300">
                    <strong className="text-purple-400 block mb-0.5">2. Add an Expense / EMI:</strong>
                    &quot;Add monthly rent ₹35,000 due in 10 days&quot;
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 text-slate-300">
                    <strong className="text-accentcyan block mb-0.5">3. Record Payment Received:</strong>
                    &quot;Client Tata paid ₹1,50,000 today&quot;
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 text-slate-300">
                    <strong className="text-warningamber block mb-0.5">4. Ask Any Financial Question:</strong>
                    &quot;What is my cash runway?&quot; or &quot;Who owes me?&quot;
                  </div>
                </div>
              </div>
            )}

            {/* Message Stream */}
            {messages.map((m) => {
              const isAi = m.sender === "ai";
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isAi ? "items-start" : "items-end"} gap-1`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 px-1 font-mono">
                    <span>{isAi ? "AetherPravah AI" : (state?.business as any)?.owner_name || "You"}</span>
                    <span>•</span>
                    <span>{m.timestamp}</span>
                  </div>

                  <div
                    className={`max-w-[88%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                      isAi
                        ? "bg-slate-900/95 text-slate-200 border border-slate-800/90 shadow-lg"
                        : "bg-brand-600 text-white font-medium shadow-md shadow-brand-600/25"
                    }`}
                  >
                    {/* Main text content */}
                    <div className="whitespace-pre-line space-y-2">
                      {m.text}
                    </div>

                    {/* Rich Structured Cards */}
                    {isAi && m.cards && m.cards.length > 0 && (
                      <div className="mt-3 space-y-2 pt-2 border-t border-slate-800">
                        {m.cards.map((card, cIdx) => {
                          if (card.type === "kpis" && card.items) {
                            return (
                              <div key={cIdx} className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-2">
                                {card.items.map((it, iIdx) => (
                                  <div
                                    key={iIdx}
                                    className="p-2 rounded-lg bg-black/50 border border-slate-800 flex flex-col"
                                  >
                                    <span className="text-[10px] text-slate-400 uppercase tracking-wide">
                                      {it.label}
                                    </span>
                                    <span
                                      className={`text-xs sm:text-sm font-bold font-mono mt-0.5 ${
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
                                className={`p-3.5 rounded-xl border my-2 ${
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
                                  <div className="bg-slate-800/70 px-3 py-1.5 text-xs font-semibold text-slate-200">
                                    {card.title}
                                  </div>
                                )}
                                <table className="w-full text-left text-xs font-mono">
                                  <thead className="bg-black/60 text-slate-400 border-b border-slate-800">
                                    <tr>
                                      {card.headers.map((h, hIdx) => (
                                        <th key={hIdx} className="p-2.5 font-medium">
                                          {h}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-800/60">
                                    {card.rows.map((row, rIdx) => (
                                      <tr key={rIdx} className="hover:bg-slate-800/30">
                                        {row.map((cell, cellIdx) => (
                                          <td key={cellIdx} className="p-2.5 text-slate-300">
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
                                className="p-3.5 rounded-xl bg-slate-950/90 border border-slate-800 my-2 space-y-2 text-xs"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-accentcyan flex items-center gap-1.5">
                                    <FileText className="w-4 h-4" />
                                    <span>Payment Reminder for {card.customer || "Client"}</span>
                                  </span>
                                  {card.amount && (
                                    <span className="font-mono font-bold text-white">
                                      {card.amount}
                                    </span>
                                  )}
                                </div>
                                <div className="p-3 rounded-lg bg-black/70 font-mono text-xs text-slate-300 whitespace-pre-wrap border border-slate-800/60 leading-relaxed">
                                  {draftMsg}
                                </div>
                                <div className="flex items-center justify-end gap-2 pt-1">
                                  <button
                                    onClick={() => copyToClipboard(`draft-${cIdx}`, draftMsg)}
                                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 flex items-center gap-1.5 transition"
                                  >
                                    {copiedDraftId === `draft-${cIdx}` ? (
                                      <>
                                        <Check className="w-3.5 h-3.5 text-brand-400" />
                                        <span>Copied to Clipboard!</span>
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="w-3.5 h-3.5" />
                                        <span>Copy WhatsApp / Email</span>
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

                    {/* Recommendations */}
                    {isAi && m.recommendations && m.recommendations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/60 space-y-1.5 text-xs">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-brand-400 block">
                          Next Recommended Steps:
                        </span>
                        {m.recommendations.map((rec, rIdx) => (
                          <div key={rIdx} className="flex items-start gap-1.5 text-slate-300 text-xs">
                            <CheckCircle2 className="w-3.5 h-3.5 text-brand-400 shrink-0 mt-0.5" />
                            <span>{rec}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Follow-up suggestion chips */}
                    {isAi && m.suggestions && m.suggestions.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-slate-800/60 flex flex-wrap gap-1.5">
                        {m.suggestions.map((sug, sIdx) => (
                          <button
                            key={sIdx}
                            onClick={() => handleSendMessage(sug)}
                            className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition"
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
              <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-400 w-fit">
                <div className="w-4 h-4 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
                <span>AI analyzing cash flow & updating financial twin...</span>
              </div>
            )}
          </div>

          {/* Bottom Chat Command Bar */}
          <div className="p-3 sm:p-4 border-t border-slate-800/80 bg-slate-950/95 shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2 bg-slate-900/90 rounded-2xl p-2 border border-slate-800 focus-within:border-brand-500 transition shadow-inner"
            >
              {/* Camera OCR */}
              <label className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 cursor-pointer transition">
                <Camera className="w-4 h-4" />
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </label>

              {/* Voice simulation */}
              <button
                type="button"
                onClick={handleVoiceSimulation}
                className={`p-2 rounded-xl transition ${
                  isVoiceRecording
                    ? "bg-dangerrose text-white animate-pulse"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
                title="Voice Note"
              >
                <Mic className="w-4 h-4" />
              </button>

              {/* Text Input */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Tell me about an invoice, expense, payment, or ask any financial question..."
                className="flex-1 bg-transparent border-none text-xs sm:text-sm text-white focus:outline-none placeholder:text-slate-500"
              />

              {/* Send Button */}
              <button
                type="submit"
                disabled={!inputText.trim()}
                className={`px-4 py-2 rounded-xl font-medium text-xs sm:text-sm transition flex items-center gap-1.5 ${
                  inputText.trim()
                    ? "bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-600/30"
                    : "bg-slate-800 text-slate-500 cursor-not-allowed"
                }`}
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </main>

        {/* ============================================================== */}
        {/* RIGHT PANE: FOUR ADVANCED FINANCIAL FEATURE TABS               */}
        {/* ============================================================== */}
        <aside className={`flex-1 flex flex-col bg-slate-900/40 h-full overflow-hidden ${
          mobileTab === "chat" ? "hidden lg:flex" : "flex"
        }`}>
          {/* Tool Navigation Tabs Bar */}
          <div className="h-12 px-4 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-1.5 text-xs overflow-x-auto no-scrollbar">
              <button
                onClick={() => setActiveTab("forecast")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "forecast" ? "bg-slate-800 text-white font-semibold border border-slate-700" : "text-slate-400 hover:text-white"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5 text-brand-400" />
                <span>Cash Flow & What-If</span>
              </button>
              <button
                onClick={() => setActiveTab("gst")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "gst" ? "bg-slate-800 text-white font-semibold border border-slate-700" : "text-slate-400 hover:text-white"
                }`}
              >
                <Building2 className="w-3.5 h-3.5 text-dangerrose" />
                <span>GST & Tax</span>
              </button>
              <button
                onClick={() => setActiveTab("ledger")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "ledger" ? "bg-slate-800 text-white font-semibold border border-slate-700" : "text-slate-400 hover:text-white"
                }`}
              >
                <Users className="w-3.5 h-3.5 text-accentcyan" />
                <span>Who Owes Me / Who I Owe</span>
              </button>
              <button
                onClick={() => setActiveTab("profit")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "profit" ? "bg-slate-800 text-white font-semibold border border-slate-700" : "text-slate-400 hover:text-white"
                }`}
              >
                <Calculator className="w-3.5 h-3.5 text-warningamber" />
                <span>Profit & EMI</span>
              </button>
            </div>
            <div className="text-[11px] text-slate-400 font-mono hidden xl:block">
              Sim Date: <span className="text-white font-semibold">16 Nov 2026</span>
            </div>
          </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {activeTab === "forecast" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block">Lowest Dip</span>
                      <span className="font-mono font-bold text-base text-dangerrose">
                        {fmtInr(forecastData?.summary?.lowest_balance ?? -1097915)}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-black/40 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block">Runway</span>
                      <span className="font-mono font-bold text-base text-brand-400">
                        {forecastData?.summary?.estimated_runway_days ?? 4} Days
                      </span>
                    </div>
                  </div>

                  {/* 45-day Trajectory */}
                  <div className="p-3 rounded-xl bg-black/40 border border-slate-800 space-y-2">
                    <span className="font-semibold text-slate-200 block">45-Day Cash Progression</span>
                    <div className="h-28 flex items-end gap-1 pt-2">
                      {forecastData?.daily?.slice(0, 30).map((d: ForecastDayItem, idx: number) => {
                        const hPct = Math.min(100, Math.max(15, (Math.abs(d.balance) / 500000) * 100));
                        return (
                          <div
                            key={idx}
                            style={{ height: `${hPct}%` }}
                            className={`flex-1 rounded-t ${
                              d.balance < 0 ? "bg-dangerrose" : "bg-brand-500"
                            }`}
                            title={`${d.date}: ${fmtInr(d.balance)}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "gst" && (
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-dangerrose/10 border border-dangerrose/30 space-y-1">
                    <span className="font-bold text-dangerrose block">GSTR-3B Due in 4 Days (20 Nov)</span>
                    <span className="text-slate-300">
                      Net Tax Payable: <strong>{fmtInr(gstPlanData?.net_payable ?? 284915)}</strong>
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-black/40 border border-slate-800 space-y-2">
                    <span className="font-semibold text-slate-200 block">GST Calculator</span>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        value={calcAmount}
                        onChange={(e) => setCalcAmount(Number(e.target.value))}
                        className="bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-white font-mono"
                      />
                      <select
                        value={calcRate}
                        onChange={(e) => setCalcRate(Number(e.target.value))}
                        className="bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-white font-mono"
                      >
                        <option value={18}>18% GST</option>
                        <option value={12}>12% GST</option>
                        <option value={5}>5% GST</option>
                        <option value={28}>28% GST</option>
                      </select>
                    </div>
                    {calcResult && (
                      <div className="grid grid-cols-2 gap-2 pt-2 text-[11px] font-mono">
                        <div>Base: {fmtInr(calcResult.base)}</div>
                        <div className="text-accentcyan">Tax: {fmtInr(calcResult.gst)}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === "ledger" && (
                <div className="space-y-3">
                  <div className="flex gap-2 border-b border-slate-800 pb-2">
                    <button
                      onClick={() => setLedgerSubTab("debtors")}
                      className={`px-3 py-1 rounded text-xs ${
                        ledgerSubTab === "debtors" ? "bg-brand-600 text-white" : "text-slate-400"
                      }`}
                    >
                      Debtors
                    </button>
                    <button
                      onClick={() => setLedgerSubTab("creditors")}
                      className={`px-3 py-1 rounded text-xs ${
                        ledgerSubTab === "creditors" ? "bg-brand-600 text-white" : "text-slate-400"
                      }`}
                    >
                      Creditors
                    </button>
                  </div>
                  {ledgerSubTab === "debtors" ? (
                    <div className="space-y-2">
                      {ledgerData?.debtors?.invoices?.map((inv: LedgerDebtorItem) => (
                        <div key={inv.id} className="p-2.5 rounded bg-black/40 border border-slate-800 space-y-1">
                          <div className="flex justify-between font-semibold">
                            <span>{inv.customer_name}</span>
                            <span className="font-mono">{fmtInr(inv.amount)}</span>
                          </div>
                          <div className="text-[10px] text-slate-400">Due: {inv.due_label}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {ledgerData?.creditors?.liabilities?.map((lib: LedgerCreditorItem) => (
                        <div key={lib.id} className="p-2.5 rounded bg-black/40 border border-slate-800 space-y-1">
                          <div className="flex justify-between font-semibold">
                            <span>{lib.name}</span>
                            <span className="font-mono">{fmtInr(lib.amount)}</span>
                          </div>
                          <div className="text-[10px] text-slate-400">Due: {lib.due_label}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "profit" && (
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-black/40 border border-slate-800 space-y-2">
                    <span className="font-semibold text-slate-200 block">Loan EMI Calculator</span>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span>Loan Amount</span>
                        <span className="font-mono">{fmtInr(loanPrincipal)}</span>
                      </div>
                      <input
                        type="range"
                        min="100000"
                        max="5000000"
                        step="50000"
                        value={loanPrincipal}
                        onChange={(e) => setLoanPrincipal(Number(e.target.value))}
                        className="w-full accent-purple-400"
                      />
                    </div>
                    {emiResult && (
                      <div className="p-2.5 rounded bg-purple-500/10 border border-purple-500/30 font-mono">
                        <span className="text-[10px] text-purple-300 block">Monthly EMI</span>
                        <span className="text-base font-bold text-white">{fmtInr(emiResult.monthly_emi)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

          </aside>

      </div>

      {/* 4. COMPANY PROFILE CREATION & EDIT MODAL */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl animate-in zoom-in-95 duration-150">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-brand-400" />
                <h3 className="font-bold text-base text-white">Create / Edit Business Profile</h3>
              </div>
              <button
                onClick={() => setShowProfileModal(false)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Company / Business Name</label>
                  <input
                    type="text"
                    required
                    value={profCompany}
                    onChange={(e) => setProfCompany(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Owner / Founder Name</label>
                  <input
                    type="text"
                    value={profOwner}
                    onChange={(e) => setProfOwner(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Business Type / Industry</label>
                  <input
                    type="text"
                    value={profType}
                    onChange={(e) => setProfType(e.target.value)}
                    placeholder="e.g. Trading, Manufacturing, IT Services"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">City / State</label>
                  <input
                    type="text"
                    value={profCity}
                    onChange={(e) => setProfCity(e.target.value)}
                    placeholder="e.g. Mumbai, Maharashtra"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-medium block">GSTIN Number (Optional)</label>
                <input
                  type="text"
                  value={profGstin}
                  onChange={(e) => setProfGstin(e.target.value)}
                  placeholder="e.g. 27AAACU1234M1Z5"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono"
                />
              </div>

              <div className="grid grid-cols-3 gap-3 pt-1">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Bank Cash (₹)</label>
                  <input
                    type="number"
                    value={profCash}
                    onChange={(e) => setProfCash(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Tax Vault (₹)</label>
                  <input
                    type="number"
                    value={profVault}
                    onChange={(e) => setProfVault(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Monthly Burn (₹)</label>
                  <input
                    type="number"
                    value={profBurn}
                    onChange={(e) => setProfBurn(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold shadow-lg shadow-brand-600/30"
                >
                  Save Profile & Start Twin
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}
