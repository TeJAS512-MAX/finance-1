import { ARCHETYPES } from "./mockData";
import { BusinessState, GSTSingularity, LiquidityWormhole } from "./types";

const BACKEND_URL = "http://localhost:8000";

export async function fetchState(archetypeKey: string = "STEEL_TRADER"): Promise<{
  state: BusinessState;
  singularity: GSTSingularity;
  candidates: LiquidityWormhole[];
}> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/state`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      let candidates: LiquidityWormhole[] = [];
      try {
        const cRes = await fetch(`${BACKEND_URL}/api/wormholes/candidates`);
        if (cRes.ok) {
          const cData = await cRes.json();
          candidates = cData.candidates || [];
        }
      } catch {
        candidates = ARCHETYPES[archetypeKey]?.candidates || [];
      }
      return {
        state: data.state,
        singularity: data.singularity,
        candidates: candidates.length > 0 ? candidates : ARCHETYPES[archetypeKey]?.candidates || [],
      };
    }
  } catch {
    // Fall back to client-side data
  }
  return ARCHETYPES[archetypeKey] || ARCHETYPES["STEEL_TRADER"];
}

export async function sendChatMessage(
  message: string,
  currentState: BusinessState,
  currentSingularity: GSTSingularity
): Promise<{
  plain_language_summary: string;
  exact_numbers: string;
  causal_explanation: string;
  top_recommended_actions: string[];
  what_if_ignore: string;
  state?: BusinessState;
  singularity?: GSTSingularity;
}> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Fall back to intelligent client-side processing
  }

  const msg = message.toLowerCase();

  if (msg.includes("who owes") || msg.includes("debtor") || msg.includes("pending")) {
    return {
      plain_language_summary: `Your largest unsettled receivable is with **Reliance Infra Projects Ltd** for **₹14.75 Lakhs** (Invoice BST/2026/1042), followed by **L&T Heavy Fabrication** for **₹9.50 Lakhs**. While these institutional buyers are solvent, their standard 35-to-45 day settlement cycle creates a severe GST timing mismatch against your Nov 20th statutory deadline.`,
      exact_numbers: `• Reliance Infra: ₹14,75,000.00 (Delay: 35 days)\n• L&T Fabrication: ₹9,50,000.00 (Delay: 28 days)\n• Total Trapped Cash: ₹24,25,000.00`,
      causal_explanation: `Institutional payment terms exceed statutory GST GSTR-3B tax payment cycles by 25 days, converting accounting revenue into a cash liquidity deficit.`,
      top_recommended_actions: [
        "Deploy 2.0% dynamic settlement rebate to Reliance treasury desk",
        "Activate Liquidity Wormhole to ring-fence tax portion",
      ],
      what_if_ignore: `Tax liability of ₹2,84,915 comes due before collections arrive, resulting in negative bank cash on Nov 20th.`,
    };
  }

  if (msg.includes("afford") || msg.includes("machine") || msg.includes("5 lakh") || msg.includes("spend")) {
    return {
      plain_language_summary: `I strongly advise **against** spending ₹5.00 Lakhs on capital equipment today. Your liquid bank cash is currently **₹1.85 Lakhs**, while your non-negotiable statutory GST obligation on Nov 20th requires **₹2.84 Lakhs**. An outflow of ₹5 Lakhs right now would immediately breach the 21-day minimum runway threshold and bounce your SBI loan EMI.`,
      exact_numbers: `• Available Bank Cash: ₹1,85,000.00\n• Minimum Tax Vault Due (20 Nov): ₹2,84,915.00\n• Deficit after ₹5L purchase: -₹6,00,000.00`,
      causal_explanation: `Capital expenditure diverts required working capital before accrued GST is funded, triggering insolvency conditions.`,
      top_recommended_actions: [
        "Defer machine purchase until Reliance settlement clears in December",
        "Explore asset equipment leasing (vendor financing) at 1.1% monthly cost",
      ],
      what_if_ignore: `Immediate cash exhaustion, bank overdraft penalties, and garnishee statutory notices under CGST Section 79.`,
    };
  }

  if (msg.includes("create invoice") || msg.includes("reliance 2.5")) {
    const updatedState = JSON.parse(JSON.stringify(currentState)) as BusinessState;
    const newInv = {
      id: "INV-AUTO-NEW",
      invoice_number: "BST/2026/1045",
      customer_id: "CUST-RELIANCE",
      customer_name: "Reliance Infra Projects Ltd",
      issue_date: "2026-11-16",
      payment_due_date: "2026-12-01",
      base_amount: 211864.41,
      gst_rate: 0.18,
      gst_amount: 38135.59,
      total_amount: 250000.0,
      cash_collected: 0.0,
      unpaid_cash: 250000.0,
      delay_prediction_days: 35,
      predicted_payment_date: "2026-12-21",
      status: "ISSUED" as const,
    };
    updatedState.invoices.unshift(newInv);
    updatedState.physics_state.pending_receivables += 250000.0;
    updatedState.physics_state.total_rupees_conserved += 250000.0;
    updatedState.gst_snapshot.accrual_output_gst += 38135.59;
    updatedState.gst_snapshot.net_gst_cash_payable += 38135.59;
    updatedState.gst_snapshot.gst_on_unpaid_invoices += 38135.59;

    const updatedSingularity = { ...currentSingularity };
    updatedSingularity.singularity_depth += 38135.59;
    updatedSingularity.statutory_tax_demand += 38135.59;

    return {
      plain_language_summary: `Created GST invoice **#BST/2026/1045** for Reliance Infra (₹2,50,000.00 incl. 18% GST). Notice: Under accrual tax law, this instantly creates a **₹38,135.59** cash tax liability due on Dec 20th. Because Reliance pays in 35 days, do not spend the invoice face value until cash settles!`,
      exact_numbers: `• Base Amount: ₹2,11,864.41\n• CGST (9%): ₹19,067.80\n• SGST (9%): ₹19,067.79\n• Total Invoice: ₹2,50,000.00\n• Deepened Singularity: ₹${updatedSingularity.singularity_depth.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
      causal_explanation: `Every new invoice immediately attaches a statutory tax gravity vector, draining future liquidity before payment arrives.`,
      top_recommended_actions: [
        "Enable automated dynamic discount in 25 days",
        "Maintain invoice in paper-trading receivables ledger",
      ],
      what_if_ignore: `Failure to reserve tax creates accumulated GSTR-3B default at month end.`,
      state: updatedState,
      singularity: updatedSingularity,
    };
  }

  if (msg.includes("activate") || msg.includes("wormhole") || msg.includes("trigger")) {
    const updatedState = JSON.parse(JSON.stringify(currentState)) as BusinessState;
    updatedState.physics_state.bank_cash = 1306085.0;
    updatedState.physics_state.tax_vault_balance = 284915.0;
    updatedState.physics_state.pending_receivables = 1400000.0;
    updatedState.physics_state.viscosity_index = 1.15;
    updatedState.physics_state.tax_gravity_well = 0.0;
    updatedState.physics_state.estimated_runway_days = 46.5;
    updatedState.genome.overall_score = 96;
    updatedState.genome.liquidity_vitality = 94;
    updatedState.genome.tax_compliance_shield = 98;
    updatedState.genome.customer_delay_resilience = 92;

    const resolvedSingularity = {
      ...currentSingularity,
      singularity_depth: 0.0,
      severity: "LOW" as const,
    };

    const executedWormhole = ARCHETYPES[currentState.business.archetype]?.candidates[0] || {
      id: "WRM-EXEC",
      title: "Wormhole-Trident: Balanced Teleportation",
      singularity_id: currentSingularity.id,
      steps: [],
      gross_liquidity_created: 1445500.0,
      total_net_cost: 29500.0,
      effective_apr_annualized: 24.83,
      runway_days_restored: 60,
      singularity_evasion_probability: 0.94,
      constitutional_clearance: true,
      status: "EXECUTED" as const,
      explanation_narrative: "Successfully executed multi-vector liquidity bridge.",
      counterfactual_inaction_damage: "Inaction averted.",
    };
    executedWormhole.status = "EXECUTED";
    updatedState.active_wormholes = [executedWormhole];

    return {
      plain_language_summary: `🚀 **Liquidity Wormhole Successfully Executed!**\n\n• **₹14,45,500.00** liquid cash liberated from Reliance receivables in under 36 hours.\n• **₹2,84,915.00** 100% ring-fenced inside the Intelligent Tax Vault—GSTR-3B tax singularity is neutralized.\n• Operating runway extended from **11.4 days to 46.5 days**.\n• Money Health Genome elevated from **38/100 to 96/100**.`,
      exact_numbers: `• Unlocked Liquid Cash: ₹14,45,500.00\n• Tax Vault Balance: ₹2,84,915.00 (100% Funded)\n• Bank Cash Reserve: ₹13,06,085.00\n• Net Discount Cost: ₹29,500.00\n• Effective Annualized Cost: 24.83% APR`,
      causal_explanation: `Synchronized multi-vector settlement collapsed customer payment latency from 35 days to 1.5 days, fulfilling money conservation laws without external high-interest debt.`,
      top_recommended_actions: [
        "Auto-file GSTR-3B on Nov 20th with zero penalties",
        "Keep remaining ₹13.06 Lakhs liquid for high-margin supplier inventory purchase",
      ],
      what_if_ignore: `Singularity has been fully neutralized. Organism is safe and growing.`,
      state: updatedState,
      singularity: resolvedSingularity,
    };
  }

  // General health status
  return {
    plain_language_summary: `Your business organism is currently running at a **Money Health Genome score of ${currentState.genome.overall_score}/100**. While operations are fundamentally profitable, an acute **GST Accrual Singularity of ₹${currentSingularity.singularity_depth.toLocaleString("en-IN", { minimumFractionDigits: 2 })}** converges on Nov 20th. Unpaid client receivables hold ₹${currentState.gst_snapshot.gst_on_unpaid_invoices.toLocaleString("en-IN")} in accrued tax liability that must be settled in cash.`,
    exact_numbers: `• Bank Cash: ₹${currentState.physics_state.bank_cash.toLocaleString("en-IN")}\n• Net GST Cash Due: ₹${currentState.gst_snapshot.net_gst_cash_payable.toLocaleString("en-IN")}\n• Cash Deficit at Event Horizon: ₹${currentSingularity.singularity_depth.toLocaleString("en-IN", { minimumFractionDigits: 2 })}\n• Operating Runway: ${currentState.physics_state.estimated_runway_days.toFixed(1)} Days`,
    causal_explanation: `Delayed payment cycles across institutional debtors leave cash flow inverted relative to statutory GST accrual cut-offs.`,
    top_recommended_actions: [
      "Review and authorize the synthesized Trident Liquidity Wormhole",
      "Halt non-essential capital expenditures until Nov 20th tax filing is secured",
    ],
    what_if_ignore: `Failure to bridge the ₹${currentSingularity.singularity_depth.toLocaleString("en-IN")} deficit causes GST portal suspension and bank account attachment.`,
  };
}
