import { create } from "zustand";
import { ARCHETYPES } from "./mockData";
import { BusinessState, GSTSingularity, LiquidityWormhole } from "./types";
import { playUiSound } from "@/components/ui/AudioController";

export interface Live3DNode {
  id: string;
  label: string;
  sublabel: string;
  type: "CUSTOMER" | "INVOICE" | "BANK" | "VAULT" | "BLACKHOLE" | "OBLIGATION";
  position: [number, number, number];
  color: string;
  emissive: string;
  value: string;
  scale?: number;
}

export interface Live3DEdge {
  id: string;
  from: [number, number, number];
  to: [number, number, number];
  color: string;
  isDrain?: boolean;
}

export interface ChatMessageItem {
  id: string;
  sender: "user" | "ai";
  timestamp: string;
  text: string;
  numbers?: string;
  causalExplanation?: string;
  recommendations?: string[];
  whatIf?: string;
}

interface AetherPravahStore {
  // Business State
  businessKey: string;
  state: BusinessState;
  singularity: GSTSingularity;
  candidates: LiquidityWormhole[];
  selectedCandidateIdx: number;

  // Live 3D World State
  nodes: Live3DNode[];
  edges: Live3DEdge[];
  selectedNodeId: string | null;
  cameraTarget: [number, number, number];
  wormholePhase: "IDLE" | "SYNTHESIZED" | "WARPING" | "EXECUTED";
  isSingularityActive: boolean;

  // Chat State
  messages: ChatMessageItem[];
  isAiThinking: boolean;

  // Actions
  switchBusiness: (key: string) => void;
  selectNode: (id: string | null) => void;
  setCameraTarget: (pos: [number, number, number]) => void;
  setSelectedCandidateIdx: (idx: number) => void;
  createInvoiceLive: (customerName: string, totalAmount: number) => void;
  simulateDelayLive: () => void;
  forgeWormholeLive: () => void;
  executeWormholeLive: () => Promise<void>;
  sendMessageLive: (text: string) => Promise<void>;
}

const INITIAL_NODES: Live3DNode[] = [
  {
    id: "cust-reliance",
    label: "Reliance Infra",
    sublabel: "35d latency",
    type: "CUSTOMER",
    position: [-3.4, 1.8, 0],
    color: "#f59e0b",
    emissive: "#d97706",
    value: "Primary Debtor • 35-day institutional cycle",
    scale: 1,
  },
  {
    id: "cust-lt",
    label: "L&T Fab",
    sublabel: "28d latency",
    type: "CUSTOMER",
    position: [-3.4, -1.2, 0],
    color: "#f59e0b",
    emissive: "#d97706",
    value: "Secondary Debtor • 28-day settlement lag",
    scale: 1,
  },
  {
    id: "inv-1042",
    label: "Inv #1042",
    sublabel: "₹14.75L",
    type: "INVOICE",
    position: [-1.2, 1.5, 0.4],
    color: "#06b6d4",
    emissive: "#0891b2",
    value: "₹14,75,000.00 • Unpaid (Accrual Trap)",
    scale: 1,
  },
  {
    id: "inv-1043",
    label: "Inv #1043",
    sublabel: "₹9.50L",
    type: "INVOICE",
    position: [-1.2, -0.9, 0.4],
    color: "#06b6d4",
    emissive: "#0891b2",
    value: "₹9,50,000.00 • Overdue",
    scale: 1,
  },
  {
    id: "bank-cash",
    label: "Bank Cash",
    sublabel: "₹1.85 Lakhs",
    type: "BANK",
    position: [1.2, 0, 0],
    color: "#10b981",
    emissive: "#059669",
    value: "₹1,85,000.00 liquid reserve",
    scale: 1,
  },
  {
    id: "tax-vault",
    label: "Tax Vault",
    sublabel: "₹35,000",
    type: "VAULT",
    position: [1.2, -2.0, 0.5],
    color: "#22d3ee",
    emissive: "#06b6d4",
    value: "₹35,000 reserved (Deficit: ₹2.49L)",
    scale: 1,
  },
  {
    id: "gst-singularity",
    label: "GST BLACK HOLE",
    sublabel: "₹2.85L (20 Nov)",
    type: "BLACKHOLE",
    position: [2.0, 2.0, 0],
    color: "#f43f5e",
    emissive: "#e11d48",
    value: "Event Horizon: 20 Nov • Deficit: ₹1,52,915",
    scale: 1.3,
  },
  {
    id: "sbi-emi",
    label: "SBI Loan EMI",
    sublabel: "₹88,000",
    type: "OBLIGATION",
    position: [3.5, -0.6, 0.3],
    color: "#8b5cf6",
    emissive: "#7c3aed",
    value: "₹88,000 due 18 Nov • Non-negotiable",
    scale: 1,
  },
];

