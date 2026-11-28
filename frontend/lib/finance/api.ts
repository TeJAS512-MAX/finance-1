import { FINANCE_API_BASE } from "@/lib/config";
import {
  BusinessState,
  GSTSingularity,
  LiquidityWormhole,
  ForecastResponse,
  GstPlanResponse,
  LedgerResponse,
  EmiResponse,
  GstCalcResponse,
  ProfitModelResponse,
} from "./types";

const BACKEND_URL = FINANCE_API_BASE;

export interface BackendStateResponse {
  current_date?: string;
  state: BusinessState;
  singularity: GSTSingularity;
  graph: {
    nodes: Array<{
      id: string;
      label: string;
      type: string;
      value: number;
      properties: Record<string, unknown>;
      x: number;
      y: number;
      charge: number;
    }>;
    edges: Array<{
      source: string;
      target: string;
      relation: string;
      weight: number;
      viscosity_days: number;
      is_counterfactual: boolean;
    }>;
  };
  candidates?: LiquidityWormhole[];
}

export interface ChatCardItem {
  type: "kpis" | "verdict" | "table" | "draft" | string;
  tone?: "good" | "bad" | "warning" | "neutral";
  title?: string;
  text?: string;
  items?: Array<{ label: string; value: string; tone?: string }>;
  headers?: string[];
  rows?: string[][];
  customer?: string;
  invoice?: string;
  amount?: string;
  subject?: string;
  message?: string;
  whatsapp_text?: string;
}

export interface ChatResponse {
  plain_language_summary: string;
  exact_numbers: string;
  causal_explanation: string;
  top_recommended_actions: string[];
  what_if_ignore: string;
  cards?: ChatCardItem[];
  kpis?: Record<string, string>;
  open_tool?: { tab: string; params?: Record<string, unknown> };
  suggestions?: string[];
  state?: BusinessState;
  singularity?: GSTSingularity;
  wormhole?: LiquidityWormhole;
}

// 1. Fetch current live state from Central Nervous System
export async function fetchStateApi(): Promise<BackendStateResponse> {
  const res = await fetch(`${BACKEND_URL}/state`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch state: ${res.statusText}`);
  }
  const data: BackendStateResponse = await res.json();

  // Also fetch dynamic candidates
  try {
    const cRes = await fetch(`${BACKEND_URL}/wormholes/candidates`, { cache: "no-store" });
    if (cRes.ok) {
      const cData = await cRes.json();
      data.candidates = cData.candidates || [];
    }
  } catch {
    data.candidates = [];
  }

  return data;
}

// 2. Real dynamic chat with Central Nervous System
export async function sendChatMessageApi(message: string): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    throw new Error(`Chat API error (${res.status}): ${await res.text()}`);
  }
  return await res.json();
}

// 3. Switch business archetype dynamically
export async function switchArchetypeApi(archetypeId: string): Promise<BackendStateResponse> {
  const res = await fetch(`${BACKEND_URL}/archetype/${archetypeId}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Switch archetype error: ${res.statusText}`);
  }
  const data = await res.json();
  try {
    const cRes = await fetch(`${BACKEND_URL}/wormholes/candidates`, { cache: "no-store" });
    if (cRes.ok) {
      const cData = await cRes.json();
      data.candidates = cData.candidates || [];
    }
  } catch {
    data.candidates = [];
  }
  return data;
}

// 4. Activate Liquidity Wormhole in the live causal substrate
export async function activateWormholeApi(): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/wormhole/activate`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Activate wormhole error: ${res.statusText}`);
  }
  return await res.json();
}

// 5. Simulate customer delay dynamically
export async function simulateDelayApi(): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/simulate-delay`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Simulate delay error: ${res.statusText}`);
  }
  return await res.json();
}

// 6. Upload real invoice document (PDF / Image) for vision OCR
export async function uploadInvoiceApi(file: File): Promise<ChatResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_URL}/upload-invoice`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Invoice upload error: ${res.statusText}`);
  }
  return await res.json();
}

// 7. Get Pearlian Counterfactual Simulation trajectories
export async function fetchCounterfactualApi(): Promise<unknown> {
  const res = await fetch(`${BACKEND_URL}/counterfactual`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Counterfactual error: ${res.statusText}`);
  }
  return await res.json();
}

