export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_AETHER_API_URL ||
  "http://127.0.0.1:8000";

export const FINANCE_API_BASE = `${API_BASE}/api/v1/finance`;
