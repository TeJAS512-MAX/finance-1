"use client";

import React from "react";
import { Activity, Sparkles } from "lucide-react";
import AudioController, { playUiSound } from "./AudioController";

export default function Navbar({
  onLaunchOrganism,
}: {
  onLaunchOrganism: () => void;
}) {
  return (
    <nav className="sticky top-0 z-40 h-20 border-b border-panelborder bg-darkbg/90 backdrop-blur-xl px-6 flex items-center justify-between">
      {/* Brand Logo & Name */}
      <div className="flex items-center gap-3.5">
        <div className="h-11 w-11 rounded-xl bg-gradient-to-tr from-brand-600 via-accentcyan to-accentpurple p-0.5 shadow-lg shadow-brand-500/20 flex items-center justify-center shrink-0">
          <div className="w-full h-full bg-darkbg rounded-[10px] flex items-center justify-center">
            <Activity className="w-5 h-5 text-accentcyan animate-pulse" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-2xl md:text-[28px] tracking-tight bg-gradient-to-r from-white via-slate-100 to-accentcyan bg-clip-text text-transparent leading-none">
              AetherPravah
            </span>
            <span className="hidden sm:inline text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              v3.8
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium hidden md:block">
            Build AI that handles money better
          </p>
        </div>
      </div>

      {/* Nav Links */}
      <div className="hidden lg:flex items-center gap-8 text-sm font-medium text-slate-300">
        <a
          href="#living-organism"
          onClick={() => playUiSound("click")}
          className="hover:text-white transition"
        >
          Living Organism
        </a>
        <a
          href="#features"
          onClick={() => playUiSound("click")}
          className="hover:text-white transition"
        >
          Features
        </a>
        <a
          href="#architecture"
          onClick={() => playUiSound("click")}
          className="hover:text-white transition"
        >
          Agent Society
        </a>
        <a
          href="#how-it-works"
          onClick={() => playUiSound("click")}
          className="hover:text-white transition"
        >
          How It Works
        </a>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <AudioController />

        <a
          href="https://github.com/TeJAS512-MAX/finance-1"
          target="_blank"
          rel="noopener noreferrer"
          title="View GitHub Repository"
          onClick={() => playUiSound("click")}
          className="p-2.5 rounded-xl glass-card hover:bg-slate-800 border border-panelborder text-slate-300 hover:text-white transition hidden sm:flex items-center gap-1.5 text-xs font-medium"
        >
          <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          <span className="hidden xl:inline">GitHub</span>
        </a>

        <button
          onClick={() => {
            playUiSound("click");
            onLaunchOrganism();
          }}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-accentcyan hover:from-brand-500 hover:to-accentcyan text-white font-semibold text-sm shadow-md shadow-brand-500/20 transition flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          <span>Launch Organism</span>
        </button>
      </div>
    </nav>
  );
}
