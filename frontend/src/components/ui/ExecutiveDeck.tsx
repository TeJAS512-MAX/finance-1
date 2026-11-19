"use client";

import React, { useState, useEffect, useRef } from "react";
import confetti from "canvas-confetti";
import {
  Send,
  Camera,
  Activity,
  Sparkles,
  TrendingUp,
  Shield,
  Scissors,
  Cpu,
  Clock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  PlusCircle,
  Sliders,
} from "lucide-react";
import { useAetherStore } from "@/lib/store";
import { playUiSound } from "./AudioController";
import CausalGraphCanvas from "../3d/CausalGraph3D";
import FinancialOrganismCanvas from "../3d/FinancialOrganism3D";
import WormholePortalCanvas from "../3d/WormholePortal3D";
import GenomeDoubleHelixCanvas from "../3d/GenomeDoubleHelix3D";

export default function ExecutiveDeck() {
  const isLoaded = useAetherStore((s) => s.isLoaded);
  const isLoading = useAetherStore((s) => s.isLoading);
  const error = useAetherStore((s) => s.error);
  const init = useAetherStore((s) => s.init);

  const businessKey = useAetherStore((s) => s.businessKey);
  const state = useAetherStore((s) => s.state);
  const singularity = useAetherStore((s) => s.singularity);
  const candidates = useAetherStore((s) => s.candidates);
  const selectedCandidateIdx = useAetherStore((s) => s.selectedCandidateIdx);

  const nodes = useAetherStore((s) => s.nodes);
  const selectedNodeId = useAetherStore((s) => s.selectedNodeId);
  const selectNode = useAetherStore((s) => s.selectNode);

  const messages = useAetherStore((s) => s.messages);
  const isThinking = useAetherStore((s) => s.isThinking);

  const switchBusiness = useAetherStore((s) => s.switchBusiness);
  const sendMessage = useAetherStore((s) => s.sendMessage);
  const activateWormhole = useAetherStore((s) => s.activateWormhole);
  const simulateDelay = useAetherStore((s) => s.simulateDelay);
  const uploadInvoice = useAetherStore((s) => s.uploadInvoice);

  // Local Deck State
  const [activeTab, setActiveTab] = useState<"radar" | "organism" | "wormhole" | "trajectory">("radar");
  const [inputQuery, setInputQuery] = useState("");
  const [openDetailsId, setOpenDetailsId] = useState<string | null>(null);
  const [isWormholeRunning, setIsWormholeRunning] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [invCustomer, setInvCustomer] = useState("Reliance Infra Projects Ltd");
  const [invAmount, setInvAmount] = useState(250000);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initialize store on mount
  useEffect(() => {
    init();
  }, [init]);

  // Auto-scroll chat
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollTop = chatEndRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  // Execute Wormhole with celebration
  const handleExecuteWormhole = async () => {
    playUiSound("wormhole");
    setIsWormholeRunning(true);
    confetti({
      particleCount: 140,
      spread: 80,
      origin: { y: 0.6 },
      colors: ["#10b981", "#22d3ee", "#f59e0b"],
    });

    try {
      await activateWormhole();
    } finally {
      setIsWormholeRunning(false);
    }
  };

  // Submit invoice from quick form
  const handleCreateInvoice = async (e: React.FormEvent) => {
    e.preventDefault();
    setShowInvoiceModal(false);
    playUiSound("click");
    await sendMessage(`Create invoice for ${invCustomer} with amount ${invAmount} rupees`);
  };

  // Upload file
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadInvoice(file);
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const activeWormhole = candidates[selectedCandidateIdx] || candidates[0];
  const isWormholeExecuted = state?.active_wormholes?.some((w) => w.status === "EXECUTED");

  if (!isLoaded && isLoading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex flex-col items-center justify-center space-y-4">
        <div className="w-12 h-12 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
        <p className="text-sm font-mono text-slate-400">Initializing Central Nervous System & Causal Graph...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-brand-500/30">
      
      {/* TOP COMMAND DECK BAR */}
      <header className="h-16 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0 z-30">
        
        {/* Brand & Conservation Indicator */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-500 to-accentcyan flex items-center justify-center font-bold text-white text-xs shadow-lg shadow-brand-500/20">
              AP
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight block leading-none">
                AetherPravah
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Causal Financial Organism</span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            <span>Conserved: ₹{state ? (state.physics_state.total_rupees_conserved / 100000).toFixed(2) : "0.00"}L</span>
          </div>
        </div>

        {/* Company Archetype Switcher */}
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
            <span className="hidden sm:inline">Bharat Steel</span>
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
            <span className="hidden sm:inline">VastraKala</span>
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
            <span className="hidden sm:inline">NexusPulse</span>
          </button>
        </div>

        {/* Live Executive KPI Strip */}
        <div className="flex items-center gap-3">
          {state && (
            <div className="hidden lg:flex items-center gap-4 text-xs font-mono pr-2">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Bank Cash</span>
                <span className="text-white font-bold">
                  ₹{(state.physics_state.bank_cash / 100000).toFixed(2)}L
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Tax Vault</span>
                <span className="text-accentcyan font-bold">
                  ₹{(state.physics_state.tax_vault_balance / 1000).toFixed(0)}k
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Runway</span>
                <span className="text-brand-400 font-bold">
                  {state.physics_state.estimated_runway_days.toFixed(1)}d
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">GST Cut-off</span>
                <span className={singularity?.severity === "LOW" ? "text-brand-400 font-bold" : "text-dangerrose font-bold"}>
                  {singularity?.days_to_event_horizon}d left
                </span>
              </div>
            </div>
          )}

          {/* Health Score Pill */}
          {state && (
            <div
              className={`px-3.5 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono ${
                state.genome.overall_score >= 70
                  ? "bg-brand-500/10 border-brand-500/30 text-brand-400"
                  : state.genome.overall_score >= 50
                  ? "bg-warningamber/10 border-warningamber/30 text-warningamber"
                  : "bg-dangerrose/10 border-dangerrose/30 text-dangerrose"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
              <span className="font-bold">{state.genome.overall_score}/100</span>
            </div>
          )}
        </div>

      </header>

      {/* ERROR BANNER IF ANY */}
      {error && (
        <div className="bg-dangerrose/15 border-b border-dangerrose/30 px-6 py-2 text-xs text-dangerrose flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => init()} className="underline hover:text-white font-medium">
            Retry Connection
          </button>
        </div>
      )}

      {/* MAIN TWO-COLUMN STUDIO */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden">
        
        {/* LEFT COLUMN: 3D Command Deck (60% on desktop) */}
        <div className="lg:col-span-7 flex flex-col border-r border-slate-800/80 bg-slate-950/40 relative h-[calc(100vh-64px)] overflow-hidden">
          
          {/* Studio Mode Selector Pills */}
          <div className="h-12 px-6 border-b border-slate-800/80 bg-slate-950/60 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-1.5 text-xs">
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("radar");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "radar"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Activity className="w-3.5 h-3.5 text-accentcyan" />
                <span>3D Spacetime Radar</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("organism");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "organism"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                <span>Living Organism</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("wormhole");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "wormhole"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Sliders className="w-3.5 h-3.5 text-warningamber" />
                <span>Wormhole Forger</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("trajectory");
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === "trajectory"
                    ? "bg-slate-800 text-white font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5 text-brand-400" />
                <span>What-If Trajectory</span>
              </button>
            </div>

            <div className="text-[11px] text-slate-400 font-mono hidden sm:block">
              {nodes.length} Causal Nodes • Live Three.js Engine
            </div>
          </div>

          {/* 3D Scene Container */}
          <div className="flex-1 relative overflow-hidden bg-black/60">
            {activeTab === "radar" && <CausalGraphCanvas />}
            {activeTab === "organism" && (
              <FinancialOrganismCanvas healthScore={state?.genome.overall_score || 38} interactive={true} />
            )}
            {activeTab === "wormhole" && (
              <div className="w-full h-full p-6 overflow-y-auto space-y-4">
                <div className="h-52 w-full rounded-2xl overflow-hidden border border-accentcyan/30 relative bg-black/60">
                  <WormholePortalCanvas isActivating={isWormholeRunning} />
                </div>
                {activeWormhole && (
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-accentcyan/20 text-accentcyan">
                          {isWormholeExecuted ? "EXECUTED" : activeWormhole.status}
                        </span>
                        <h3 className="text-base font-bold text-white mt-1">{activeWormhole.title}</h3>
                        <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                          {activeWormhole.explanation_narrative}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-[11px] text-slate-400 uppercase block">Liberates</span>
                        <span className="text-xl font-bold mono text-accentcyan">
                          ₹{(activeWormhole.gross_liquidity_created / 100000).toFixed(2)}L
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t border-slate-800">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Vector Steps:
                      </span>
                      {activeWormhole.steps.map((s) => (
                        <div key={s.step_number} className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-semibold text-white block">{s.action_type.replace(/_/g, " ")}</span>
                            <span className="text-slate-400 text-[11px]">{s.causal_mechanism}</span>
                          </div>
                          <span className="font-mono font-bold text-brand-400 ml-3 shrink-0">
                            +₹{s.amount_unlocked.toLocaleString("en-IN")}
                          </span>
                        </div>
                      ))}
                    </div>

                    {!isWormholeExecuted ? (
                      <button
                        onClick={handleExecuteWormhole}
                        className="w-full py-3 rounded-xl bg-gradient-to-r from-accentcyan to-brand-600 hover:from-accentcyan/90 hover:to-brand-500 text-white font-semibold text-sm transition shadow-lg shadow-accentcyan/20 flex items-center justify-center gap-2"
                      >
                        <Sparkles className="w-4 h-4" />
                        <span>Authorize & Execute Wormhole</span>
                      </button>
                    ) : (
                      <div className="w-full py-2.5 rounded-xl bg-brand-500/20 text-brand-400 font-bold text-xs flex items-center justify-center gap-2">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Singularity Neutralized • Tax Fully Secured</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            {activeTab === "trajectory" && (
              <div className="w-full h-full p-6 overflow-y-auto space-y-4">
                <div className="h-56 w-full rounded-2xl overflow-hidden border border-slate-800 bg-black/60 relative">
                  <GenomeDoubleHelixCanvas score={state?.genome.overall_score || 38} />
                </div>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-4 rounded-xl bg-dangerrose/10 border border-dangerrose/30">
                    <span className="font-semibold text-dangerrose block mb-1">Path A: Status Quo (Inaction)</span>
                    <p className="text-slate-300 leading-relaxed text-[11px]">
                      Cash plunges negative on 20th Nov due to statutory tax debits preceding receivables collection. Bank notices enforced under CGST Section 79.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-brand-500/10 border border-brand-500/30">
                    <span className="font-semibold text-brand-400 block mb-1">Path B: do(Wormhole)</span>
                    <p className="text-slate-300 leading-relaxed text-[11px]">
                      Cash stays buoyant at +₹13.06 Lakhs. GST accrual fully satisfied by Tax Vault. Operating runway safely extends past 40 days.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Floating Node Inspector Card (appears when a node is selected in 3D radar) */}
            {activeTab === "radar" && selectedNode && (
              <div className="absolute top-4 left-4 p-4 rounded-2xl bg-slate-950/90 border border-slate-700/80 backdrop-blur-md shadow-2xl max-w-xs space-y-2 text-xs pointer-events-auto">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <span className="font-bold text-white text-sm">{selectedNode.label}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                    {selectedNode.type}
                  </span>
                </div>
                <div className="space-y-1 text-slate-300 text-[11px]">
                  <div>
                    <span className="text-slate-400">Value: </span>
                    <span className="font-mono font-bold text-white">{selectedNode.value}</span>
                  </div>
                  {Boolean(selectedNode.properties?.typical_delay) && (
                    <div>
                      <span className="text-slate-400">Cycle Latency: </span>
                      <span className="text-warningamber font-mono font-semibold">
                        +{String(selectedNode.properties.typical_delay)} days
                      </span>
                    </div>
                  )}
                  {Boolean(selectedNode.properties?.gst) && (
                    <div>
                      <span className="text-slate-400">Accrued GST: </span>
                      <span className="text-dangerrose font-mono font-semibold">
                        ₹{Number(selectedNode.properties.gst).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                </div>
                <div className="pt-1.5 flex gap-2">
                  <button
                    onClick={() => sendMessage(`Tell me more about ${selectedNode.label}`)}
                    className="flex-1 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition"
                  >
                    Inspect in Chat
                  </button>
                  <button
                    onClick={() => selectNode(null)}
                    className="px-2 py-1 rounded-lg bg-slate-900 text-slate-400 hover:text-white text-[11px] transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Interactive Causal Sandbox Bar */}
          <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/80 flex flex-wrap items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowInvoiceModal(true)}
                className="px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-medium text-xs transition flex items-center gap-1.5 shadow"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Draft Invoice (Live 3D)</span>
              </button>
              <button
                onClick={() => simulateDelay()}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-warningamber border border-slate-700 font-medium text-xs transition flex items-center gap-1.5"
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Simulate 30d Delay</span>
              </button>
              <button
                onClick={handleExecuteWormhole}
                className="px-3.5 py-2 rounded-xl bg-accentcyan/10 hover:bg-accentcyan/20 border border-accentcyan/40 text-accentcyan font-semibold text-xs transition flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Activate Wormhole</span>
              </button>
            </div>

            <div className="text-xs text-slate-400 font-mono">
              Event Horizon: <strong className="text-dangerrose">20 Nov</strong>
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: Causal Intelligence Console (40% on desktop) */}
        <div className="lg:col-span-5 flex flex-col bg-slate-950 h-[calc(100vh-64px)] overflow-hidden">
          
          {/* Console Header */}
          <div className="h-12 px-5 border-b border-slate-800/80 bg-slate-900/40 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Causal Intelligence Console
              </span>
            </div>
            <span className="text-[11px] text-brand-400 font-mono">Zero Hardcoded Training</span>
          </div>

          {/* Messages Scroll Area */}
          <div ref={chatEndRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"} items-start gap-2.5`}
              >
                {m.sender === "ai" && (
                  <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-brand-600 to-accentcyan flex items-center justify-center font-bold text-white text-[10px] shrink-0 mt-1 shadow">
                    AP
                  </div>
                )}
                <div
                  className={`max-w-[90%] p-4 rounded-2xl ${
                    m.sender === "user"
                      ? "bg-brand-600 text-white rounded-br-sm text-sm"
                      : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-sm text-sm space-y-3"
                  }`}
                >
                  {m.sender === "ai" && (
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 text-[11px]">
                      <span className="font-bold text-white">Central Nervous System</span>
                      <span className="text-slate-500 font-mono">{m.timestamp}</span>
                    </div>
                  )}

                  {/* Body Text */}
                  <div className="leading-relaxed whitespace-pre-line text-xs sm:text-sm text-slate-200">
                    {m.text}
                  </div>

                  {/* Recommendations */}
                  {m.recommendations && m.recommendations.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block">
                        Recommended Causal Actions:
                      </span>
                      {m.recommendations.map((rec, rIdx) => (
                        <div
                          key={rIdx}
                          className="p-2 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 flex items-center justify-between"
                        >
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Expandable Vitals & Counterfactual */}
                  {m.numbers && (
                    <div className="pt-2 border-t border-slate-800/80">
                      <button
                        onClick={() => setOpenDetailsId(openDetailsId === m.id ? null : m.id)}
                        className="text-[11px] font-medium text-accentcyan hover:underline flex items-center gap-1"
                      >
                        <span>View Exact Numbers & Counterfactual</span>
                        {openDetailsId === m.id ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {openDetailsId === m.id && (
                        <div className="mt-2 space-y-2 text-xs">
                          <div className="p-2.5 rounded-xl bg-black/80 border border-slate-800 mono text-slate-300 whitespace-pre-line text-[11px] leading-relaxed">
                            {m.numbers}
                          </div>
                          {m.causalExplanation && (
                            <div className="p-2 rounded-xl bg-accentcyan/5 border border-accentcyan/20 text-slate-300 text-[11px] leading-relaxed">
                              <span className="font-semibold text-accentcyan block mb-0.5">Causal Mechanism:</span>
                              {m.causalExplanation}
                            </div>
                          )}
                          {m.whatIf && (
                            <div className="p-2 rounded-xl bg-dangerrose/10 border border-dangerrose/30 text-dangerrose text-[11px] leading-relaxed">
                              <span className="font-semibold block mb-0.5">Counterfactual (If ignored):</span>
                              {m.whatIf}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isThinking && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <div className="w-6 h-6 rounded-full bg-accentcyan/20 text-accentcyan flex items-center justify-center font-bold text-[10px]">
                  AP
                </div>
                <div className="px-3.5 py-2 rounded-2xl bg-slate-900 border border-slate-800 flex items-center gap-1.5">
                  <span className="text-xs text-slate-300 font-medium">Computing causal trajectories</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan animate-bounce [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}
          </div>

          {/* Console Input Bar */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-900/60 flex flex-col gap-2 shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!inputQuery.trim()) return;
                playUiSound("click");
                sendMessage(inputQuery);
                setInputQuery("");
              }}
              className="flex items-center gap-2"
            >
              {/* Document OCR upload */}
              <label
                className="cursor-pointer p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 transition shrink-0"
                title="Upload Invoice Document (OCR)"
              >
                <input type="file" onChange={handleFileUpload} accept="image/*,.pdf" className="hidden" />
                <Camera className="w-4 h-4" />
              </label>

              {/* Free-form text query input */}
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask anything (e.g. 'Can I afford ₹3L?', 'Who owes me money?')..."
                className="flex-1 bg-slate-950 border border-slate-800 focus:border-brand-500 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none transition shadow-inner"
              />

              {/* Send Button */}
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs transition flex items-center gap-1.5 shadow"
              >
                <span>Ask</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>

      </div>

      {/* DRAFT INVOICE MODAL */}
      {showInvoiceModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-slate-950 border border-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Draft New Invoice</h3>
              <button
                onClick={() => setShowInvoiceModal(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Cancel
              </button>
            </div>
            <form onSubmit={handleCreateInvoice} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Customer / Debtor</label>
                <input
                  type="text"
                  value={invCustomer}
                  onChange={(e) => setInvCustomer(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-sm focus:border-brand-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Total Bill Amount (INR)</label>
                <input
                  type="number"
                  value={invAmount}
                  onChange={(e) => setInvAmount(Number(e.target.value))}
                  className="w-full p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-sm font-mono focus:border-brand-500 focus:outline-none"
                  required
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Under Indian CGST Section 39, 18% GST (₹{(invAmount * 0.1525).toFixed(0)}) will immediately accrue.
                </span>
              </div>
              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm transition shadow"
              >
                Create Invoice & Update 3D Graph
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
