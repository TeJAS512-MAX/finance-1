import { BusinessState, GSTSingularity, LiquidityWormhole } from "./types";

const BACKEND_URL = "http://localhost:8000";

export interface BackendStateResponse {
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

export interface ChatResponse {
  plain_language_summary: string;
  exact_numbers: string;
  causal_explanation: string;
  top_recommended_actions: string[];
  what_if_ignore: string;
  state?: BusinessState;
  singularity?: GSTSingularity;
  wormhole?: LiquidityWormhole;
}

// 1. Fetch current live state from Central Nervous System
export async function fetchStateApi(): Promise<BackendStateResponse> {
  const res = await fetch(`${BACKEND_URL}/api/state`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch state: ${res.statusText}`);
  }
  const data: BackendStateResponse = await res.json();

  // Also fetch dynamic candidates
  try {
    const cRes = await fetch(`${BACKEND_URL}/api/wormholes/candidates`, { cache: "no-store" });
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
  const res = await fetch(`${BACKEND_URL}/api/chat`, {
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
  const res = await fetch(`${BACKEND_URL}/api/archetype/${archetypeId}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Switch archetype error: ${res.statusText}`);
  }
  const data = await res.json();
  try {
    const cRes = await fetch(`${BACKEND_URL}/api/wormholes/candidates`, { cache: "no-store" });
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
  const res = await fetch(`${BACKEND_URL}/api/wormhole/activate`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Activate wormhole error: ${res.statusText}`);
  }
  return await res.json();
}

// 5. Simulate customer delay dynamically
export async function simulateDelayApi(): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/api/simulate-delay`, {
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

  const res = await fetch(`${BACKEND_URL}/api/upload-invoice`, {
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
  const res = await fetch(`${BACKEND_URL}/api/counterfactual`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Counterfactual error: ${res.statusText}`);
  }
  return await res.json();
}
