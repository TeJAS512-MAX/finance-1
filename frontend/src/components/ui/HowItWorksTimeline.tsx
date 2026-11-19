"use client";

import React from "react";
import { motion } from "framer-motion";
import { Camera, AlertTriangle, Sparkles, TrendingUp } from "lucide-react";

const STEPS = [
  {
    step: "01",
    icon: <Camera className="w-5 h-5 text-accentcyan" />,
    title: "Continuous Ingest & Twin Generation",
    description:
      "Upload invoices, bank statements, or voice notes. The active sensor swarm maps every rupee into the Causal Spacetime Graph with strict conservation.",
  },
  {
    step: "02",
    icon: <AlertTriangle className="w-5 h-5 text-dangerrose" />,
    title: "GST Accrual Singularity Detection",
    description:
      "The physics engine measures fluid viscosity and predicts the exact cash deficit on the 20th of the month GSTR-3B tax deadline weeks in advance.",
  },
  {
    step: "03",
    icon: <Sparkles className="w-5 h-5 text-brand-500" />,
    title: "Multi-Vector Wormhole Synthesis",
    description:
      "Synthesizes Pareto-optimal bridges (Trident Balanced, Velocity Surge, Sovereign Shield) combining dynamic rebates, paper factoring, and tax auto-sweep.",
  },
  {
    step: "04",
    icon: <TrendingUp className="w-5 h-5 text-accentpurple" />,
    title: "Formal Clearance & Teleportation",
    description:
      "The Constitutional Supreme Court verifies runway and statutory rules. With 1-click human approval, liquid cash is liberated and tax is 100% secured.",
  },
];

export default function HowItWorksTimeline() {
  return (
    <section id="how-it-works" className="py-20 px-6 max-w-7xl mx-auto border-t border-panelborder/60">
      <div className="text-center space-y-4 mb-16">
        <span className="text-xs uppercase font-bold tracking-wider px-3.5 py-1 rounded-full bg-accentpurple/10 text-accentpurple border border-accentpurple/20">
          Autonomous Lifecycle
        </span>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
          How the Organism Protects Your Money
        </h2>
        <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
          From bill issuance to statutory tax cut-off, follow how AetherPravah prevents liquidity failure.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {STEPS.map((step, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: idx * 0.1 }}
            className="p-6 rounded-2xl glass-card border border-panelborder flex flex-col justify-between space-y-4 relative group hover:border-slate-500 transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="text-2xl font-black mono text-slate-500 group-hover:text-accentcyan transition-colors">
                {step.step}
              </span>
              <div className="p-2.5 rounded-xl bg-black/50 border border-panelborder">
                {step.icon}
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-bold text-white tracking-tight leading-snug">
                {step.title}
              </h3>
              <p className="text-xs md:text-sm text-slate-300 font-normal leading-[1.65]">
                {step.description}
              </p>
            </div>

            <div className="pt-3 border-t border-panelborder/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Autonomous Phase {step.step}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
