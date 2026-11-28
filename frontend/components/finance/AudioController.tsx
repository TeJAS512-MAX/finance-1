"use client";

import React, { useState, useRef } from "react";
import { Volume2, VolumeX } from "lucide-react";

export function playUiSound(type: "click" | "wormhole" | "alert" | "success") {
  if (typeof window === "undefined") return;
  try {
    const AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext;
    const ctx = new AudioContext();

    if (type === "click") {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.06);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    } else if (type === "wormhole") {
      // Futuristic teleportation whoosh
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(150, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 0.8);
      osc.frequency.exponentialRampToValueAtTime(220, ctx.currentTime + 1.4);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.4);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 1.4);
    } else if (type === "success") {
      // Harmonic chord
      [523.25, 659.25, 783.99, 1046.5].forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.06);
        gain.gain.setValueAtTime(0.06, ctx.currentTime + idx * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + idx * 0.06);
        osc.stop(ctx.currentTime + 0.7);
      });
    } else if (type === "alert") {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.setValueAtTime(330, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    }
  } catch {
    // Audio context not allowed or unsupported
  }
}

export default function AudioController() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const droneOscRef = useRef<OscillatorNode | null>(null);

  const toggleSound = () => {
    if (!isPlaying) {
      try {
        const AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext;
        const ctx = new AudioContext();
        audioContextRef.current = ctx;

        // Subtle organic financial organism ambient drone
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(55, ctx.currentTime); // Low A hum
        gain.gain.setValueAtTime(0.015, ctx.currentTime);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        droneOscRef.current = osc;

        setIsPlaying(true);
        playUiSound("click");
      } catch {
        setIsPlaying(false);
      }
    } else {
      if (droneOscRef.current) {
        try {
          droneOscRef.current.stop();
        } catch {}
      }
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close();
        } catch {}
      }
      setIsPlaying(false);
    }
  };

  return (
    <button
      onClick={toggleSound}
      title={isPlaying ? "Mute Organism Sound" : "Enable Organism Audio"}
      className="p-2.5 rounded-xl glass-card hover:bg-slate-800/80 border border-panelborder text-slate-400 hover:text-white transition flex items-center gap-2 text-xs font-medium"
    >
      {isPlaying ? (
        <>
          <Volume2 className="w-4 h-4 text-brand-500 animate-pulse" />
          <span className="hidden sm:inline text-brand-400">Audio Active</span>
        </>
      ) : (
        <>
          <VolumeX className="w-4 h-4 text-slate-500" />
          <span className="hidden sm:inline text-slate-400">Audio Muted</span>
        </>
      )}
    </button>
  );
}
