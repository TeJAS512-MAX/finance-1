"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck, Zap, Sparkles } from "lucide-react";
import FinancialOrganismCanvas from "../3d/FinancialOrganism3D";
import { playUiSound } from "./AudioController";
import { useAetherStore } from "@/lib/store";

export default function HeroSection({
  onEnterOrganism,
}: {
  onEnterOrganism: () => void;
}) {
  const state = useAetherStore((s) => s.state);
  const singularity = useAetherStore((s) => s.singularity);
  const candidates = useAetherStore((s) => s.candidates);
  const wormholePhase = useAetherStore((s) => s.wormholePhase);

  const healthScore = state.genome.overall_score;
  const rupeesLakhs = (state.physics_state.total_rupees_conserved / 100000).toFixed(2);

  return (
    <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden px-6 pt-12 pb-16">
      {/* Background Subtle Gradient Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[700px] bg-gradient-to-tr from-brand-600/15 via-accentcyan/15 to-transparent rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-96 h-96 bg-dangerrose/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative z-10">
        
        {/* Left Column: Vision & Typography */}
        <div className="lg:col-span-7 space-y-6 text-left">
          
          {/* Category Innovation Badge */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full glass-card border border-brand-500/30 text-xs md:text-sm font-medium text-brand-400"
          >
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-ping" />
            <span>World&apos;s First Causal Financial Organism</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-300">CGST Section 39 Protective Layer</span>
          </motion.div>

          {/* Main Hero Headline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="space-y-2"
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white leading-[1.12]">
              Build AI that{" "}
              <span className="bg-gradient-to-r from-brand-400 via-accentcyan to-brand-500 bg-clip-text text-transparent">
                handles money better
              </span>
            </h1>
            <p className="text-xl md:text-2xl font-semibold text-slate-300 tracking-tight leading-snug">
              “The AI that treats your money like a living organism and never lets it die.”
            </p>
          </motion.div>

          {/* Deep Narrative Description */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="text-base md:text-lg text-slate-300 font-normal leading-[1.65] max-w-2xl"
          >
            Indian MSMEs don&apos;t fail from lack of profit—they fail from the{" "}
            <strong className="text-dangerrose font-semibold">GST Accrual Trap</strong>, delayed institutional payments, and mismatched loan EMIs. AetherPravah maintains a continuous{" "}
            <span className="text-white font-medium">Causal Spacetime Digital Twin</span> of every rupee, predicts liquidity black holes weeks before they strike, and automatically forges{" "}
            <span className="text-accentcyan font-medium">Liquidity Wormholes</span> to keep your business alive.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="flex flex-wrap items-center gap-4 pt-2"
          >
            <button
              onClick={() => {
                playUiSound("click");
                onEnterOrganism();
              }}
              className="px-7 py-3.5 rounded-xl bg-gradient-to-r from-brand-600 via-brand-500 to-accentcyan hover:from-brand-500 hover:to-accentcyan text-white font-semibold text-base shadow-xl shadow-brand-500/25 transition-all duration-300 hover:scale-[1.02] flex items-center gap-2.5 group"
            >
              <span>Enter the Organism</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>

            <a
              href="#architecture"
              onClick={() => playUiSound("click")}
              className="px-6 py-3.5 rounded-xl glass-card hover:bg-slate-800/90 border border-panelborder text-slate-300 hover:text-white font-medium text-base transition-all duration-300 flex items-center gap-2"
            >
              <Zap className="w-4 h-4 text-accentcyan" />
              <span>Causal Architecture</span>
            </a>
          </motion.div>

          {/* Live Micro Vitals Bar */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="pt-6 border-t border-panelborder/80 grid grid-cols-3 gap-4 text-xs md:text-sm font-medium"
          >
            <div>
              <span className="text-slate-400 block text-xs uppercase tracking-wider">Rupee Conservation</span>
              <span className="text-white font-bold mono text-base">₹{rupeesLakhs} Lakhs</span>
              <span className="text-brand-400 block text-[11px] font-normal">Zero Mathematical Leakage</span>
            </div>
            <div>
              <span className="text-slate-400 block text-xs uppercase tracking-wider">GST Singularity</span>
              <span className={`font-bold mono text-base ${singularity.severity === "LOW" ? "text-brand-400" : "text-dangerrose"}`}>
                {singularity.severity === "LOW" ? "Neutralized" : `${singularity.days_to_event_horizon} Days Left`}
              </span>
              <span className="text-slate-400 block text-[11px] font-normal">20 Nov Cut-off Horizon</span>
            </div>
            <div>
              <span className="text-slate-400 block text-xs uppercase tracking-wider">Wormhole Bridge</span>
              <span className="text-accentcyan font-bold mono text-base">
                {wormholePhase === "EXECUTED" ? "Active Transmit" : `${candidates.length} Pareto Paths`}
              </span>
              <span className="text-slate-400 block text-[11px] font-normal">
                {wormholePhase === "EXECUTED" ? "100% Ring-Fenced" : "Instant 24-36h Teleport"}
              </span>
            </div>
          </motion.div>

        </div>

        {/* Right Column: 3D Living Organism */}
        <div className="lg:col-span-5 h-[480px] lg:h-[580px] w-full relative flex items-center justify-center">
          <div className="absolute inset-0 wormhole-tunnel rounded-full pointer-events-none" />
          
          {/* Reacts live to health score: Emerald when healthy (96), Amber/Rose when stressed (38) */}
          <FinancialOrganismCanvas healthScore={healthScore} interactive={true} />

          {/* Floating Micro Highlights */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="absolute top-8 left-0 p-3.5 rounded-2xl glass-card border border-panelborder shadow-xl text-xs space-y-1 max-w-[200px]"
          >
            <div className="flex items-center gap-2 text-warningamber font-semibold">
              <Sparkles className="w-4 h-4" />
              <span>Living Fluid Physics</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Viscosity index {state.physics_state.viscosity_index.toFixed(2)} tracking collection friction.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="absolute bottom-8 right-0 p-3.5 rounded-2xl glass-card border border-brand-500/30 shadow-xl text-xs space-y-1 max-w-[210px]"
          >
            <div className="flex items-center gap-2 text-brand-400 font-semibold">
              <ShieldCheck className="w-4 h-4" />
              <span>Tax Gravity Shield</span>
            </div>
            <p className="text-slate-400 text-[11px]">Automatic tax reservation prevents statutory account freezes.</p>
          </motion.div>
        </div>

      </div>
    </section>
  );
}
