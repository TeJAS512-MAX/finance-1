import { create } from "zustand";
import { ARCHETYPES } from "./mockData";
import {
  fetchStateApi,
  sendChatMessageApi,
  switchArchetypeApi,
  activateWormholeApi,
  simulateDelayApi,
  uploadInvoiceApi,
  saveProfileApi,
  UserProfileData,
  BackendStateResponse,
  ChatResponse,
  ChatCardItem,
} from "./api";
import { BusinessState, GSTSingularity, LiquidityWormhole } from "./types";
import { playUiSound } from "@/components/ui/AudioController";

export interface Live3DNode {
  id: string;
  label: string;
  sublabel: string;
  type: string;
  position: [number, number, number];
  color: string;
  emissive: string;
  value: string;
  rawAmount: number;
  properties: Record<string, unknown>;
  scale?: number;
}

export interface Live3DEdge {
  id: string;
  from: [number, number, number];
  to: [number, number, number];
  color: string;
  relation: string;
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
  cards?: ChatCardItem[];
  suggestions?: string[];
}

interface AetherStoreState {
  // Connection & loading
  isLoaded: boolean;
  isLoading: boolean;
  error: string | null;

  // Active view
  activeView: "radar" | "wormhole" | "simulator";

  // Business state
  businessKey: string;
  state: BusinessState;
  singularity: GSTSingularity;
  candidates: LiquidityWormhole[];
  selectedCandidateIdx: number;

  // 3D Scene graph
  nodes: Live3DNode[];
  edges: Live3DEdge[];
  selectedNodeId: string | null;
  cameraTarget: [number, number, number];

  // Chat
  messages: ChatMessageItem[];
  isThinking: boolean;
  isAiThinking: boolean;
  wormholePhase: "IDLE" | "SYNTHESIZED" | "WARPING" | "EXECUTED";

  // Actions
  init: () => Promise<void>;
  switchBusiness: (archetypeId: string) => Promise<void>;
  selectNode: (id: string | null) => void;
  setActiveView: (view: "radar" | "wormhole" | "simulator") => void;
  setSelectedCandidateIdx: (idx: number) => void;
  sendMessage: (text: string) => Promise<void>;
  sendMessageLive: (text: string) => Promise<void>;
  activateWormhole: () => Promise<void>;
  executeWormholeLive: () => Promise<void>;
  simulateDelay: () => Promise<void>;
  simulateDelayLive: () => Promise<void>;
  createInvoiceLive: (customer: string, amount: number) => Promise<void>;
  uploadInvoice: (file: File) => Promise<void>;
  saveUserProfile: (profile: UserProfileData) => Promise<void>;
}

