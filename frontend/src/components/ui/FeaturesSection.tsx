"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  GitMerge,
  AlertOctagon,
  Sparkles,
  Lock,
  ShieldCheck,
  BrainCircuit,
} from "lucide-react";

interface FeatureCardProps {
  icon: React.ReactNode;
  tag: string;
  title: string;
  description: string;
  benefit: string;
  glowColor: string;
}

const FEATURES: FeatureCardProps[] = [
  {
    icon: <GitMerge className="w-6 h-6 text-accentcyan" />,
    tag: "Physics Substrate",
    title: "Causal Digital Twin",
    description:
      "Tracks every rupee with mass, velocity, and viscous delay. Enforces mathematical conservation laws so money is never lost to hidden leaks.",
    benefit: "Zero mathematical leakage across all bank accounts and invoices.",
    glowColor: "hover:border-accentcyan/50 hover:shadow-[0_0_30px_rgba(34,211,238,0.2)]",
  },
  {
    icon: <AlertOctagon className="w-6 h-6 text-dangerrose" />,
    tag: "Section 39 CGST Act",
    title: "GST Singularity Predictor",
    description:
      "Predicts the exact day when unpaid customer invoices create an unavoidable cash deficit on the 20th of the month GSTR-3B tax filing.",
    benefit: "Detects cash black holes 2–3 weeks before statutory deadlines.",
    glowColor: "hover:border-dangerrose/50 hover:shadow-[0_0_30px_rgba(244,63,94,0.2)]",
  },
  {
    icon: <Sparkles className="w-6 h-6 text-brand-500" />,
    tag: "World First",
    title: "Liquidity Wormhole Forger",
    description:
      "Automatically designs legal multi-vector combinations: behavioral discount acceleration + paper invoice factoring + tax vault auto-sweep.",
    benefit: "Teleports receivables cash in under 36 hours without predatory 36% APR debt.",
    glowColor: "hover:border-brand-500/50 hover:shadow-[0_0_30px_rgba(16,185,129,0.2)]",
  },
  {
    icon: <Lock className="w-6 h-6 text-accentpurple" />,
    tag: "Statutory Escrow",
    title: "Intelligent Tax Vault",
    description:
      "Automatically isolates the 18% or 12% GST component of every rupee received into a protected vault so operating burn cannot consume tax money.",
    benefit: "Eliminates monthly GST filing panic and 18% p.a. default interest.",
    glowColor: "hover:border-accentpurple/50 hover:shadow-[0_0_30px_rgba(139,92,246,0.2)]",
  },
  {
    icon: <ShieldCheck className="w-6 h-6 text-brand-400" />,
    tag: "GSTR-2B Immune System",
    title: "Supplier ITC Sentinel",
    description:
      "Validates supplier filing compliance in real time. Flags non-filing vendors before you pay them, protecting your input tax credits.",
    benefit: "Prevents GSTR-2B credit loss and statutory vendor disputes.",
    glowColor: "hover:border-brand-400/50 hover:shadow-[0_0_30px_rgba(52,211,153,0.2)]",
  },
  {
    icon: <BrainCircuit className="w-6 h-6 text-warningamber" />,
    tag: "Behavioral AI",
    title: "Collection Psychologist",
    description:
      "Analyzes accounts payable psychology across PSU, corporate, and private buyers to deploy the optimal channel, phrasing, and discount timing.",
    benefit: "Accelerates institutional collections by up to 18 days.",
    glowColor: "hover:border-warningamber/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.2)]",
  },
];

export default function FeaturesSection() {
  return (
    <section id="features" className="py-20 px-6 max-w-7xl mx-auto">
      <div className="text-center space-y-4 mb-16">
        <span className="text-xs uppercase font-bold tracking-wider px-3.5 py-1 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
          Advanced Capabilities
        </span>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
          How AetherPravah protects your capital
        </h2>
        <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
          Six synchronized intelligence engines working in unison to ensure your business maintains liquidity, escapes tax traps, and never runs out of runway.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURES.map((feature, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: idx * 0.1 }}
            className={`p-7 rounded-2xl glass-card border border-panelborder transition-all duration-300 ${feature.glowColor} flex flex-col justify-between group`}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="p-3 rounded-xl bg-black/50 border border-panelborder group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mono">
                  {feature.tag}
                </span>
              </div>
              <h3 className="text-xl font-bold text-white tracking-tight leading-snug">
                {feature.title}
              </h3>
              <p className="text-sm text-slate-300 font-normal leading-[1.65]">
                {feature.description}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-panelborder/60">
              <span className="text-xs font-semibold text-brand-400 flex items-center gap-1.5">
                <span>✦</span>
                <span>{feature.benefit}</span>
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
