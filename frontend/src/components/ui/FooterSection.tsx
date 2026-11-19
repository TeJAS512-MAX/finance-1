"use client";

import React from "react";
import { Activity, ShieldCheck } from "lucide-react";

export default function FooterSection() {
  return (
    <footer className="border-t border-panelborder bg-darkerbg text-slate-400 py-12 px-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-accentcyan flex items-center justify-center">
                <Activity className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-xl text-white tracking-tight">
                AetherPravah
              </span>
            </div>
            <p className="text-xs md:text-sm text-slate-400 font-medium">
              “The AI that treats your money like a living organism and never lets it die.”
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs md:text-sm font-medium">
            <div className="flex items-center gap-1.5 text-brand-400 bg-brand-500/10 border border-brand-500/20 px-3 py-1.5 rounded-full">
              <ShieldCheck className="w-4 h-4" />
              <span>Strict Rupee Conservation Verified</span>
            </div>
            <div className="flex items-center gap-1.5 text-accentcyan bg-accentcyan/10 border border-accentcyan/20 px-3 py-1.5 rounded-full">
              <span>Pearlian do-calculus Engine</span>
            </div>
          </div>
        </div>

        {/* Legal Statutory Disclaimer: 12px desktop, 11px mobile, Regular 400, muted color */}
        <div className="pt-6 border-t border-panelborder/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-normal text-slate-500">
          <p>
            © 2026 AetherPravah AI. Built for Indian MSMEs facing the GST Accrual Trap.
          </p>
          <p className="text-center sm:text-right max-w-xl text-[11px] md:text-xs">
            Paper-trading simulation environment. Designed for compliance with the Central Goods and Services Tax (CGST) Act, 2017 Section 39. Not statutory tax or legal counsel.
          </p>
        </div>
      </div>
    </footer>
  );
}