function processBackendGraph(
  graph: BackendStateResponse["graph"]
): { nodes: Live3DNode[]; edges: Live3DEdge[] } {
  if (!graph || !graph.nodes) return { nodes: [], edges: [] };

  const nodePosMap = new Map<string, [number, number, number]>();

  const nodes: Live3DNode[] = graph.nodes.map((n) => {
    const x3d = (n.x - 370) / 80;
    const y3d = -(n.y - 220) / 70;
    const isLiability = n.type === "TAX_LIABILITY";
    const z3d = isLiability ? 0.2 : (n.type === "INVOICE" ? 0.35 : 0);
    const pos: [number, number, number] = [x3d, y3d, z3d];
    nodePosMap.set(n.id, pos);

    let color = "#38bdf8";
    let emissive = "#0284c7";
    let sublabel = `₹${(n.value / 1000).toFixed(0)}k`;

    if (n.type === "BANK_ACCOUNT") {
      color = "#10b981";
      emissive = "#059669";
      sublabel = `₹${(n.value / 100000).toFixed(2)}L`;
    } else if (n.type === "TAX_VAULT") {
      color = "#22d3ee";
      emissive = "#0891b2";
      sublabel = `₹${(n.value / 1000).toFixed(0)}k`;
    } else if (n.type === "TAX_LIABILITY") {
      color = "#f43f5e";
      emissive = "#e11d48";
      sublabel = `₹${(n.value / 1000).toFixed(0)}k Due 20th`;
    } else if (n.type === "CUSTOMER") {
      color = "#f59e0b";
      emissive = "#d97706";
      sublabel = `${n.properties?.typical_delay || 35}d cycle`;
    } else if (n.type === "LOAN_OBLIGATION") {
      color = "#8b5cf6";
      emissive = "#7c3aed";
      sublabel = `₹${(n.value / 1000).toFixed(0)}k EMI`;
    }

    return {
      id: n.id,
      label: n.label,
      sublabel,
      type: n.type,
      position: pos,
      color,
      emissive,
      value: `₹${n.value.toLocaleString("en-IN")}`,
      rawAmount: n.value,
      properties: n.properties || {},
      scale: isLiability ? 1.35 : 1,
    };
  });

  const edges: Live3DEdge[] = [];
  if (graph.edges) {
    graph.edges.forEach((e, idx) => {
      const fromPos = nodePosMap.get(e.source);
      const toPos = nodePosMap.get(e.target);
      if (fromPos && toPos) {
        const isDrain =
          e.relation === "STATUTORY_GRAVITY_DRAIN" ||
          e.relation === "TRIGGERS_INSTANT_TAX_ACCRUAL";
        let edgeColor = "#06b6d4";
        if (isDrain) edgeColor = "#f43f5e";
        else if (e.relation === "SHIELDS_AND_SATISFIES") edgeColor = "#10b981";
        else if (e.relation === "CONTROLS_PAYMENT_TIMING") edgeColor = "#f59e0b";
        else if (e.relation === "MUST_HONOR_OBLIGATION") edgeColor = "#8b5cf6";

        edges.push({
          id: `e-${idx}-${e.source}-${e.target}`,
          from: fromPos,
          to: toPos,
          color: edgeColor,
          relation: e.relation,
          isDrain,
        });
      }
    });
  }

  return { nodes, edges };
}

