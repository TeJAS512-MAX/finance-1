"use client";

import React, { useState } from "react";
import {
  Eye,
  Users,
  Scale,
  Award,
  Dna,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";

interface LayerDetail {
  id: string;
  name: string;
  tier: string;
  icon: React.ReactNode;
  description: string;
  agents: string[];
  proof: string;
}

const TIERS: LayerDetail[] = [
  {
    id: "tier-0",
    name: "Active Sensor Swarm",
    tier: "Tier 0",
    icon: <Eye className="w-5 h-5 text-accentcyan" />,
    description:
      "Multimodal intake layer extracting structured invoices, bank feeds, payment advice, and director voice notes with Bayesian confidence calibration.",
    agents: ["Vision OCR Sensor", "Bank Statement Ingest", "Voice Note Acoustic Parser", "Intent Categorizer"],
    proof: "Confidence threshold >= 0.85 calibrated against historical error margins.",
  },
  {
    id: "tier-1",
    name: "Specialist Agent Swarm",
    tier: "Tier 1",
    icon: <Users className="w-5 h-5 text-brand-500" />,
    description:
      "Domain-specific micro-agents executing continuous checks across GSTR-3B accruals, collection psychology, and vendor input tax credits.",
    agents: ["InvoiceForge Specialist", "GST Accrual Guardian", "Collection Psychologist", "Tax Vault Keeper"],
    proof: "Tracks net GST cash due vs unpaid invoice tax liabilities at minute-level resolution.",
  },
  {
    id: "tier-2",
    name: "Adversarial Debate Parliament",
    tier: "Tier 2",
    icon: <Scale className="w-5 h-5 text-warningamber" />,
    description:
      "Five autonomous cognitive agents debate every major financial intervention from contrasting perspectives to eliminate blind spots.",
    agents: ["Optimist Agent", "Pessimist Agent", "Risk Officer", "Causal Purist", "Behavioral Economist"],
    proof: "Debates require multi-agent quorum before proposing any Liquidity Wormhole.",
  },
  {
    id: "tier-3",
    name: "Constitutional Supreme Court",
    tier: "Tier 3",
    icon: <Award className="w-5 h-5 text-dangerrose" />,
    description:
      "Formal symbolic math verifier. Evaluates every proposal against constitutional financial laws and statutory CGST Section 39 compliance.",
    agents: ["Symbolic Math Verifier", "Runway Guard (21-Day Minimum)", "Paper-Trading Sandbox Auditor"],
    proof: "Rejects any action that breaches minimum 21 days runway or violates rupee conservation.",
  },
  {
    id: "tier-4",
    name: "Meta-Evolution Chamber",
    tier: "Tier 4",
    icon: <Dna className="w-5 h-5 text-accentpurple" />,
    description:
      "Self-model and introspection layer that audits past forecasting variance and refines prompt genomes across customer behavior models.",
    agents: ["Self-Model Introspection", "Genome Mutator", "Episodic Error Tracer"],
    proof: "Continuous Bayesian drift correction improving delay forecasts month-over-month.",
  },
];

export default function ArchitectureSection() {
  const [selectedTier, setSelectedTier] = useState<LayerDetail>(TIERS[2]);

  return (
    <section id="architecture" className="py-20 px-6 max-w-7xl mx-auto">
      <div className="text-center space-y-4 mb-16">
        <span className="text-xs uppercase font-bold tracking-wider px-3.5 py-1 rounded-full bg-accentcyan/10 text-accentcyan border border-accentcyan/20">
          Cognitive Hierarchy
        </span>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
          The 5-Tier Agent Society & Causal Substrate
        </h2>
        <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
          Not a single LLM prompt. AetherPravah is a structured society of 30+ specialized agents bounded by formal mathematical proofs.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Tier Selector Buttons (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          {TIERS.map((tier) => (
            <button
              key={tier.id}
              onClick={() => setSelectedTier(tier)}
              className={`w-full p-4 rounded-2xl glass-card border transition-all duration-200 text-left flex items-center justify-between ${
                selectedTier.id === tier.id
                  ? "border-accentcyan/60 bg-accentcyan/10 shadow-lg shadow-accentcyan/10"
                  : "border-panelborder hover:border-slate-600 hover:bg-slate-800/40"
              }`}
            >
              <div className="flex items-center gap-3.5">
                <div className="p-2.5 rounded-xl bg-black/60 border border-panelborder">
                  {tier.icon}
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mono block">
                    {tier.tier}
                  </span>
                  <span className="text-base font-bold text-white tracking-tight">
                    {tier.name}
                  </span>
                </div>
              </div>
              <ChevronRight
                className={`w-5 h-5 transition-transform ${
                  selectedTier.id === tier.id ? "text-accentcyan translate-x-1" : "text-slate-500"
                }`}
              />
            </button>
          ))}
        </div>

        {/* Selected Tier Deep-Dive Card (7 cols) */}
        <div className="lg:col-span-7 p-8 rounded-3xl glass-panel border border-panelborder bg-darkerbg shadow-2xl space-y-6">
          <div className="flex items-center justify-between border-b border-panelborder pb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-black/60 border border-panelborder">
                {selectedTier.icon}
              </div>
              <div>
                <span className="text-xs font-semibold text-accentcyan mono uppercase tracking-wider">
                  {selectedTier.tier} Architecture
                </span>
                <h3 className="text-2xl font-bold text-white tracking-tight">
                  {selectedTier.name}
                </h3>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-400 text-xs font-medium">
              Active in Organism
            </span>
          </div>

          <p className="text-base text-slate-300 font-normal leading-relaxed">
            {selectedTier.description}
          </p>

          <div className="space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Specialist Agent Roster:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {selectedTier.agents.map((ag, aIdx) => (
                <div
                  key={aIdx}
                  className="p-3 rounded-xl bg-black/40 border border-panelborder flex items-center gap-2.5 text-xs font-medium text-slate-200"
                >
                  <CheckCircle2 className="w-4 h-4 text-brand-500 shrink-0" />
                  <span>{ag}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/20 text-xs text-slate-300 space-y-1">
            <span className="font-bold text-brand-400 block uppercase tracking-wide">
              Formal Symbolic Guarantee:
            </span>
            <p className="font-normal text-slate-300 leading-relaxed">
              {selectedTier.proof}
            </p>
          </div>
        </div>

      </div>
    </section>
  );
}
