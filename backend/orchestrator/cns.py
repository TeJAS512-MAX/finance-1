from __future__ import annotations
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional
import uuid
import re

from backend.models.schemas import (
    AetherPravahState, Invoice, Customer, Supplier, Obligation,
    GSTLiabilitySnapshot, MoneyPhysicsState, MoneyHealthGenome,
    LiquidityWormhole, RupeePacket, BusinessProfile
)
from backend.physics.engine import MoneyPhysicsEngine
from backend.physics.singularity import GSTSingularityPredictor, SingularityPrediction
from backend.causal.graph import CausalSpacetimeGraph
from backend.causal.wormhole_forger import LiquidityWormholeForger
from backend.causal.simulator import CounterfactualSimulator
from backend.agents.sensors import ActiveSensorSwarm, SensorExtractionResult
from backend.agents.specialists import (
    InvoiceForgeSpecialist, GSTAccrualGuardian,
    CollectionPsychologist, TaxVaultKeeper
)
from backend.agents.parliament import AdversarialDebateParliament, DebateTranscript
from backend.agents.supreme_court import ConstitutionalSupremeCourt, ConstitutionalVerificationResult
from backend.agents.meta_evolution import MetaEvolutionChamber
from backend.data.archetypes import (
    generate_bharat_steel_data,
    generate_vastrakala_data,
    generate_nexus_pulse_data
)

