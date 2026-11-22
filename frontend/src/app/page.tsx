"use client";

import React, { useState, useEffect } from "react";
import ExecutiveDeck from "@/components/ui/ExecutiveDeck";
import LoginPage, { UserAuthData } from "@/components/ui/LoginPage";
import CustomCursor from "@/components/ui/CustomCursor";

export default function Home() {
  const [user, setUser] = useState<UserAuthData | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("aether_user");
      if (saved) {
        setUser(JSON.parse(saved));
      }
    } catch {
      localStorage.removeItem("aether_user");
    } finally {
      setIsReady(true);
    }
  }, []);

  const handleLogin = (userData: UserAuthData) => {
    setUser(userData);
    try {
      localStorage.setItem("aether_user", JSON.stringify(userData));
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogout = () => {
    setUser(null);
    try {
      localStorage.removeItem("aether_user");
    } catch (e) {
      console.error(e);
    }
  };

  if (!isReady) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#070b14] text-slate-100 relative selection:bg-brand-500/30 selection:text-white overflow-hidden">
      {/* Interactive Custom Cursor */}
      <CustomCursor />

      {!user ? (
        <LoginPage onLogin={handleLogin} />
      ) : (
        <ExecutiveDeck user={user} onLogout={handleLogout} />
      )}
    </main>
  );
}