export interface UserProfileData {
  company_name: string;
  owner_name?: string;
  business_type?: string;
  city?: string;
  gstin?: string;
  bank_cash?: number;
  tax_vault?: number;
  monthly_burn?: number;
}

export async function saveProfileApi(profile: UserProfileData): Promise<BackendStateResponse> {
  const res = await fetch(`${BACKEND_URL}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(`Save profile error: ${res.statusText}`);
  return await res.json();
}

export async function getProfileApi(): Promise<{
  business: {
    id: string;
    name: string;
    owner_name: string;
    archetype: string;
    city: string;
    gstin: string;
  };
  bank_cash: number;
  tax_vault: number;
  runway: number;
}> {
  const res = await fetch(`${BACKEND_URL}/profile`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Get profile error: ${res.statusText}`);
  return await res.json();
}

// 8. Fetch 45-day Cash Flow Forecast & What-If
export async function fetchForecastApi(params?: {
  delay_days?: number;
  discount_pct?: number;
  expense_cut_pct?: number;
  planned_spend?: number;
  spend_day?: number;
}): Promise<ForecastResponse> {
  const q = new URLSearchParams();
  if (params?.delay_days !== undefined) q.set("delay", String(params.delay_days));
  if (params?.discount_pct !== undefined) q.set("discount", String(params.discount_pct));
  if (params?.expense_cut_pct !== undefined) q.set("cost_cut", String(params.expense_cut_pct));
  if (params?.planned_spend !== undefined) q.set("spend", String(params.planned_spend));
  if (params?.spend_day !== undefined) q.set("spend_day", String(params.spend_day));

  const res = await fetch(`${BACKEND_URL}/forecast?${q.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Forecast error: ${res.statusText}`);
  return await res.json();
}

// 9. Fetch GST & Tax Planner
export async function fetchGstPlanApi(): Promise<GstPlanResponse> {
  const res = await fetch(`${BACKEND_URL}/gst-plan`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GST Plan error: ${res.statusText}`);
  return await res.json();
}

// 10. Fetch Debtors & Creditors Ledger
export async function fetchLedgerApi(): Promise<LedgerResponse> {
  const res = await fetch(`${BACKEND_URL}/ledger`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Ledger error: ${res.statusText}`);
  return await res.json();
}

// 11. Fetch Loan EMI Calculation
export async function fetchEmiApi(principal: number, rateAnnual: number, tenureMonths: number): Promise<EmiResponse> {
  const res = await fetch(
    `${BACKEND_URL}/emi?principal=${principal}&rate=${rateAnnual}&months=${tenureMonths}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`EMI error: ${res.statusText}`);
  return await res.json();
}

// 12. Fetch GST Calculator
export async function fetchGstCalcApi(amount: number, rate: number, mode: "gross" | "net"): Promise<GstCalcResponse> {
  const res = await fetch(
    `${BACKEND_URL}/gst-calc?amount=${amount}&rate=${rate}&inclusive=${mode === "gross"}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`GST calc error: ${res.statusText}`);
  return await res.json();
}

// 13. Fetch Profit & Business Model
export async function fetchProfitModelApi(sales: number, cogsPct: number, fixedCosts: number, emi: number): Promise<ProfitModelResponse> {
  const res = await fetch(
    `${BACKEND_URL}/profit-model?monthly_sales=${sales}&cogs_pct=${cogsPct}&running_costs=${fixedCosts}&emis=${emi}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Profit model error: ${res.statusText}`);
  return await res.json();
}


export async function resetProfileApi(): Promise<BackendStateResponse> {
  const res = await fetch(`${BACKEND_URL}/profile/reset`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Reset profile error: ${res.statusText}`);
  return await res.json();
}

export async function fetchReminderApi(invoiceId: string): Promise<{
  reminder: {
    invoice_number: string;
    customer_name: string;
    amount: number;
    days_overdue: number;
    subject: string;
    message: string;
    channel: string;
    tone: string;
  };
}> {
  const res = await fetch(`${BACKEND_URL}/reminder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
  if (!res.ok) throw new Error(`Reminder error: ${res.statusText}`);
  return await res.json();
}
