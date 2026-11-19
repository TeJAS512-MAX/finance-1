"use client";

import React, { useState, useEffect, useRef } from "react";
import confetti from "canvas-confetti";
import {
  Send,
  Camera,
  Mic,
  Activity,
  AlertTriangle,
  Sparkles,
  TrendingUp,
  Award,
  Clock,
  Shield,
  Scissors,
  Cpu,
  RefreshCw,
  Droplet,
  Anchor,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { playUiSound } from "./AudioController";
import { useAetherStore } from "@/lib/store";
import CausalGraphCanvas from "../3d/CausalGraph3D";
import WormholePortalCanvas from "../3d/WormholePortal3D";
import GenomeDoubleHelixCanvas from "../3d/GenomeDoubleHelix3D";

export default function LivingAppExperience() {
  // Global Live Store
  const businessKey = useAetherStore((s) => s.businessKey);
  const state = useAetherStore((s) => s.state);
  const singularity = useAetherStore((s) => s.singularity);
  const candidates = useAetherStore((s) => s.candidates);
  const selectedCandidateIdx = useAetherStore((s) => s.selectedCandidateIdx);
  const setSelectedCandidateIdx = useAetherStore((s) => s.setSelectedCandidateIdx);
  const wormholePhase = useAetherStore((s) => s.wormholePhase);
  const messages = useAetherStore((s) => s.messages);
  const isAiThinking = useAetherStore((s) => s.isAiThinking);

  const switchBusiness = useAetherStore((s) => s.switchBusiness);
  const createInvoiceLive = useAetherStore((s) => s.createInvoiceLive);
  const simulateDelayLive = useAetherStore((s) => s.simulateDelayLive);
  const executeWormholeLive = useAetherStore((s) => s.executeWormholeLive);
  const sendMessageLive = useAetherStore((s) => s.sendMessageLive);

  // Local UI state
  const [activeTab, setActiveTab] = useState<"singularity" | "graph" | "wormhole" | "trajectory">("singularity");
  const [inputText, setInputText] = useState("");
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);
  const [openDetailsCardId, setOpenDetailsCardId] = useState<string | null>(null);

  const chatScrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat on new messages or thinking status
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, isAiThinking]);

  // Handle switching business archetype
  const handleSwitchArchetype = (key: string) => {
    playUiSound("click");
    switchBusiness(key);
  };

  // Submit chat message
  const handleSendMessage = async (customText?: string) => {
    const textToSend = customText || inputText;
    if (!textToSend.trim()) return;

    if (!customText) setInputText("");
    await sendMessageLive(textToSend);
  };

  // Trigger wormhole execution
  const executeWormhole = async () => {
    confetti({
      particleCount: 140,
      spread: 80,
      origin: { y: 0.6 },
      colors: ["#10b981", "#22d3ee", "#f59e0b"],
    });
    await executeWormholeLive();
  };

  // Voice note simulation
  const startVoiceNoteSimulation = () => {
    playUiSound("click");
    setIsVoiceRecording(true);
    setTimeout(() => {
      setIsVoiceRecording(false);
      handleSendMessage("What is my cash runway status? Create invoice for Reliance 2.5 lakh");
    }, 2800);
  };

  // Photo upload simulation
  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    playUiSound("click");
    handleSendMessage(`Uploaded invoice photo: ${file.name}. Run Vision OCR and check GST liability.`);
  };

  const activeWormhole = candidates[selectedCandidateIdx] || candidates[0];
  const isWormholeExecuted = wormholePhase === "EXECUTED" || (state.active_wormholes.length > 0 && state.active_wormholes[0].status === "EXECUTED");

  return (
    <section id="living-organism" className="min-h-screen py-10 px-4 sm:px-6 max-w-[1550px] mx-auto">
      {/* Top Header Command Bar */}
      <div className="mb-6 p-4 rounded-2xl glass-panel border border-panelborder flex flex-wrap items-center justify-between gap-4">
        
        {/* Archetype Switcher */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mr-1">
            MSME Twin:
          </span>
          <div className="flex items-center bg-black/50 rounded-xl p-1 border border-panelborder text-xs md:text-sm">
            <button
              onClick={() => handleSwitchArchetype("STEEL_TRADER")}
              className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                businessKey === "STEEL_TRADER"
                  ? "bg-brand-600 text-white shadow-md shadow-brand-600/30 font-semibold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>Bharat Steel (Navi Mumbai)</span>
            </button>
            <button
              onClick={() => handleSwitchArchetype("VASTRAKALA")}
              className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                businessKey === "VASTRAKALA"
                  ? "bg-brand-600 text-white shadow-md shadow-brand-600/30 font-semibold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Scissors className="w-4 h-4" />
              <span>VastraKala (Surat)</span>
            </button>
            <button
              onClick={() => handleSwitchArchetype("NEXUS_PULSE")}
              className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                businessKey === "NEXUS_PULSE"
                  ? "bg-brand-600 text-white shadow-md shadow-brand-600/30 font-semibold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>NexusPulse (Bengaluru)</span>
            </button>
          </div>
        </div>

        {/* Genome Score Pill */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
            <span className="mono text-slate-300 font-semibold">{state.business.city}</span>
            <span className="px-2 py-0.5 rounded bg-black/60 text-slate-300 mono text-xs border border-panelborder">
              GST: {state.business.gstin}
            </span>
          </div>

          <div
            className={`flex items-center gap-2.5 px-4 py-2 rounded-xl border ${
              state.genome.overall_score >= 70
                ? "bg-brand-500/10 border-brand-500/30 text-brand-400"
                : state.genome.overall_score >= 50
                ? "bg-warningamber/10 border-warningamber/30 text-warningamber"
                : "bg-dangerrose/10 border-dangerrose/30 text-dangerrose"
            }`}
          >
            <div className="relative flex items-center justify-center">
              <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-current opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-current" />
            </div>
            <div className="flex flex-col text-right">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Health Genome
              </span>
              <span className="text-base font-bold mono leading-none">
                {state.genome.overall_score} / 100
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Main Dual-Pane Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start h-[780px]">
        
        {/* LEFT PANE: Conversational AI Twin (5 cols) */}
        <div className="lg:col-span-5 h-full rounded-2xl glass-panel border border-panelborder flex flex-col overflow-hidden bg-darkerbg shadow-2xl relative">
          
          {/* Chat Header */}
          <div className="h-16 px-4 py-3 border-b border-panelborder bg-panel/60 backdrop-blur-md flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-brand-600 to-accentcyan flex items-center justify-center font-bold text-white text-xs shadow-md">
                  AP
                </div>
                <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-brand-500 border-2 border-darkbg" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm md:text-base font-semibold text-white tracking-tight">
                    AetherPravah AI
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-400 font-medium">
                    Online
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-medium">24x7 Causal CFO Organism</p>
              </div>
            </div>
            <div className="text-xs text-brand-400 font-medium flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Conserved</span>
            </div>
          </div>

          {/* Quick Suggested Prompt Chips */}
          <div className="p-2.5 border-b border-panelborder bg-black/40 flex items-center gap-2 overflow-x-auto text-xs shrink-0 no-scrollbar">
            <button
              onClick={() => handleSendMessage("How is my money?")}
              className="px-3.5 py-1.5 rounded-full bg-panel hover:bg-slate-800 border border-panelborder text-slate-300 hover:text-white transition whitespace-nowrap font-medium"
            >
              🩺 How is my money?
            </button>
            <button
              onClick={() => handleSendMessage("Who owes me the most money?")}
              className="px-3.5 py-1.5 rounded-full bg-panel hover:bg-slate-800 border border-panelborder text-slate-300 hover:text-white transition whitespace-nowrap font-medium"
            >
              📊 Who owes me money?
            </button>
            <button
              onClick={() => handleSendMessage("Can I afford a new machine of 5 lakhs?")}
              className="px-3.5 py-1.5 rounded-full bg-panel hover:bg-slate-800 border border-panelborder text-slate-300 hover:text-white transition whitespace-nowrap font-medium"
            >
              🛑 Can I spend 5 Lakhs?
            </button>
            <button
              onClick={() => createInvoiceLive("Reliance Infra", 250000)}
              className="px-3.5 py-1.5 rounded-full bg-panel hover:bg-slate-800 border border-panelborder text-accentcyan hover:text-white transition whitespace-nowrap font-medium"
            >
              📄 Create Reliance Bill (Live 3D)
            </button>
            <button
              onClick={() => simulateDelayLive()}
              className="px-3.5 py-1.5 rounded-full bg-dangerrose/10 border border-dangerrose/40 hover:bg-dangerrose/20 text-dangerrose transition whitespace-nowrap font-medium"
            >
              ⚠️ Simulate 30d Delay
            </button>
            <button
              onClick={executeWormhole}
              className="px-3.5 py-1.5 rounded-full bg-accentcyan/10 border border-accentcyan/40 hover:bg-accentcyan/20 text-accentcyan transition whitespace-nowrap font-semibold"
            >
              ⚡ Trigger Wormhole
            </button>
          </div>

          {/* Messages Scroll Area */}
          <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"} items-start gap-2.5`}
              >
                {msg.sender === "ai" && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-600 to-accentcyan flex items-center justify-center font-bold text-white text-[11px] shrink-0 mt-1 shadow">
                    AP
                  </div>
                )}
                <div
                  className={`max-w-[88%] p-4 rounded-2xl ${
                    msg.sender === "user"
                      ? "chat-bubble-user text-white rounded-br-sm text-base font-normal leading-relaxed"
                      : "chat-bubble-ai text-slate-200 rounded-tl-sm space-y-3"
                  }`}
                >
                  {msg.sender === "ai" && (
                    <div className="flex items-center justify-between border-b border-panelborder/60 pb-2 text-xs">
                      <span className="font-bold text-white">AetherPravah AI</span>
                      <span className="text-slate-500 font-medium">{msg.timestamp}</span>
                    </div>
                  )}

                  {/* Body Text: 16px Regular, line-height 1.65 */}
                  <div className="text-base font-normal leading-[1.65] text-slate-200 whitespace-pre-line">
                    {msg.text}
                  </div>

                  {/* Recommendations */}
                  {msg.recommendations && msg.recommendations.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide block">
                        Recommended Actions:
                      </span>
                      {msg.recommendations.map((rec, rIdx) => (
                        <div
                          key={rIdx}
                          className="p-2.5 rounded-xl bg-panel/80 border border-panelborder text-xs text-slate-200 flex items-center justify-between"
                        >
                          <span>{rec}</span>
                          {rec.includes("Wormhole") && (
                            <button
                              onClick={executeWormhole}
                              className="ml-2 px-2.5 py-1 rounded-lg bg-accentcyan hover:bg-white text-black font-semibold text-xs shrink-0 transition"
                            >
                              Activate
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Collapsible Exact Financial Vitals */}
                  {msg.numbers && (
                    <div className="pt-2 border-t border-panelborder/60">
                      <button
                        onClick={() =>
                          setOpenDetailsCardId(openDetailsCardId === msg.id ? null : msg.id)
                        }
                        className="text-xs font-medium text-accentcyan hover:underline flex items-center gap-1"
                      >
                        <span>View Exact Financial Vitals & Counterfactual</span>
                        {openDetailsCardId === msg.id ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {openDetailsCardId === msg.id && (
                        <div className="mt-2.5 space-y-2 text-xs">
                          <div className="p-3 rounded-xl bg-black/60 border border-panelborder mono text-slate-300 whitespace-pre-line leading-relaxed">
                            {msg.numbers}
                          </div>
                          {msg.causalExplanation && (
                            <div className="p-2.5 rounded-xl bg-accentcyan/5 border border-accentcyan/20 text-slate-300 leading-relaxed">
                              <span className="font-semibold text-accentcyan block mb-0.5">
                                Causal Spacetime Driver:
                              </span>
                              {msg.causalExplanation}
                            </div>
                          )}
                          {msg.whatIf && (
                            <div className="p-2.5 rounded-xl bg-dangerrose/10 border border-dangerrose/30 text-dangerrose leading-relaxed">
                              <span className="font-semibold block mb-0.5">
                                What if you ignore this? (Counterfactual)
                              </span>
                              {msg.whatIf}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isAiThinking && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <div className="w-7 h-7 rounded-full bg-accentcyan/20 text-accentcyan flex items-center justify-center font-bold text-xs">
                  AP
                </div>
                <div className="px-3.5 py-2 rounded-2xl bg-panel border border-panelborder flex items-center gap-1.5">
                  <span className="text-xs text-slate-300 font-medium">Computing causal trajectories</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan typing-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan typing-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-accentcyan typing-dot" />
                </div>
              </div>
            )}
          </div>

          {/* Voice Note Recording Banner */}
          {isVoiceRecording && (
            <div className="px-4 py-2.5 bg-accentpurple/15 border-t border-accentpurple/30 flex items-center justify-between text-xs text-accentpurple">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accentpurple animate-ping" />
                <span className="font-medium">Listening to English voice note...</span>
              </div>
              <span className="mono text-[11px] text-slate-400">Processing audio</span>
            </div>
          )}

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-panelborder bg-darkbg flex flex-col gap-2 shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              {/* Photo OCR Upload Button */}
              <label
                className="cursor-pointer p-2.5 rounded-xl bg-panel hover:bg-slate-800 text-slate-400 hover:text-white border border-panelborder transition flex items-center justify-center shrink-0"
                title="Upload Invoice Photo (Vision OCR)"
              >
                <input
                  type="file"
                  onChange={handlePhotoUpload}
                  accept="image/*,.pdf"
                  className="hidden"
                />
                <Camera className="w-4 h-4" />
              </label>

              {/* Simulated Mic Button */}
              <button
                type="button"
                onClick={startVoiceNoteSimulation}
                className="p-2.5 rounded-xl bg-panel hover:bg-slate-800 text-slate-400 hover:text-accentpurple border border-panelborder transition flex items-center justify-center shrink-0"
                title="Simulate Voice Note"
              >
                <Mic className="w-4 h-4" />
              </button>

              {/* Text Input: 16px text-base */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask anything (e.g. 'How is my money?', 'Who owes me money?')..."
                className="flex-1 bg-panel border border-panelborder focus:border-brand-500 rounded-xl px-4 py-2.5 text-base font-normal text-white placeholder-slate-500 focus:outline-none transition shadow-inner"
              />

              {/* Send Button */}
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm transition flex items-center gap-1.5 shadow-md shadow-brand-600/20 shrink-0"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>

        {/* RIGHT PANE: 3D Living Financial Dashboard (7 cols) */}
        <div className="lg:col-span-7 h-full rounded-2xl glass-panel border border-panelborder flex flex-col overflow-hidden bg-darkerbg shadow-2xl">
          
          {/* Dashboard Tabs Header */}
          <div className="h-16 px-6 border-b border-panelborder bg-panel/40 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("singularity");
                }}
                className={`px-3.5 py-2 rounded-lg text-xs md:text-sm font-semibold transition flex items-center gap-1.5 shrink-0 ${
                  activeTab === "singularity"
                    ? "border-b-2 border-dangerrose text-white font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <AlertTriangle className="w-4 h-4 text-dangerrose" />
                <span>GST Singularity</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("graph");
                }}
                className={`px-3.5 py-2 rounded-lg text-xs md:text-sm font-semibold transition flex items-center gap-1.5 shrink-0 ${
                  activeTab === "graph"
                    ? "border-b-2 border-accentcyan text-white font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Activity className="w-4 h-4 text-accentcyan" />
                <span>3D Causal Graph</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("wormhole");
                }}
                className={`px-3.5 py-2 rounded-lg text-xs md:text-sm font-semibold transition flex items-center gap-1.5 shrink-0 ${
                  activeTab === "wormhole"
                    ? "border-b-2 border-brand-500 text-white font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Sparkles className="w-4 h-4 text-brand-500" />
                <span>Wormhole Forger</span>
              </button>
              <button
                onClick={() => {
                  playUiSound("click");
                  setActiveTab("trajectory");
                }}
                className={`px-3.5 py-2 rounded-lg text-xs md:text-sm font-semibold transition flex items-center gap-1.5 shrink-0 ${
                  activeTab === "trajectory"
                    ? "border-b-2 border-brand-500 text-white font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <TrendingUp className="w-4 h-4 text-brand-400" />
                <span>What-If Trajectory</span>
              </button>
            </div>

            <div className="text-xs mono text-slate-400 font-medium hidden sm:flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>Sim Date: 16 Nov 2026</span>
            </div>
          </div>

          {/* TAB 1: GST SINGULARITY RADAR */}
          {activeTab === "singularity" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Singularity Alert Card */}
              <div className="p-6 rounded-2xl glass-card singularity-glow border border-dangerrose/30 bg-dangerrose/5 relative overflow-hidden">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                        singularity.severity === "LOW"
                          ? "bg-brand-500/20 text-brand-400 border border-brand-500/30"
                          : "bg-dangerrose/20 text-dangerrose border border-dangerrose/30"
                      }`}>
                        {singularity.severity === "LOW" ? "SINGULARITY NEUTRALIZED" : "CRITICAL BLACK HOLE"}
                      </span>
                      <span className="text-xs md:text-sm text-slate-400 font-medium">
                        Event Horizon in{" "}
                        <strong className="text-white mono font-bold">
                          {singularity.days_to_event_horizon} Days
                        </strong>{" "}
                        (20 Nov 2026)
                      </span>
                    </div>
                    <h3 className="text-lg md:text-xl font-bold text-white tracking-tight mt-1.5 leading-snug">
                      GST Accrual Singularity
                    </h3>
                    <p className="text-xs md:text-sm text-slate-300 font-normal mt-1 max-w-xl leading-relaxed">
                      CGST Act Section 39 mandates cash tax settlement on billed invoices even when institutional buyers take 45+ days to pay.
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 uppercase tracking-wider font-medium block mb-1">
                      Deficit at Horizon
                    </span>
                    <div className={`text-3xl md:text-4xl font-bold mono tracking-tighter leading-none ${
                      singularity.severity === "LOW" ? "text-brand-400" : "text-dangerrose"
                    }`}>
                      ₹{singularity.singularity_depth.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>

                {/* Statutory Cash Breakdown Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5 mt-5 pt-4 border-t border-panelborder text-xs">
                  <div className="p-3 rounded-xl bg-panel/70 border border-panelborder">
                    <span className="text-slate-400 block text-[11px] font-medium uppercase tracking-wider">
                      Net Tax Due (20th)
                    </span>
                    <span className="text-white font-bold mono text-base block mt-0.5">
                      ₹{state.gst_snapshot.net_gst_cash_payable.toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-panel/70 border border-dangerrose/30">
                    <span className="text-dangerrose block text-[11px] font-semibold uppercase tracking-wider">
                      GST on Unpaid Bills
                    </span>
                    <span className="text-dangerrose font-bold mono text-base block mt-0.5">
                      ₹{state.gst_snapshot.gst_on_unpaid_invoices.toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-panel/70 border border-panelborder">
                    <span className="text-slate-400 block text-[11px] font-medium uppercase tracking-wider">
                      Bank Cash Reserve
                    </span>
                    <span className="text-white font-bold mono text-base block mt-0.5">
                      ₹{state.physics_state.bank_cash.toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-panel/70 border border-panelborder">
                    <span className="text-slate-400 block text-[11px] font-medium uppercase tracking-wider">
                      Tax Vault Balance
                    </span>
                    <span className="text-accentcyan font-bold mono text-base block mt-0.5">
                      ₹{state.physics_state.tax_vault_balance.toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Macroscopic Physics Vitals (Fluid Viscosity & Tax Gravity) */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-5 rounded-xl glass-card border border-panelborder">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-400 mb-2">
                    <span>Fluid Viscosity Index</span>
                    <Droplet className="w-4 h-4 text-warningamber" />
                  </div>
                  <div className="text-3xl font-bold mono tracking-tighter text-warningamber leading-none">
                    {state.physics_state.viscosity_index.toFixed(2)}
                  </div>
                  <p className="text-xs text-slate-400 mt-2">1.0 = Laminar, 3.0+ = Delayed collections</p>
                </div>

                <div className="p-5 rounded-xl glass-card border border-panelborder">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-400 mb-2">
                    <span>Tax Gravity Force</span>
                    <Anchor className="w-4 h-4 text-accentpurple" />
                  </div>
                  <div className="text-2xl font-bold mono tracking-tighter text-accentpurple leading-none">
                    ₹{Math.round(state.physics_state.tax_gravity_well).toLocaleString("en-IN")}/d
                  </div>
                  <p className="text-xs text-slate-400 mt-2">Downward pull to 20th statutory cut-off</p>
                </div>

                <div className="p-5 rounded-xl glass-card border border-panelborder">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-400 mb-2">
                    <span>Operating Runway</span>
                    <Clock className="w-4 h-4 text-brand-500" />
                  </div>
                  <div className="text-3xl font-bold mono tracking-tighter text-brand-500 leading-none">
                    {state.physics_state.estimated_runway_days.toFixed(1)} Days
                  </div>
                  <p className="text-xs text-slate-400 mt-2">Conformal 90% confidence bound</p>
                </div>
              </div>

              {/* Invoices Table */}
              <div className="p-5 rounded-xl glass-card border border-panelborder">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs md:text-sm font-bold text-slate-200 uppercase tracking-wider">
                    Unsettled Receivables & Accrual Matrix
                  </h4>
                  <span className="text-xs mono text-slate-400">
                    Total Pending:{" "}
                    <strong className="text-white">
                      ₹{state.physics_state.pending_receivables.toLocaleString("en-IN")}
                    </strong>
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs md:text-sm">
                    <thead>
                      <tr className="text-slate-400 border-b border-panelborder font-medium uppercase text-xs">
                        <th className="pb-2.5">Invoice #</th>
                        <th className="pb-2.5">Customer</th>
                        <th className="pb-2.5">Total (₹)</th>
                        <th className="pb-2.5">GST Accrued</th>
                        <th className="pb-2.5">Delay Pred</th>
                        <th className="pb-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-panelborder/50 text-slate-300 font-normal">
                      {state.invoices.map((inv) => (
                        <tr key={inv.id} className="hover:bg-panel/40 transition">
                          <td className="py-2.5 font-medium mono text-white">{inv.invoice_number}</td>
                          <td className="py-2.5">{inv.customer_name}</td>
                          <td className="py-2.5 font-bold mono">₹{inv.total_amount.toLocaleString("en-IN")}</td>
                          <td className="py-2.5 font-medium mono text-dangerrose">
                            ₹{inv.gst_amount.toLocaleString("en-IN")}
                          </td>
                          <td className="py-2.5 mono text-warningamber">+{inv.delay_prediction_days}d</td>
                          <td className="py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                inv.status === "PAID"
                                  ? "bg-brand-500/20 text-brand-500"
                                  : inv.status === "CRITICAL_TRAP"
                                  ? "bg-dangerrose/20 text-dangerrose"
                                  : "bg-accentcyan/20 text-accentcyan"
                              }`}
                            >
                              {inv.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: 3D CAUSAL SPACETIME GRAPH */}
          {activeTab === "graph" && (
            <div className="flex-1 p-6 flex flex-col space-y-4">
              <div className="flex items-center justify-between text-xs">
                <div>
                  <h4 className="text-base font-bold text-white tracking-tight">
                    3D Causal Spacetime Graph (Live Reactive)
                  </h4>
                  <p className="text-slate-400">
                    Interactive topology of RupeePackets, Invoice accrual vectors, and Black Hole gravitational wells.
                  </p>
                </div>
                <span className="px-3 py-1 rounded-full bg-accentcyan/10 border border-accentcyan/30 text-accentcyan font-mono text-xs">
                  Strict Conservation: ₹{(state.physics_state.total_rupees_conserved / 100000).toFixed(2)} Lakhs
                </span>
              </div>

              <div className="flex-1 h-[520px] rounded-2xl overflow-hidden relative border border-panelborder">
                <CausalGraphCanvas />
              </div>
            </div>
          )}

          {/* TAB 3: LIQUIDITY WORMHOLE FORGER */}
          {activeTab === "wormhole" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              
              {/* Pareto Frontier Strategy Tabs */}
              {candidates.length > 1 && !isWormholeExecuted && (
                <div className="p-2.5 rounded-xl bg-panel/70 border border-panelborder flex items-center gap-2 overflow-x-auto text-xs md:text-sm">
                  <span className="text-slate-400 font-semibold uppercase tracking-wider text-xs pl-1 shrink-0">
                    Pareto Strategies:
                  </span>
                  {candidates.map((c, idx) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        playUiSound("click");
                        setSelectedCandidateIdx(idx);
                      }}
                      className={`px-3.5 py-2 rounded-lg font-medium transition flex items-center gap-1.5 shrink-0 ${
                        idx === selectedCandidateIdx
                          ? "bg-accentcyan text-black font-bold shadow-md shadow-accentcyan/30"
                          : "bg-panel border border-panelborder text-slate-300 hover:text-white"
                      }`}
                    >
                      <span>{c.title.includes(":") ? c.title.split(":")[1].trim() : c.title}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Wormhole 3D Portal Card */}
              <div className="p-6 rounded-2xl glass-card wormhole-glow border border-accentcyan/40 bg-accentcyan/5 space-y-5 relative overflow-hidden">
                <div className="flex items-start justify-between">
                  <div>
                    <span
                      className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                        isWormholeExecuted
                          ? "bg-brand-500/20 text-brand-500 border border-brand-500/30"
                          : "bg-accentcyan/20 text-accentcyan border border-accentcyan/30"
                      }`}
                    >
                      {isWormholeExecuted ? "EXECUTED" : activeWormhole.status}
                    </span>
                    <h3 className="text-lg md:text-xl font-bold text-white tracking-tight mt-2 leading-snug">
                      {activeWormhole.title}
                    </h3>
                    <p className="text-xs md:text-sm text-slate-300 font-normal mt-1 max-w-xl leading-relaxed">
                      {activeWormhole.explanation_narrative}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 uppercase tracking-wider font-medium block mb-1">
                      Gross Liberated
                    </span>
                    <div className="text-3xl md:text-4xl font-bold text-accentcyan mono tracking-tighter leading-none">
                      ₹{activeWormhole.gross_liquidity_created.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                    <span className="text-xs text-slate-400 font-medium block mt-1">
                      Total Net Cost:{" "}
                      <strong className="mono text-white font-semibold">
                        ₹{activeWormhole.total_net_cost.toLocaleString("en-IN")}
                      </strong>
                    </span>
                  </div>
                </div>

                {/* 3D Wormhole Portal Mini Preview */}
                <div className="h-44 w-full rounded-xl overflow-hidden border border-accentcyan/30 bg-black/60 relative">
                  <WormholePortalCanvas isActivating={wormholePhase === "WARPING" || wormholePhase === "SYNTHESIZED"} />
                </div>

                {/* Step Breakdown */}
                <div className="space-y-2.5 pt-2 border-t border-panelborder">
                  <h4 className="text-xs md:text-sm font-bold text-slate-200 uppercase tracking-wider">
                    Synthesized Vector Steps:
                  </h4>
                  {activeWormhole.steps.map((step) => (
                    <div
                      key={step.step_number}
                      className="p-3.5 rounded-xl bg-panel/70 border border-panelborder flex items-center justify-between text-xs md:text-sm"
                    >
                      <div className="flex items-center gap-3.5">
                        <span className="w-7 h-7 rounded-lg bg-accentcyan/20 text-accentcyan font-bold mono flex items-center justify-center text-xs shrink-0">
                          {step.step_number}
                        </span>
                        <div>
                          <span className="font-semibold text-white text-sm md:text-base">
                            {step.action_type.replace(/_/g, " ")}
                          </span>
                          <span className="text-slate-400 block text-xs md:text-sm font-normal mt-0.5 leading-relaxed">
                            {step.causal_mechanism}
                          </span>
                        </div>
                      </div>
                      <div className="text-right shrink-0 ml-4">
                        <span className="font-bold mono text-brand-500 block text-sm md:text-base">
                          +₹{step.amount_unlocked.toLocaleString("en-IN")}
                        </span>
                        <span className="text-xs text-slate-400 font-medium">
                          {step.implementation_time_hours}h SLA
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Supreme Court Clearance & Execution Button */}
                <div className="p-5 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-between">
                  <div className="flex items-center gap-3.5">
                    <Award className="w-8 h-8 text-brand-500 shrink-0" />
                    <div>
                      <span className="text-xs md:text-sm font-bold text-brand-500 uppercase tracking-wide">
                        Constitutional Supreme Court Clearance
                      </span>
                      <p className="text-xs md:text-[13px] text-slate-300 font-normal mt-0.5">
                        Passed formal symbolic math check • Protects 21-day minimum runway • Paper-trading sandbox
                      </p>
                    </div>
                  </div>
                  {!isWormholeExecuted ? (
                    <button
                      onClick={executeWormhole}
                      className="px-6 py-3 rounded-xl bg-gradient-to-r from-accentcyan to-brand-600 hover:from-accentcyan/90 hover:to-brand-500 text-white font-semibold text-sm md:text-base shadow-lg shadow-accentcyan/20 transition flex items-center gap-2 shrink-0"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>Authorize & Execute Wormhole</span>
                    </button>
                  ) : (
                    <span className="px-4 py-2 rounded-xl bg-brand-500/20 text-brand-500 font-bold text-xs md:text-sm flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Executed Successfully</span>
                    </span>
                  )}
                </div>
              </div>

            </div>
          )}

          {/* TAB 4: PEARLIAN COUNTERFACTUAL FORWARD SIMULATOR */}
          {activeTab === "trajectory" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="p-6 rounded-2xl glass-card border border-panelborder space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg md:text-xl font-bold text-white tracking-tight leading-snug">
                      Pearlian Counterfactual Simulator
                    </h4>
                    <p className="text-xs md:text-sm text-slate-400 font-normal mt-0.5">
                      40-Day Monte-Carlo cash flow trajectory: Status Quo (Inaction) vs do(Liquidity Wormhole).
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      playUiSound("click");
                      handleSendMessage("How is my money?");
                    }}
                    className="px-4 py-2 rounded-xl bg-panel border border-panelborder text-xs md:text-sm text-slate-200 hover:text-white font-medium flex items-center gap-2 transition"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>Re-simulate 100 Runs</span>
                  </button>
                </div>

                {/* 3D Genome Double Helix Canvas Preview */}
                <div className="h-56 w-full rounded-xl overflow-hidden border border-panelborder bg-black/60 relative">
                  <GenomeDoubleHelixCanvas score={state.genome.overall_score} />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-panelborder text-xs md:text-sm">
                  <div className="p-4 rounded-xl bg-dangerrose/10 border border-dangerrose/30">
                    <span className="font-semibold text-dangerrose block text-sm md:text-base mb-1">
                      Path A: Status Quo (Inaction)
                    </span>
                    <p className="text-slate-300 font-normal leading-relaxed">
                      Liquid cash plunges to -₹1.53 Lakhs on 20th Nov. GST E-way bills blocked. Bank accounts frozen under Garnishee statutory order.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-brand-500/10 border border-brand-500/30">
                    <span className="font-semibold text-brand-500 block text-sm md:text-base mb-1">
                      Path B: do(Liquidity Wormhole)
                    </span>
                    <p className="text-slate-300 font-normal leading-relaxed">
                      Cash remains buoyant at +₹13.06 Lakhs. Statutory GST fully covered by Tax Vault. Operating runway safely extends to 40+ days.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

      </div>
    </section>
  );
}