const INITIAL_EDGES: Live3DEdge[] = [
  { id: "e1", from: [-3.4, 1.8, 0], to: [-1.2, 1.5, 0.4], color: "#f59e0b" },
  { id: "e2", from: [-3.4, -1.2, 0], to: [-1.2, -0.9, 0.4], color: "#f59e0b" },
  { id: "e3", from: [-1.2, 1.5, 0.4], to: [1.2, 0, 0], color: "#06b6d4" },
  { id: "e4", from: [-1.2, -0.9, 0.4], to: [1.2, 0, 0], color: "#06b6d4" },
  { id: "e5", from: [-1.2, 1.5, 0.4], to: [2.0, 2.0, 0], color: "#f43f5e", isDrain: true },
  { id: "e6", from: [-1.2, -0.9, 0.4], to: [2.0, 2.0, 0], color: "#f43f5e", isDrain: true },
  { id: "e7", from: [2.0, 2.0, 0], to: [1.2, 0, 0], color: "#f43f5e", isDrain: true },
  { id: "e8", from: [1.2, 0, 0], to: [1.2, -2.0, 0.5], color: "#22d3ee" },
  { id: "e9", from: [1.2, 0, 0], to: [3.5, -0.6, 0.3], color: "#8b5cf6" },
];

export const useAetherStore = create<AetherPravahStore>((set, get) => ({
  businessKey: "STEEL_TRADER",
  state: ARCHETYPES["STEEL_TRADER"].state,
  singularity: ARCHETYPES["STEEL_TRADER"].singularity,
  candidates: ARCHETYPES["STEEL_TRADER"].candidates,
  selectedCandidateIdx: 0,

  nodes: INITIAL_NODES,
  edges: INITIAL_EDGES,
  selectedNodeId: "gst-singularity",
  cameraTarget: [0, 0, 0],
  wormholePhase: "IDLE",
  isSingularityActive: true,

  messages: [
    {
      id: "init-1",
      sender: "ai",
      timestamp: "12:00 PM",
      text: "Hello! I am actively tracking all **₹30.65 Lakhs** across **Bharat Steel Traders** in real time with zero mathematical leakage.\n\nWhile operations are profitable, an acute **GSTR-3B GST Accrual Singularity** converges on Nov 20th. Unpaid customer bills hold ₹3,69,915 in accrued GST liability that must be settled in cash.",
      numbers: "• Bank Cash: ₹1,85,000.00\n• Net GST Cash Due (20 Nov): ₹2,84,915.00\n• Immediate Deficit at Event Horizon: ₹1,52,915.00",
      causalExplanation: "Section 39 CGST Act requires cash tax settlement before institutional payments clear.",
      recommendations: ["Authorize synthesized Trident Liquidity Wormhole", "Simulate customer settlement delay"],
      whatIf: "Liquidity black hole results in bank account freezing under Garnishee statutory order.",
    },
  ],
  isAiThinking: false,

  switchBusiness: (key: string) => {
    playUiSound("click");
    const data = ARCHETYPES[key] || ARCHETYPES["STEEL_TRADER"];
    set({
      businessKey: key,
      state: data.state,
      singularity: data.singularity,
      candidates: data.candidates,
      selectedCandidateIdx: 0,
      wormholePhase: "IDLE",
      isSingularityActive: true,
      selectedNodeId: "gst-singularity",
      cameraTarget: [0, 0, 0],
    });
  },

  selectNode: (id: string | null) => {
    playUiSound("click");
    const node = get().nodes.find((n) => n.id === id);
    if (node) {
      set({ selectedNodeId: id, cameraTarget: node.position });
    } else {
      set({ selectedNodeId: null, cameraTarget: [0, 0, 0] });
    }
  },

  setCameraTarget: (pos: [number, number, number]) => set({ cameraTarget: pos }),

  setSelectedCandidateIdx: (idx: number) => {
    playUiSound("click");
    set({ selectedCandidateIdx: idx });
  },

  // 1. Create Invoice LIVE: Spawns new 3D node and connects causal vectors
  createInvoiceLive: (customerName: string, totalAmount: number) => {
    playUiSound("click");
    const currentNodes = [...get().nodes];
    const currentEdges = [...get().edges];
    const newInvId = `inv-${Date.now().toString().slice(-4)}`;
    const yPos = currentNodes.length % 2 === 0 ? 0.3 : -0.3;

    // Spawn 3D Node
    const newNode: Live3DNode = {
      id: newInvId,
      label: `Inv #${newInvId.toUpperCase()}`,
      sublabel: `₹${(totalAmount / 100000).toFixed(2)}L`,
      type: "INVOICE",
      position: [-1.2, yPos, 0.8],
      color: "#38bdf8",
      emissive: "#0284c7",
      value: `₹${totalAmount.toLocaleString("en-IN")} • Newly Billed`,
      scale: 1.2,
    };

    // Connect causal vectors: Customer -> Invoice -> GST Black Hole
    const newEdges: Live3DEdge[] = [
      { id: `e-new-cust-${newInvId}`, from: [-3.4, 1.8, 0], to: [-1.2, yPos, 0.8], color: "#f59e0b" },
      { id: `e-new-drain-${newInvId}`, from: [-1.2, yPos, 0.8], to: [2.0, 2.0, 0], color: "#f43f5e", isDrain: true },
    ];

    // Deepen GST Accrual Singularity
    const gstAccrued = totalAmount * 0.1525; // 18% GST portion
    const updatedSingularity = { ...get().singularity };
    updatedSingularity.singularity_depth += gstAccrued;
    updatedSingularity.statutory_tax_demand += gstAccrued;

    const updatedState = { ...get().state };
    updatedState.physics_state.pending_receivables += totalAmount;
    updatedState.physics_state.total_rupees_conserved += totalAmount;
    updatedState.gst_snapshot.net_gst_cash_payable += gstAccrued;

    // Expand GST Black Hole node scale
    const updatedNodes = currentNodes.map((n) => {
      if (n.type === "BLACKHOLE") {
        return {
          ...n,
          scale: (n.scale || 1.3) + 0.15,
          sublabel: `₹${(updatedSingularity.statutory_tax_demand / 100000).toFixed(2)}L (20 Nov)`,
          value: `Deepened Deficit: ₹${updatedSingularity.singularity_depth.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
        };
      }
      return n;
    });

    set({
      nodes: [...updatedNodes, newNode],
      edges: [...currentEdges, ...newEdges],
      singularity: updatedSingularity,
      state: updatedState,
      selectedNodeId: newInvId,
      cameraTarget: [-1.2, yPos, 0.8],
    });

    get().sendMessageLive(`Create invoice for Reliance ₹${(totalAmount / 100000).toFixed(1)} Lakh`);
  },

  // 2. Simulate Delay LIVE: Expands Black Hole distortion in 3D
  simulateDelayLive: () => {
    playUiSound("alert");
    const updatedSingularity = { ...get().singularity };
    updatedSingularity.singularity_depth += 65000;
    updatedSingularity.days_to_event_horizon = Math.max(1, updatedSingularity.days_to_event_horizon - 1);

    const updatedState = { ...get().state };
    updatedState.physics_state.viscosity_index = 4.85;
    updatedState.physics_state.estimated_runway_days = 7.2;
    updatedState.genome.overall_score = Math.max(20, updatedState.genome.overall_score - 8);

    // Expand Black Hole node scale in 3D
    const updatedNodes = get().nodes.map((n) => {
      if (n.type === "BLACKHOLE") {
        return {
          ...n,
          scale: 1.8,
          value: `CRITICAL DRAIN • Deficit: ₹${updatedSingularity.singularity_depth.toLocaleString("en-IN")}`,
        };
      }
      return n;
    });

    set({
      singularity: updatedSingularity,
      state: updatedState,
      nodes: updatedNodes,
      selectedNodeId: "gst-singularity",
      cameraTarget: [2.0, 2.0, 0],
    });

    get().sendMessageLive("Simulate 30-day customer delay across institutional receivables");
  },

  // 3. Forge Wormhole LIVE: Prepares portal
  forgeWormholeLive: () => {
    playUiSound("click");
    set({ wormholePhase: "SYNTHESIZED" });
  },

  // 4. Execute Wormhole LIVE: Warp speed sequence + neutralizes black hole
  executeWormholeLive: async () => {
    playUiSound("wormhole");
    set({ wormholePhase: "WARPING" });

    await new Promise((r) => setTimeout(r, 1200));

    playUiSound("success");
    const resolvedSingularity = {
      ...get().singularity,
      singularity_depth: 0,
      severity: "LOW" as const,
    };

    const updatedState = { ...get().state };
    updatedState.physics_state.bank_cash = 1306085.0;
    updatedState.physics_state.tax_vault_balance = 284915.0;
    updatedState.physics_state.pending_receivables = 1400000.0;
    updatedState.physics_state.viscosity_index = 1.15;
    updatedState.physics_state.estimated_runway_days = 46.5;
    updatedState.genome.overall_score = 96;

    // Neutralize Black Hole in 3D & spawn Wormhole Bridge node
    const updatedNodes = get().nodes.map((n) => {
      if (n.type === "BLACKHOLE") {
        return {
          ...n,
          color: "#10b981",
          emissive: "#059669",
          scale: 0.5,
          label: "TAX SECURED",
          sublabel: "100% Ring-Fenced",
          value: "Singularity Neutralized • Zero GST Default",
        };
      }
      return n;
    });

    // Remove red drain edges
    const updatedEdges = get().edges.map((e) => {
      if (e.isDrain) {
        return { ...e, color: "#10b981", isDrain: false };
      }
      return e;
    });

    set({
      wormholePhase: "EXECUTED",
      isSingularityActive: false,
      singularity: resolvedSingularity,
      state: updatedState,
      nodes: updatedNodes,
      edges: updatedEdges,
      selectedNodeId: "bank-cash",
      cameraTarget: [1.2, 0, 0],
    });

    get().sendMessageLive("Activate Liquidity Wormhole");
  },

  // 5. Send Chat Message LIVE
  sendMessageLive: async (text: string) => {
    if (!text.trim()) return;
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Add user message if not automated
    if (!text.startsWith("Create invoice") && !text.startsWith("Simulate") && !text.startsWith("Activate")) {
      const userMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "user",
        timestamp: now,
        text,
      };
      set({ messages: [...get().messages, userMsg], isAiThinking: true });
    } else {
      set({ isAiThinking: true });
    }

    try {
      const { sendChatMessage } = await import("./api");
      const res = await sendChatMessage(text, get().state, get().singularity);
      set({ isAiThinking: false });

      const aiMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: res.plain_language_summary,
        numbers: res.exact_numbers,
        causalExplanation: res.causal_explanation,
        recommendations: res.top_recommended_actions,
        whatIf: res.what_if_ignore,
      };
      set({ messages: [...get().messages, aiMsg] });
    } catch {
      set({ isAiThinking: false });
    }
  },
}));