export const useAetherStore = create<AetherStoreState>((set, get) => ({
  isLoaded: false,
  isLoading: false,
  error: null,

  activeView: "radar",

  businessKey: "STEEL_TRADER",
  state: ARCHETYPES["STEEL_TRADER"].state,
  singularity: ARCHETYPES["STEEL_TRADER"].singularity,
  candidates: ARCHETYPES["STEEL_TRADER"].candidates,
  selectedCandidateIdx: 0,

  nodes: [],
  edges: [],
  selectedNodeId: "NODE-GST-LIABILITY",
  cameraTarget: [0, 0, 0],

  messages: [],
  isThinking: false,
  isAiThinking: false,
  wormholePhase: "IDLE",

  init: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await fetchStateApi();
      const { nodes, edges } = processBackendGraph(data.graph);
      const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      const welcomeMsg: ChatMessageItem = {
        id: "sys-init",
        sender: "ai",
        timestamp: now,
        text: `The **Central Nervous System** is active for **${data.state.business.name}**.\n\nTracking **₹${(
          data.state.physics_state.total_rupees_conserved / 100000
        ).toFixed(2)} Lakhs** with strict mathematical conservation.\n\n⚠️ **GST Accrual Singularity**: ₹${(
          data.singularity.singularity_depth / 1000
        ).toFixed(1)}k net cash deficit converges on Nov 20th statutory cut-off. Ask me anything about your cash, invoices, or runway.`,
        numbers: `• Bank Cash: ₹${data.state.physics_state.bank_cash.toLocaleString("en-IN")}\n• Net GST Due: ₹${data.state.gst_snapshot.net_gst_cash_payable.toLocaleString("en-IN")}\n• Cash Deficit: ₹${data.singularity.singularity_depth.toLocaleString("en-IN")}`,
        causalExplanation: "CGST Section 39 creates tax liabilities upon bill generation, preceding buyer settlement cycles.",
        recommendations: [
          "Activate Liquidity Wormhole to ring-fence tax",
          "Simulate customer collection delay",
        ],
        whatIf: "Tax default triggers Section 79 bank account attachment and E-way bill freezing.",
      };

      set({
        isLoaded: true,
        isLoading: false,
        state: data.state,
        singularity: data.singularity,
        candidates: data.candidates || [],
        nodes,
        edges,
        messages: [welcomeMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        isLoading: false,
        error: `Could not connect to backend engine: ${msg}`,
      });
    }
  },

  switchBusiness: async (archetypeId: string) => {
    playUiSound("click");
    set({ isLoading: true, error: null });
    try {
      const data = await switchArchetypeApi(archetypeId);
      const { nodes, edges } = processBackendGraph(data.graph);
      const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      const switchMsg: ChatMessageItem = {
        id: `sw-${Date.now()}`,
        sender: "ai",
        timestamp: now,
        text: `Switched operational context to **${data.state.business.name}** (${data.state.business.city}).\n\nTotal conserved capital: ₹${(
          data.state.physics_state.total_rupees_conserved / 100000
        ).toFixed(2)} Lakhs. Viscosity index is currently ${data.state.physics_state.viscosity_index.toFixed(2)}.`,
        numbers: `• Bank Cash: ₹${data.state.physics_state.bank_cash.toLocaleString("en-IN")}\n• Tax Demand: ₹${data.state.gst_snapshot.net_gst_cash_payable.toLocaleString("en-IN")}\n• Runway: ${data.state.physics_state.estimated_runway_days.toFixed(1)} Days`,
      };

      set({
        isLoading: false,
        businessKey: archetypeId,
        state: data.state,
        singularity: data.singularity,
        candidates: data.candidates || [],
        nodes,
        edges,
        selectedCandidateIdx: 0,
        messages: [...get().messages, switchMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: msg });
    }
  },

  saveUserProfile: async (profile: UserProfileData) => {
    playUiSound("click");
    set({ isLoading: true, error: null });
    try {
      const res = await saveProfileApi(profile);
      const { nodes, edges } = processBackendGraph(res.graph);
      const welcomeMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: `Namaste ${profile.owner_name || "Owner"}! I am now tracking **${profile.company_name}** (${profile.city || "India"}).\n\nYour liquid bank cash is starting at **₹${(res.state.physics_state.bank_cash).toLocaleString("en-IN")}**. You can now tell me any customer invoice you issued, expense to pay, or money received, and I will maintain your live cash flow and GST twin!`,
        numbers: `• Company: ${profile.company_name}\n• Bank Cash: ₹${(res.state.physics_state.bank_cash).toLocaleString("en-IN")}\n• Operating Runway: ${res.state.physics_state.estimated_runway_days.toFixed(1)} Days`,
        suggestions: ["Add an invoice", "Add an expense", "How is my money?", "What GST do I owe?"]
      };

      set({
        isLoading: false,
        businessKey: "CUSTOM",
        state: res.state,
        singularity: res.singularity,
        nodes,
        edges,
        messages: [...get().messages, welcomeMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: msg });
    }
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

  setActiveView: (view) => {
    playUiSound("click");
    set({ activeView: view });
  },

  setSelectedCandidateIdx: (idx: number) => {
    playUiSound("click");
    set({ selectedCandidateIdx: idx });
  },

  sendMessage: async (text: string) => {
    if (!text.trim()) return;
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const userMsg: ChatMessageItem = {
      id: Math.random().toString(),
      sender: "user",
      timestamp: now,
      text,
    };

    set({ messages: [...get().messages, userMsg], isThinking: true });

    try {
      const resp: ChatResponse = await sendChatMessageApi(text);
      const aiMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: resp.plain_language_summary,
        numbers: resp.exact_numbers,
        causalExplanation: resp.causal_explanation,
        recommendations: resp.top_recommended_actions,
        whatIf: resp.what_if_ignore,
        cards: resp.cards,
        suggestions: resp.suggestions,
      };

      const partialUpdates: Partial<AetherStoreState> = {
        messages: [...get().messages, aiMsg],
        isThinking: false,
      };

      if (resp.state) {
        partialUpdates.state = resp.state;
      }
      if (resp.singularity) {
        partialUpdates.singularity = resp.singularity;
      }

      set(partialUpdates);

      // Refresh graph nodes and edges to reflect changes
      try {
        const freshState = await fetchStateApi();
        const { nodes, edges } = processBackendGraph(freshState.graph);
        set({
          nodes,
          edges,
          candidates: freshState.candidates || get().candidates,
        });
      } catch {
        // graph stays current
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        isThinking: false,
        messages: [
          ...get().messages,
          {
            id: Math.random().toString(),
            sender: "ai",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            text: `Error connecting to Central Nervous System: ${msg}`,
          },
        ],
      });
    }
  },

  activateWormhole: async () => {
    playUiSound("wormhole");
    set({ isThinking: true });
    try {
      const resp = await activateWormholeApi();
      playUiSound("success");
      const aiMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: resp.plain_language_summary,
        numbers: resp.exact_numbers,
        causalExplanation: resp.causal_explanation,
        recommendations: resp.top_recommended_actions,
        whatIf: resp.what_if_ignore,
        cards: resp.cards,
        suggestions: resp.suggestions,
      };

      const freshState = await fetchStateApi();
      const { nodes, edges } = processBackendGraph(freshState.graph);

      set({
        isThinking: false,
        state: freshState.state,
        singularity: freshState.singularity,
        candidates: freshState.candidates || [],
        nodes,
        edges,
        messages: [...get().messages, aiMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isThinking: false, error: msg });
    }
  },

  simulateDelay: async () => {
    playUiSound("alert");
    set({ isThinking: true });
    try {
      const resp = await simulateDelayApi();
      const aiMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: resp.plain_language_summary,
        numbers: resp.exact_numbers,
        causalExplanation: resp.causal_explanation,
        recommendations: resp.top_recommended_actions,
        whatIf: resp.what_if_ignore,
        cards: resp.cards,
        suggestions: resp.suggestions,
      };

      const freshState = await fetchStateApi();
      const { nodes, edges } = processBackendGraph(freshState.graph);

      set({
        isThinking: false,
        state: freshState.state,
        singularity: freshState.singularity,
        nodes,
        edges,
        messages: [...get().messages, aiMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isThinking: false, error: msg });
    }
  },

  uploadInvoice: async (file: File) => {
    playUiSound("click");
    set({ isThinking: true });
    try {
      const resp = await uploadInvoiceApi(file);
      playUiSound("success");
      const aiMsg: ChatMessageItem = {
        id: Math.random().toString(),
        sender: "ai",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: resp.plain_language_summary,
        numbers: resp.exact_numbers,
        causalExplanation: resp.causal_explanation,
        recommendations: resp.top_recommended_actions,
        whatIf: resp.what_if_ignore,
        cards: resp.cards,
        suggestions: resp.suggestions,
      };

      const freshState = await fetchStateApi();
      const { nodes, edges } = processBackendGraph(freshState.graph);

      set({
        isThinking: false,
        state: freshState.state,
        singularity: freshState.singularity,
        nodes,
        edges,
        messages: [...get().messages, aiMsg],
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ isThinking: false, error: msg });
    }
  },

  sendMessageLive: async (text: string) => {
    return get().sendMessage(text);
  },

  executeWormholeLive: async () => {
    return get().activateWormhole();
  },

  simulateDelayLive: async () => {
    return get().simulateDelay();
  },

  createInvoiceLive: async (customer: string, amount: number) => {
    return get().sendMessage(`Create invoice for ${customer} ${amount} rupees`);
  },
}));
