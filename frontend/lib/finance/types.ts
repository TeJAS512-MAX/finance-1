export interface RupeePacket {
  id: string;
  amount: number;
  location: string;
  earmarked_for: string;
  source_invoice_id?: string;
  arrival_timestamp: string;
  confidence: number;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  customer_id: string;
  customer_name: string;
  issue_date: string;
  payment_due_date: string;
  base_amount: number;
  gst_rate: number;
  gst_amount: number;
  total_amount: number;
  cash_collected: number;
  unpaid_cash: number;
  delay_prediction_days: number;
  predicted_payment_date: string;
  status: "ISSUED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CRITICAL_TRAP";
}

export interface Customer {
  id: string;
  name: string;
  historical_delay_mean_days: number;
  payment_delay_variance: number;
  discount_sensitivity: number;
  dispute_probability: number;
  optimal_chasing_channel: string;
  psychological_profile: string;
}

export interface Obligation {
  id: string;
  name: string;
  category: "LOAN_EMI" | "SUPPLIER_PAYABLE" | "PAYROLL" | "OPERATIONAL_EXPENSE";
  amount: number;
  due_date: string;
  is_negotiable: boolean;
  priority: number;
}

export interface GSTLiabilitySnapshot {
  period: string;
  accrual_output_gst: number;
  eligible_input_tax_credit: number;
  net_gst_cash_payable: number;
  gst_on_unpaid_invoices: number;
  due_date: string;
}

export interface WormholeStep {
  step_number: number;
  action_type: string;
  target_entity: string;
  amount_unlocked: number;
  cost_or_haircut: number;
  implementation_time_hours: number;
  confidence: number;
  causal_mechanism: string;
}

export interface LiquidityWormhole {
  id: string;
  title: string;
  singularity_id: string;
  steps: WormholeStep[];
  gross_liquidity_created: number;
  total_net_cost: number;
  effective_apr_annualized: number;
  runway_days_restored: number;
  singularity_evasion_probability: number;
  constitutional_clearance: boolean;
  status: "SYNTHESIZED" | "PENDING_APPROVAL" | "EXECUTED" | "DISMISSED";
  explanation_narrative: string;
  counterfactual_inaction_damage: string;
}

export interface MoneyHealthGenome {
  overall_score: number;
  liquidity_vitality: number;
  tax_compliance_shield: number;
  customer_delay_resilience: number;
  debt_service_health: number;
  capital_efficiency: number;
}

export interface GSTSingularity {
  id: string;
  detection_timestamp: string;
  event_horizon_date: string;
  days_to_event_horizon: number;
  singularity_depth: number;
  statutory_tax_demand: number;
  tax_vault_deficit: number;
  severity: "LOW" | "ELEVATED" | "CRITICAL" | "TERMINAL";
  primary_trapped_invoice_id: string;
  primary_debtor_name: string;
  causal_root_chains: string[];
}

export interface BusinessState {
  business: {
    id: string;
    name: string;
    archetype: string;
    monthly_burn_rate: number;
    gstin: string;
    city: string;
  };
  physics_state: {
    bank_cash: number;
    tax_vault_balance: number;
    pending_receivables: number;
    total_rupees_conserved: number;
    viscosity_index: number;
    tax_gravity_well: number;
    estimated_runway_days: number;
  };
  genome: MoneyHealthGenome;
  gst_snapshot: GSTLiabilitySnapshot;
  invoices: Invoice[];
  customers: Customer[];
  obligations: Obligation[];
  active_wormholes: LiquidityWormhole[];
}

export interface ForecastDayItem {
  day: number;
  date: string;
  balance: number;
  inflow: number;
  outflow: number;
  is_negative: boolean;
}

export interface ForecastEventItem {
  day: number;
  date: string;
  inflow: number;
  outflow: number;
  balance: number;
  description: string;
  is_negative: boolean;
}

export interface ForecastResponse {
  dates: string[];
  balances: number[];
  summary: {
    starting_cash: number;
    ending_cash: number;
    lowest_balance: number;
    lowest_date: string;
    lowest_date_label: string;
    lowest_day_offset: number;
    is_deficit: boolean;
    max_deficit: number;
    estimated_runway_days: number;
    daily_burn_rate: number;
    total_inflows: number;
    total_outflows: number;
  };
  events: ForecastEventItem[];
  daily: ForecastDayItem[];
  assumptions: string[];
}

export interface GstStepItem {
  title: string;
  detail: string;
  amount: number;
  tone: string;
}

export interface GstPlanResponse {
  period: string;
  due_date: string;
  due_label: string;
  days_left: number;
  output_gst: number;
  itc_claimed: number;
  itc_at_risk: number;
  net_payable: number;
  in_vault: number;
  still_to_arrange: number;
  vault_coverage_pct: number;
  bank_cash: number;
  gst_on_unpaid: number;
  steps: GstStepItem[];
}

export interface LedgerDebtorItem {
  id: string;
  invoice_number: string;
  customer_name: string;
  amount: number;
  gst_amount: number;
  due_date: string;
  due_label: string;
  days_overdue: number;
  delay_prediction_days: number;
  expected_label: string;
  status: string;
}

export interface LedgerCreditorItem {
  id: string;
  name: string;
  category: string;
  amount: number;
  due_date: string;
  due_label: string;
  days_left: number;
  priority: number;
  priority_label: string;
  status: string;
}

export interface LedgerResponse {
  debtors: {
    invoices: LedgerDebtorItem[];
    summary: {
      total_pending: number;
      overdue_amount: number;
      expected_30_days: number;
      gst_inside: number;
      count: number;
    };
  };
  creditors: {
    liabilities: LedgerCreditorItem[];
    summary: {
      total_payables: number;
      bank_cash: number;
      coverage_deficit: number;
      count: number;
    };
  };
}

export interface EmiResponse {
  principal: number;
  rate_annual: number;
  tenure_months: number;
  monthly_emi: number;
  total_interest: number;
  total_payment: number;
  verdict: {
    ratio_pct?: number | null;
    verdict: "comfortable" | "stretched" | "heavy";
    text: string;
  };
}

export interface GstCalcResponse {
  base: number;
  gst: number;
  cgst: number;
  sgst: number;
  total: number;
}

export interface ProfitModelResponse {
  monthly_sales: number;
  cogs_percentage: number;
  cost_of_goods_sold: number;
  gross_profit: number;
  gross_margin_pct: number;
  operating_expenses: number;
  operating_profit: number;
  existing_emis: number;
  net_profit: number;
  net_margin_pct: number;
  break_even_sales: number;
}
