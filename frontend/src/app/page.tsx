"use client";

import React, { useRef } from "react";
import Navbar from "@/components/ui/Navbar";
import HeroSection from "@/components/ui/HeroSection";
import LivingAppExperience from "@/components/ui/LivingAppExperience";
import FeaturesSection from "@/components/ui/FeaturesSection";
import ArchitectureSection from "@/components/ui/ArchitectureSection";
import HowItWorksTimeline from "@/components/ui/HowItWorksTimeline";
import FooterSection from "@/components/ui/FooterSection";
import CustomCursor from "@/components/ui/CustomCursor";

export default function Home() {
  const livingOrganismRef = useRef<HTMLDivElement>(null);

  const scrollToOrganism = () => {
    const el = document.getElementById("living-organism");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <main className="min-h-screen bg-darkbg text-slate-100 relative selection:bg-brand-500/30 selection:text-white overflow-x-hidden">
      {/* Interactive Custom Cursor */}
      <CustomCursor />

      {/* Top Sticky Navigation */}
      <Navbar onLaunchOrganism={scrollToOrganism} />

      {/* 3D Hero Section */}
      <HeroSection onEnterOrganism={scrollToOrganism} />

      {/* Main Living Organism Application Experience */}
      <div ref={livingOrganismRef}>
        <LivingAppExperience />
      </div>

      {/* Innovation Features */}
      <FeaturesSection />

      {/* 5-Tier Agent Society & Causal Substrate */}
      <ArchitectureSection />

      {/* Autonomous Lifecycle Timeline */}
      <HowItWorksTimeline />

      {/* Footer & Statutory Disclaimers */}
      <FooterSection />
    </main>
  );
}