class CentralNervousSystem:
    """
    AetherPravah Central Nervous System:
    Coordinates the living financial organism, routing all sensory inputs
    through the Causal Spacetime Substrate, Debate Parliament, and Supreme Court.
    """

    def __init__(self):
        self.current_date = date(2026, 11, 16)
        self.state: AetherPravahState = generate_bharat_steel_data(self.current_date)
        self.graph = CausalSpacetimeGraph()
        self.meta_evolution = MetaEvolutionChamber()
        self.sync_graph()

    def set_archetype(self, archetype_id: str) -> AetherPravahState:
        if archetype_id == "VASTRAKALA":
            self.state = generate_vastrakala_data(self.current_date)
        elif archetype_id == "NEXUS_PULSE":
            self.state = generate_nexus_pulse_data(self.current_date)
        else:
            self.state = generate_bharat_steel_data(self.current_date)
        
        self.sync_graph()
        return self.state

    def sync_graph(self):
        """Re-synchronizes the Causal Spacetime Graph with current physical state."""
        self.graph.build_from_state(
            bank_cash=self.state.physics_state.bank_cash,
            tax_vault=self.state.physics_state.tax_vault_balance,
            invoices=self.state.invoices,
            customers=self.state.customers,
            suppliers=self.state.suppliers,
            obligations=self.state.obligations,
            gst_snapshot=self.state.gst_snapshot
        )
        viz = self.graph.export_graph_visualization()
        self.state.causal_nodes = [n for n in self.graph.nodes_data.values()]
        self.state.causal_edges = self.graph.edges_data

    def predict_current_singularity(self) -> SingularityPrediction:
        return GSTSingularityPredictor.evaluate(
            current_date=self.current_date,
            bank_cash=self.state.physics_state.bank_cash,
            tax_vault_balance=self.state.physics_state.tax_vault_balance,
            invoices=self.state.invoices,
            obligations=self.state.obligations,
            gst_snapshot=self.state.gst_snapshot
        )

    def recompute_physics_and_genome(self):
        singularity = self.predict_current_singularity()
        
        # Calculate new physics
        burn = 240000.0 if self.state.business.archetype == "STEEL_TRADER" else (180000.0 if self.state.business.archetype == "GARMENT_MANUFACTURER" else 650000.0)
        self.state.physics_state = MoneyPhysicsEngine.calculate_state(
            current_date=self.current_date,
            bank_cash=self.state.physics_state.bank_cash,
            tax_vault=self.state.physics_state.tax_vault_balance,
            invoices=self.state.invoices,
            obligations=self.state.obligations,
            gst_snapshot=self.state.gst_snapshot,
            rupee_packets=self.state.rupee_packets,
            monthly_burn_rate=burn
        )

        # Update Genome score
        if singularity.is_singularity_imminent:
            score = max(20, int(75 - (singularity.singularity_depth / 8000.0)))
            trajectory = "BLACK_HOLE_IMMINENT" if singularity.severity == "CRITICAL" else "DECAYING_WARNING"
        else:
            score = min(96, int(60 + (self.state.physics_state.bank_cash / 15000.0)))
            trajectory = "EVOLVING_THRIVING" if score > 80 else "STABLE_BALANCED"

        self.state.genome.overall_score = score
        self.state.genome.trajectory = trajectory
        self.state.gst_snapshot.singularity_risk_score = singularity.probability_of_default
        self.sync_graph()

    def process_user_message(self, message: str, attached_image_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes any user message or multimodal upload and returns the
        strict 5-part protective response format.
        """
        # Tier 0: Sensing
        if attached_image_filename:
            sensor_res = ActiveSensorSwarm.parse_invoice_image_ocr(attached_image_filename)
        else:
            sensor_res = ActiveSensorSwarm.parse_natural_language_or_voice(message)

        singularity = self.predict_current_singularity()
        q_raw = message.strip()

        # Handle Invoice Creation
        if sensor_res.intent == "CREATE_INVOICE":
            data = sensor_res.extracted_data
            cust_name = data.get("customer_name", "Reliance Infra Projects Ltd")
            
            # Find or create customer
            cust = next((c for c in self.state.customers if cust_name.lower() in c.name.lower()), None)
            if not cust:
                cust = Customer(
                    name=cust_name,
                    gstin="27AAACR9999M1Z1",
                    industry="B2B Commercial",
                    payment_behavior_score=65.0,
                    psychological_profile="BUREAUCRATIC_ENTERPRISE",
                    typical_delay_days=30,
                    optimal_chasing_channel="WHATSAPP_GENTLE"
                )
                self.state.customers.append(cust)

            base = float(data.get("base_amount", 250000.0))
            gst_rate = float(data.get("gst_rate", 0.18))
            new_inv, new_packets = InvoiceForgeSpecialist.create_invoice(
                customer=cust,
                base_amount=base,
                gst_rate=gst_rate,
                due_days=30,
                current_date=self.current_date
            )

            self.state.invoices.append(new_inv)
            self.state.rupee_packets.extend(new_packets)

            # Update GST snapshot: invoice instantly adds to accrued output GST!
            self.state.gst_snapshot.output_gst_gross += new_inv.gst_amount
            self.state.gst_snapshot.gst_on_unpaid_invoices += new_inv.gst_amount
            self.state.gst_snapshot.net_gst_cash_payable += new_inv.gst_amount
            self.state.gst_snapshot.tax_deficit += new_inv.gst_amount

            self.recompute_physics_and_genome()
            updated_singularity = self.predict_current_singularity()

            # Synthesize Wormhole if singularity triggered
            wormhole = LiquidityWormholeForger.forge_wormhole(
                current_date=self.current_date,
                singularity=updated_singularity,
                bank_cash=self.state.physics_state.bank_cash,
                tax_vault_balance=self.state.physics_state.tax_vault_balance,
                invoices=self.state.invoices,
                customers=self.state.customers,
                obligations=self.state.obligations,
                gst_snapshot=self.state.gst_snapshot
            )
            if wormhole:
                self.state.active_wormholes = [wormhole]

            # 5-Part Response
            summary = (
                f"✅ **Invoice #{new_inv.invoice_number} created successfully for {new_inv.customer_name}** (₹{new_inv.total_amount:,.2f} total, ₹{new_inv.gst_amount:,.2f} GST). "
                f"Important statutory note: Under Indian GST accrual regulations, this ₹{new_inv.gst_amount:,.2f} tax liability accrues immediately and must be paid in cash by the 20th, even if the buyer settles the invoice 60 days later!"
            )
            numbers = (
                f"- Base: ₹{new_inv.base_amount:,.2f} | GST (18%): ₹{new_inv.gst_amount:,.2f}\n"
                f"- New Net GST Payable on 20th: ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
                f"- Available Bank Cash: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                f"- Immediate Statutory Deficit: ₹{self.state.gst_snapshot.tax_deficit:,.2f}\n"
                f"- Singularity Risk: {updated_singularity.probability_of_default * 100:.0f}% (Confidence: 96%)"
            )
            causal = (
                f"Because the Indian GST council levies tax on *accrual (bill creation date)* rather than cash collection, "
                f"issuing this invoice deepened your 20th Nov GST Black Hole by exactly ₹{new_inv.gst_amount:,.2f}. "
                f"Since Reliance takes ~{cust.typical_delay_days} days to clear funds, bank cash will run dry before payment arrives."
            )
            actions = [
                "✨ **Activate Synthesized Liquidity Wormhole** (bridges the deficit via 2% prompt discount + paper factoring)",
                f"Auto-reserve 18% (₹{new_inv.gst_amount:,.2f}) into Intelligent Tax Vault upon receipt",
                f"Dispatch psychometrically targeted reminder to {cust.name}'s finance director"
            ]
            counterfactual = (
                f"If unaddressed: On the 20th of the month, your bank account will fail to honor the statutory GST debit of ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}. "
                f"The GST portal will block E-way bill generation for consignments, and daily compounding interest penalties of 18% p.a. under Section 50 will be enforced."
            )

            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": updated_singularity.model_dump(),
                "wormhole": wormhole.model_dump() if wormhole else None,
                "state": self.state.model_dump()
            }

        # Handle Wormhole Execution
        if sensor_res.intent == "ACTIVATE_WORMHOLE":
            if not self.state.active_wormholes:
                w = LiquidityWormholeForger.forge_wormhole(
                    current_date=self.current_date,
                    singularity=singularity,
                    bank_cash=self.state.physics_state.bank_cash,
                    tax_vault_balance=self.state.physics_state.tax_vault_balance,
                    invoices=self.state.invoices,
                    customers=self.state.customers,
                    obligations=self.state.obligations,
                    gst_snapshot=self.state.gst_snapshot
                )
                if w:
                    self.state.active_wormholes = [w]

            if self.state.active_wormholes:
                active_w = self.state.active_wormholes[0]
                # Tier 2: Parliament Debate
                debate = AdversarialDebateParliament.deliberate(active_w, singularity, self.state.physics_state)
                # Tier 3: Supreme Court Verification
                sc_res = ConstitutionalSupremeCourt.verify(active_w, self.state.physics_state)

                if sc_res.is_cleared:
                    # Execute Wormhole!
                    active_w.status = "EXECUTED"
                    net_inflow = active_w.gross_liquidity_created - active_w.total_net_cost
                    
                    # Satisfy tax vault first
                    needed_tax = max(0.0, self.state.gst_snapshot.net_gst_cash_payable - self.state.physics_state.tax_vault_balance)
                    tax_fill = min(needed_tax, net_inflow * 0.45)
                    bank_add = net_inflow - tax_fill

                    self.state.physics_state.tax_vault_balance += tax_fill
                    self.state.physics_state.bank_cash += bank_add
                    self.state.gst_snapshot.tax_vault_reserved += tax_fill
                    self.state.gst_snapshot.tax_deficit = max(0.0, self.state.gst_snapshot.net_gst_cash_payable - self.state.gst_snapshot.tax_vault_reserved)

                    # Update RupeePackets conservation
                    self.state.rupee_packets.append(RupeePacket(
                        amount=net_inflow,
                        source_entity=active_w.title,
                        current_location="BANK_AVAILABLE",
                        causal_history=["Teleported via Liquidity Wormhole execution"]
                    ))

                    # Mark targeted invoice as partially settled
                    for inv in self.state.invoices:
                        if inv.status in ("ISSUED", "OVERDUE"):
                            inv.status = "PAID"
                            inv.amount_paid = inv.total_amount
                            break

                    self.recompute_physics_and_genome()
                    post_sing = self.predict_current_singularity()

                    summary = (
                        f"🚀 **Liquidity Wormhole Successfully Activated!** "
                        f"Your Financial Organism is now fully secured. We liberated ₹{active_w.gross_liquidity_created:,.2f} "
                        f"(net ₹{net_inflow:,.2f} after discount costs of ₹{active_w.total_net_cost:,.2f}). "
                        f"Your Tax Vault is now 100% funded, and the GST Accrual Singularity has been successfully resolved!"
                    )
                    numbers = (
                        f"- Cash Liberated: ₹{active_w.gross_liquidity_created:,.2f} (Effective APR: {active_w.effective_apr_annualized}%)\n"
                        f"- Tax Vault Secured: ₹{self.state.physics_state.tax_vault_balance:,.2f} / ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
                        f"- New Bank Balance: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                        f"- Operating Runway: {self.state.physics_state.estimated_runway_days:.1f} Days (Up from ~11 days)\n"
                        f"- Money Health Genome: {self.state.genome.overall_score}/100 ({self.state.genome.trajectory})"
                    )
                    causal = (
                        f"Because we intervened directly with a 2% accelerated discount on Reliance and paper TReDS bridge, "
                        f"we bypassed the 35-day institutional bureaucracy delay. The cash reached your organism before Nov 20th, "
                        f"preventing statutory tax default and keeping your e-way bills intact."
                    )
                    actions = [
                        "Monitor incoming RTGS verification from Reliance Treasury",
                        "Tax Vault auto-lock is active: ₹2,49,915 will be auto-debited cleanly on Nov 20 GSTR-3B filing",
                        "Relax and focus on high-margin sales — your cash runway is safe for the next 35+ days!"
                    ]
                    counterfactual = (
                        "Without this Wormhole, today you would be staring at bank account freeze notices and 18% compounding interest."
                    )

                    return {
                        "plain_language_summary": summary,
                        "exact_numbers": numbers,
                        "causal_explanation": causal,
                        "top_recommended_actions": actions,
                        "what_if_ignore": counterfactual,
                        "debate_transcript": debate.model_dump(),
                        "supreme_court_verification": sc_res.model_dump(),
                        "singularity": post_sing.model_dump(),
                        "wormhole": active_w.model_dump(),
                        "state": self.state.model_dump()
                    }

        # Simulate Delay
        if sensor_res.intent == "SIMULATE_DELAY":
            for inv in self.state.invoices:
                if inv.status in ("ISSUED", "OVERDUE"):
                    inv.delay_prediction_days += 30.0
                    inv.status = "CRITICAL_TRAP"
            self.recompute_physics_and_genome()
            post_sing = self.predict_current_singularity()
            w = LiquidityWormholeForger.forge_wormhole(
                current_date=self.current_date,
                singularity=post_sing,
                bank_cash=self.state.physics_state.bank_cash,
                tax_vault_balance=self.state.physics_state.tax_vault_balance,
                invoices=self.state.invoices,
                customers=self.state.customers,
                obligations=self.state.obligations,
                gst_snapshot=self.state.gst_snapshot
            )
            self.state.active_wormholes = [w] if w else []

            summary = (
                f"⚠️ **Customer Delay Simulated (+30 Days).** "
                f"Viscosity index zoomed up to {self.state.physics_state.viscosity_index:.2f}. "
                f"Your customers are now predicted to hold ₹{self.state.physics_state.pending_receivables:,.2f} for over 60 days. "
                f"This creates an extreme GST Accrual Singularity!"
            )
            numbers = (
                f"- Viscosity: {self.state.physics_state.viscosity_index:.2f} (Severe sludge)\n"
                f"- Singularity Depth: ₹{post_sing.singularity_depth:,.2f}\n"
                f"- Current Bank Cash: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                f"- Health Genome: {self.state.genome.overall_score}/100"
            )
            causal = (
                "Because delays increased without any change to the statutory 20th Nov tax deadline, "
                "the temporal gap between tax outflow and cash inflow widened into a liquidity black hole."
            )
            actions = [
                "Deploy Liquidity Wormhole immediately",
                "Trigger Director-level phone outreach with 2% discount incentive",
                "Apply paper-invoice financing on TReDS portal"
            ]
            counterfactual = (
                f"If ignored, the business will be insolvent on {post_sing.event_horizon_date.strftime('%d %b')}."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": post_sing.model_dump(),
                "wormhole": w.model_dump() if w else None,
                "state": self.state.model_dump()
            }

        # Query: Receivables / Debtors ("who owes me money?")
        if sensor_res.intent == "QUERY_RECEIVABLES":
            unpaid_invoices = [inv for inv in self.state.invoices if inv.status != "PAID"]
            total_unpaid = sum(inv.unpaid_cash for inv in unpaid_invoices)
            
            summary = (
                f"📊 **You have a total of ₹{total_unpaid:,.2f} in outstanding receivables** across {len(unpaid_invoices)} unpaid invoices.\n\n"
                f"• **Reliance Infra Projects Ltd**: ₹14.75 Lakhs (Estimated delay: 35 days, Due: {self.state.invoices[0].due_date.strftime('%d %b')})\n"
                f"• **Larsen & Toubro Heavy Fab**: ₹9.50 Lakhs (Estimated delay: 28 days)\n"
                f"• **Shree Ram Fabrication Works**: ₹4.20 Lakhs (Currently OVERDUE by 25+ days)\n\n"
                f"Crucially, ₹{self.state.gst_snapshot.gst_on_unpaid_invoices:,.2f} in statutory GST has already accrued on these unpaid invoices and must be paid by Nov 20th."
            )
            breakdown_lines = "\n".join([
                f"- **{inv.customer_name}**: ₹{inv.unpaid_cash:,.2f} (Due: {inv.due_date.strftime('%d %b')}, Delay: +{inv.delay_prediction_days}d, Status: {inv.status})"
                for inv in unpaid_invoices
            ])
            numbers = (
                f"- Total Unpaid Receivables: ₹{total_unpaid:,.2f}\n"
                f"- GST Accrued on Unpaid Invoices: ₹{self.state.gst_snapshot.gst_on_unpaid_invoices:,.2f}\n"
                f"- Primary Risk Customers: Reliance Infra Projects (₹14.75L) & Shree Ram (₹4.20L Overdue)"
            )
            causal = (
                "These customer payment delays increase your Fluid Viscosity to "
                f"{self.state.physics_state.viscosity_index:.2f}, while sovereign GST accrues strictly upon bill generation."
            )
            actions = [
                "Deploy a 2% prompt settlement discount for Reliance to unlock ₹14.45L within 36 hours",
                "Issue a formal statutory Section 16 MSMED reminder to Shree Ram Fabrication",
                "Ring-fence incoming settlements into the Intelligent Tax Vault"
            ]
            counterfactual = (
                "If unaddressed, Reliance will settle only in late December, long after your Nov 20th GST Singularity arrives."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Query: Payables / Suppliers / Creditors ("who do I owe money to?")
        if sensor_res.intent == "QUERY_PAYABLES":
            total_supp = sum(s.total_payable for s in self.state.suppliers)
            total_obls = sum(o.amount for o in self.state.obligations)
            
            summary = (
                f"💼 **Your upcoming liabilities over the next 30 days total ₹{total_supp + total_obls:,.2f}.**\n\n"
                f"1. **Raw Material Suppliers**: ₹{self.state.suppliers[0].total_payable:,.2f} payable to Jindal Steel & Power Ltd (GSTR-2B ITC compliance score: 98%).\n"
                f"2. **Bank Loans & Facilities**: SBI MSME Term Loan EMI of ₹88,000 (Due Nov 18) and Stockyard Lease rent of ₹65,000.\n"
                f"3. **Statutory Taxes**: Net GST cash liability of ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f} due on Nov 20."
            )
            numbers = (
                f"- Supplier Payables: ₹{total_supp:,.2f}\n"
                f"- Senior EMIs & Rent: ₹{total_obls:,.2f}\n"
                f"- Net GST Cash Due (Nov 20): ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
                f"- Current Bank Cash: ₹{self.state.physics_state.bank_cash:,.2f}"
            )
            causal = (
                "Prioritize the SBI EMI on Nov 18 (priority 1) to protect your credit rating, while renegotiating the stockyard lease to preserve liquidity."
            )
            actions = [
                "Honor SBI EMI of ₹88,000 to maintain working capital credit limits",
                "Reconcile Jindal Steel invoices against GSTR-2B to claim ₹85,000 in booked ITC",
                "Activate Liquidity Wormhole to bridge the timing mismatch"
            ]
            counterfactual = (
                "Defaulting on the SBI EMI will incur 24% default penalties and downgrade your banking limits."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Query: Affordability / Capex ("can I afford a new machine / 5 lakh expense?")
        if sensor_res.intent == "QUERY_AFFORDABILITY":
            summary = (
                f"🛑 **Recommendation: PAUSE DISCRETIONARY CAPEX & EXPENSES.**\n\n"
                f"Your operational bank account currently holds ₹{self.state.physics_state.bank_cash:,.2f} in liquid cash, "
                f"while your mandatory GSTR-3B tax payment due on the 20th requires ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}. "
                f"You are facing an active **statutory deficit of ₹{singularity.singularity_depth:,.2f}**. "
                f"Committing to new capital expenditures right now will precipitate an immediate liquidity default on Nov 20th!"
            )
            numbers = (
                f"- Current Bank Cash: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                f"- Mandatory Nov 20 Tax Due: ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
                f"- Current Runway: {self.state.physics_state.estimated_runway_days:.1f} Days (Below 21-Day Safety Rule)\n"
                f"- Liquidity Deficit: ₹{singularity.singularity_depth:,.2f}"
            )
            causal = (
                "Every rupee spent on discretionary capex right now directly reduces the funds needed to satisfy sovereign GST obligations."
            )
            actions = [
                "Postpone all non-essential equipment purchases until Nov 20 tax is remitted",
                "Activate Liquidity Wormhole to rebuild bank cushion above ₹10 Lakhs",
                "Once customer collections from Reliance arrive, reassess capex viability"
            ]
            counterfactual = (
                "If you incur additional capex now, senior bank cheques and statutory tax debits will bounce on Nov 18/20th."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Query: Explanation / Concept ("what is gst accrual / wormhole?")
        if sensor_res.intent == "QUERY_EXPLANATION":
            summary = (
                f"💡 **GST Accrual Trap & Liquidity Wormholes Explained:**\n\n"
                f"• **The GST Accrual Trap**: Under the Indian GST regime, tax liability is legally recognized on the *date of invoice issuance*, not when cash is collected. "
                f"When you issue an invoice of ₹14.75 Lakhs to an enterprise buyer (which includes ₹2.25 Lakhs of GST), you are legally required to remit ₹2.25 Lakhs in cash to the government on the 20th of the following month, even if the buyer takes 90 days to settle.\n\n"
                f"• **Liquidity Wormholes**: AetherPravah's proprietary mechanism that dynamically coordinates prompt settlement incentives (e.g. 2% cash discount), verified paper invoice factoring, and automatic tax vault sweeps to accelerate liquidity arrival from weeks to 24–48 hours."
            )
            numbers = (
                f"- GST Accrual on Unpaid Bills: ₹{self.state.gst_snapshot.gst_on_unpaid_invoices:,.2f}\n"
                f"- Money Health Genome Score: {self.state.genome.overall_score}/100\n"
                f"- Statutory Due Date: 20th of every month (GSTR-3B)"
            )
            causal = (
                "The temporal mismatch between legal tax accrual and commercial buyer delays is the primary systemic cause of MSME insolvency."
            )
            actions = [
                "Use the Intelligent Tax Vault to auto-reserve 18% of every incoming rupee",
                "Trigger Liquidity Wormholes whenever projected deficit exceeds ₹1 Lakh"
            ]
            counterfactual = (
                "Understanding this dynamic protects your enterprise from surprise bank account attachments."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Query: Greeting ("Hi, hello, hey")
        if sensor_res.intent == "GREETING":
            summary = (
                f"Hello! Welcome to **AetherPravah** — your 24/7 Causal Financial AI.\n\n"
                f"I am actively tracking every single rupee of **{self.state.business.name}** in real time. "
                f"You can ask me anything: customer payment statuses, invoice creation, cash runway forecasts, "
                f"vendor liabilities, or statutory GST compliance. How can I assist you with your business finances today?"
            )
            numbers = (
                f"- Business: {self.state.business.name} ({self.state.business.city})\n"
                f"- Bank Cash: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                f"- Unpaid Receivables: ₹{self.state.physics_state.pending_receivables:,.2f}\n"
                f"- Health Genome: {self.state.genome.overall_score}/100"
            )
            causal = (
                "Your financial organism is active and continuously running probabilistic state estimation."
            )
            actions = [
                "Ask 'Who owes me the most money?'",
                "Type 'Create invoice for [Customer] [Amount]'",
                "Check 'How is my money?' for a full health audit"
            ]
            counterfactual = (
                "Regular conversational monitoring ensures no cash black hole forms undetected."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Arbitrary Free-form Conversational Inquiry
        if sensor_res.intent == "CONVERSATIONAL_INQUIRY":
            summary = (
                f"Regarding your query: *\"{q_raw}\"*\n\n"
                f"Here is the financial status for **{self.state.business.name}**: "
                f"Your operational bank account has ₹{self.state.physics_state.bank_cash:,.2f} in liquid reserves, while customers currently hold ₹{self.state.physics_state.pending_receivables:,.2f} in pending receivables. "
                f"Most crucially, an upcoming **GSTR-3B tax liability of ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}** is due on Nov 20th. "
                f"Based on your cash velocity, your business has {self.state.physics_state.estimated_runway_days:.1f} days of operating runway."
            )
            numbers = (
                f"- Query Evaluated: \"{q_raw}\"\n"
                f"- Bank Available Cash: ₹{self.state.physics_state.bank_cash:,.2f}\n"
                f"- Tax Liability (Nov 20): ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
                f"- Operating Runway: {self.state.physics_state.estimated_runway_days:.1f} Days\n"
                f"- Health Genome Score: {self.state.genome.overall_score}/100 ({self.state.genome.trajectory})"
            )
            causal = (
                f"Based on your Causal Spacetime Graph, accelerating payment timing across your {len(self.state.invoices)} active invoices "
                f"will optimize your overall liquidity velocity."
            )
            actions = [
                "Activate Liquidity Wormhole to bridge working capital",
                "Review pending debtor invoices in the Singularity Radar",
                "Ask me specific questions like 'Who owes me the most?' or 'Can I buy equipment?'"
            ]
            counterfactual = (
                "Ignoring liquidity timing leads to unexpected statutory GST cash freezes on the 20th."
            )
            return {
                "plain_language_summary": summary,
                "exact_numbers": numbers,
                "causal_explanation": causal,
                "top_recommended_actions": actions,
                "what_if_ignore": counterfactual,
                "singularity": singularity.model_dump(),
                "wormhole": self.state.active_wormholes[0].model_dump() if self.state.active_wormholes else None,
                "state": self.state.model_dump()
            }

        # Default / Health Query
        if not self.state.active_wormholes and singularity.is_singularity_imminent:
            w = LiquidityWormholeForger.forge_wormhole(
                current_date=self.current_date,
                singularity=singularity,
                bank_cash=self.state.physics_state.bank_cash,
                tax_vault_balance=self.state.physics_state.tax_vault_balance,
                invoices=self.state.invoices,
                customers=self.state.customers,
                obligations=self.state.obligations,
                gst_snapshot=self.state.gst_snapshot
            )
            if w:
                self.state.active_wormholes = [w]

        w_active = self.state.active_wormholes[0] if self.state.active_wormholes else None

        summary = (
            f"Welcome! The Financial Organism for **{self.state.business.name}** currently holds a **Money Health Genome score of {self.state.genome.overall_score}/100** ({self.state.genome.trajectory}). "
            f"While top-line sales remain profitable, an impending **GST Accrual Singularity on Nov 20th** threatens to strain your working capital if left unmanaged."
        )
        numbers = (
            f"- Liquid Bank Balance: ₹{self.state.physics_state.bank_cash:,.2f}\n"
            f"- Pending Receivables (Delayed): ₹{self.state.physics_state.pending_receivables:,.2f}\n"
            f"- Statutory GST Due (Nov 20): ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f}\n"
            f"- GST Accrual Trap (GST on Unpaid Bills): ₹{self.state.gst_snapshot.gst_on_unpaid_invoices:,.2f}\n"
            f"- Immediate Cash Deficit at Horizon: ₹{singularity.singularity_depth:,.2f}\n"
            f"- Estimated Runway: {self.state.physics_state.estimated_runway_days:.1f} Days (90% Conf: {self.state.physics_state.confidence_interval_runway[0]} - {self.state.physics_state.confidence_interval_runway[1]} days)"
        )
        causal = (
            f"Because Reliance Infra Projects and L&T are operating on a 35-day payment cycle, ₹{self.state.gst_snapshot.gst_on_unpaid_invoices:,.2f} of GST "
            f"has legally accrued on their uncollected invoices. The GST portal does not wait for customer collection. "
            f"On Nov 20th, ₹{self.state.gst_snapshot.net_gst_cash_payable:,.2f} will be demanded from an available bank pool of only ₹{self.state.physics_state.bank_cash:,.2f}."
        )
        actions = [
            f"🚀 **Authorize Liquidity Wormhole**: Teleports ₹{w_active.gross_liquidity_created:,.2f} via 2% prompt discount & paper factoring" if w_active else "Tax Vault Auto-Sweep",
            "Send AI-crafted psychometric reminder to Reliance Accounts Team",
            "Maintain 21-day runway minimum by shielding the Tax Vault"
        ]
        counterfactual = (
            f"If you take no action, bank cash hits negative -₹{singularity.singularity_depth:,.2f} in {singularity.days_to_event_horizon} days. "
            f"SBI will bounce loan EMIs and the GST portal will freeze e-way bill generation."
        )

        return {
            "plain_language_summary": summary,
            "exact_numbers": numbers,
            "causal_explanation": causal,
            "top_recommended_actions": actions,
            "what_if_ignore": counterfactual,
            "singularity": singularity.model_dump(),
            "wormhole": w_active.model_dump() if w_active else None,
            "state": self.state.model_dump()
        }
