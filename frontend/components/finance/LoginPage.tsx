"use client";

import React, { useState } from "react";
import {
  Building2,
  Lock,
  Mail,
  User,
  MapPin,
  FileText,
  Wallet,
  ArrowRight,
  Eye,
  EyeOff,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  Landmark,
  Zap,
  CheckCircle2,
  AlertCircle
} from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_AETHER_API_URL || "http://127.0.0.1:8000";
const BACKEND_URL = `${API_BASE}/api/v1/finance`;

export interface UserAuthData {
  name: string;
  email: string;
  company_name: string;
  business_type?: string;
  city?: string;
  gstin?: string;
  token?: string;
}

interface LoginPageProps {
  onLogin: (user: UserAuthData) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [activeTab, setActiveTab] = useState<"signin" | "register">("signin");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sign In Form State
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register Form State
  const [regName, setRegName] = useState("");
  const [regCompany, setRegCompany] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regType, setRegType] = useState("Trading & Distribution");
  const [regCity, setRegCity] = useState("Mumbai, Maharashtra");
  const [regGstin, setRegGstin] = useState("27AAACU1234M1Z5");
  const [regBankCash, setRegBankCash] = useState(350000);

  // 1-Click Demo Login
  const handleDemoLogin = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${BACKEND_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "demo@aetherpravah.com", password: "password123" })
      });
      if (res.ok) {
        const data = await res.json();
        onLogin(data.user);
      } else {
        // Fallback demo user if API unreachable
        onLogin({
          name: "Rajesh Sharma",
          email: "demo@aetherpravah.com",
          company_name: "Apex Solutions Enterprise",
          business_type: "Trading & Services",
          city: "Mumbai, Maharashtra",
          gstin: "27AAACU1234M1Z5"
        });
      }
    } catch {
      onLogin({
        name: "Rajesh Sharma",
        email: "demo@aetherpravah.com",
        company_name: "Apex Solutions Enterprise",
        business_type: "Trading & Services",
        city: "Mumbai, Maharashtra",
        gstin: "27AAACU1234M1Z5"
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Standard Sign In
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim()) {
      setErrorMsg("Please enter your email or username");
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${BACKEND_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword || "password123" })
      });
      if (res.ok) {
        const data = await res.json();
        onLogin(data.user);
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || "Authentication failed. Please verify credentials.");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Connection failed";
      setErrorMsg(`Connection error: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Register
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regCompany.trim() || !regEmail.trim()) {
      setErrorMsg("Please fill in all required profile fields");
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${BACKEND_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: regName,
          email: regEmail,
          password: regPassword || "pass123",
          company_name: regCompany,
          business_type: regType,
          city: regCity,
          gstin: regGstin,
          bank_cash: regBankCash,
          tax_vault: 25000,
          monthly_burn: 80000
        })
      });
      if (res.ok) {
        const data = await res.json();
        onLogin(data.user);
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || "Registration failed");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Connection failed";
      setErrorMsg(`Connection error: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] flex items-center justify-center p-4 sm:p-6 lg:p-8 relative selection:bg-brand-500/30 selection:text-white overflow-hidden">
      
      {/* Background Ambient Glows */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-accentcyan/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Container Card */}
      <div className="w-full max-w-5xl bg-slate-900/80 border border-slate-800/80 rounded-3xl shadow-2xl backdrop-blur-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 z-10">
        
        {/* LEFT COLUMN: BRANDING & PRODUCT HIGHLIGHTS (5 cols) */}
        <div className="lg:col-span-5 p-8 lg:p-10 bg-gradient-to-b from-slate-900 via-slate-950 to-[#070b14] border-b lg:border-b-0 lg:border-r border-slate-800/80 flex flex-col justify-between">
          <div className="space-y-6">
            
            {/* Logo & Platform Name */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-brand-500 to-accentcyan flex items-center justify-center font-bold text-white text-base shadow-lg shadow-brand-500/20">
                AP
              </div>
              <div>
                <span className="font-bold text-white text-lg tracking-tight block">
                  AetherPravah
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  Conversational AI Financial Twin
                </span>
              </div>
            </div>

            {/* Headline */}
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-snug">
                Smart Financial Intelligence for Your Business
              </h1>
              <p className="mt-2 text-xs sm:text-sm text-slate-400 leading-relaxed">
                Connect your business finances to a conversational AI assistant. Track cash runway, predict GST liabilities, and manage debtor collections in plain English.
              </p>
            </div>

            {/* 4 Feature Highlights */}
            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/60">
                <div className="p-2 rounded-lg bg-brand-500/15 text-brand-400 shrink-0">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">Conversational Assistant</h4>
                  <p className="text-[11px] text-slate-400">Add invoices, log bills, and record payments directly via chat.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/60">
                <div className="p-2 rounded-lg bg-dangerrose/15 text-dangerrose shrink-0">
                  <Landmark className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">GST 2.0 & Section 39 Radar</h4>
                  <p className="text-[11px] text-slate-400">Track accrued tax liabilities so you never face cash shortages on the 20th.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/60">
                <div className="p-2 rounded-lg bg-accentcyan/15 text-accentcyan shrink-0">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">30-Day Cash Flow What-If</h4>
                  <p className="text-[11px] text-slate-400">Simulate customer payment delays and capex affordability before spending.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/60">
                <div className="p-2 rounded-lg bg-purple-500/15 text-purple-400 shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">Rupee Conservation Engine</h4>
                  <p className="text-[11px] text-slate-400">100% mathematical precision with zero financial leakage across accounts.</p>
                </div>
              </div>
            </div>

          </div>

          {/* Bottom Security Badge */}
          <div className="pt-6 border-t border-slate-800/60 flex items-center gap-2 text-[11px] text-slate-500 font-mono">
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
            <span>Strict Rupee Conservation • MSME Compliant</span>
          </div>
        </div>

        {/* RIGHT COLUMN: AUTHENTICATION FORMS (7 cols) */}
        <div className="lg:col-span-7 p-8 lg:p-10 flex flex-col justify-center bg-slate-950/60">
          
          {/* Top Form Header & Tabs */}
          <div className="space-y-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {activeTab === "signin" ? "Sign In to Your Business" : "Create Business Profile"}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {activeTab === "signin"
                    ? "Enter your credentials to access your financial twin"
                    : "Set up your company parameters and launch your AI twin"}
                </p>
              </div>

              {/* 1-Click Demo Shortcut */}
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isLoading}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-500/15 hover:bg-brand-500/25 text-brand-300 border border-brand-500/30 text-xs font-semibold transition"
                title="Instant access with pre-configured company"
              >
                <Zap className="w-3.5 h-3.5 fill-current" />
                <span>1-Click Demo</span>
              </button>
            </div>

            {/* Tab Switcher Pills */}
            <div className="grid grid-cols-2 p-1 rounded-2xl bg-slate-900 border border-slate-800 text-xs">
              <button
                type="button"
                onClick={() => { setActiveTab("signin"); setErrorMsg(null); }}
                className={`py-2 rounded-xl font-semibold transition flex items-center justify-center gap-1.5 ${
                  activeTab === "signin"
                    ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
              <button
                type="button"
                onClick={() => { setActiveTab("register"); setErrorMsg(null); }}
                className={`py-2 rounded-xl font-semibold transition flex items-center justify-center gap-1.5 ${
                  activeTab === "register"
                    ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Register Business</span>
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div className="mb-4 p-3 rounded-xl bg-dangerrose/10 border border-dangerrose/30 text-dangerrose text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* SIGN IN FORM */}
          {activeTab === "signin" && (
            <form onSubmit={handleSignIn} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">
                  Email Address or Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="e.g. rajesh@apexsolutions.in or demo"
                    className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none transition shadow-inner text-xs sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-slate-300 font-medium">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={handleDemoLogin}
                    className="text-[11px] text-accentcyan hover:underline"
                  >
                    Use demo password?
                  </button>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-10 pr-10 py-2.5 text-white placeholder-slate-500 focus:outline-none transition shadow-inner text-xs sm:text-sm font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs sm:text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 disabled:opacity-50 mt-2"
              >
                {isLoading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Financial Twin</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Mobile 1-Click Demo Shortcut */}
              <div className="pt-3 border-t border-slate-800/80 text-center sm:hidden">
                <button
                  type="button"
                  onClick={handleDemoLogin}
                  className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-brand-400 font-semibold text-xs border border-brand-500/30 flex items-center justify-center gap-1.5 transition"
                >
                  <Zap className="w-3.5 h-3.5 fill-current" />
                  <span>1-Click Instant Demo Access</span>
                </button>
              </div>
            </form>
          )}

          {/* REGISTER BUSINESS FORM */}
          {activeTab === "register" && (
            <form onSubmit={handleRegister} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Owner / Founder Name *</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <User className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="text"
                      required
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      placeholder="e.g. Rahul Sharma"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Company / Business Name *</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Building2 className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="text"
                      required
                      value={regCompany}
                      onChange={(e) => setRegCompany(e.target.value)}
                      placeholder="e.g. Apex Industrial Solutions"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Work Email Address *</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Mail className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="email"
                      required
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="e.g. rahul@apex.in"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Create Password *</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Lock className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-9 py-2 text-white placeholder-slate-500 focus:outline-none font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500"
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Industry / Business Type</label>
                  <select
                    value={regType}
                    onChange={(e) => setRegType(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                  >
                    <option value="Trading & Distribution">Trading & Distribution</option>
                    <option value="Manufacturing & Fabrication">Manufacturing & Fabrication</option>
                    <option value="Garments & Textiles">Garments & Textiles</option>
                    <option value="IT & Digital Services">IT & Digital Services</option>
                    <option value="Logistics & Transport">Logistics & Transport</option>
                    <option value="Retail & E-Commerce">Retail & E-Commerce</option>
                    <option value="Healthcare & Pharma">Healthcare & Pharma</option>
                    <option value="Construction & Infra">Construction & Infra</option>
                    <option value="Consulting & Agency">Consulting & Agency</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">City & State</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <MapPin className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="text"
                      value={regCity}
                      onChange={(e) => setRegCity(e.target.value)}
                      placeholder="e.g. Pune, Maharashtra"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">GSTIN Number (Optional)</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <FileText className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="text"
                      maxLength={15}
                      value={regGstin}
                      onChange={(e) => setRegGstin(e.target.value.toUpperCase())}
                      placeholder="e.g. 27AAACU1234M1Z5"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none font-mono uppercase"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Initial Bank Balance (₹)</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                      <Wallet className="w-3.5 h-3.5" />
                    </div>
                    <input
                      type="number"
                      step={1000}
                      value={regBankCash}
                      onChange={(e) => setRegBankCash(Number(e.target.value))}
                      placeholder="350000"
                      className="w-full bg-slate-900/90 border border-slate-800 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2 text-white placeholder-slate-500 focus:outline-none font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs sm:text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 disabled:opacity-50 mt-1"
              >
                {isLoading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Creating Twin...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Launch AI Financial Twin</span>
                  </>
                )}
              </button>
            </form>
          )}

        </div>

      </div>

    </div>
  );
}
