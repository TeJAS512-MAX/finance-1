"use client";

import React from "react";
import ExecutiveDeck from "@/components/ui/ExecutiveDeck";
import CustomCursor from "@/components/ui/CustomCursor";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#070b14] text-slate-100 relative selection:bg-brand-500/30 selection:text-white overflow-hidden">
      {/* Interactive Custom Cursor */}
      <CustomCursor />

      {/* Advanced Executive Financial Command Deck */}
      <ExecutiveDeck />
    </main>
  );
}
