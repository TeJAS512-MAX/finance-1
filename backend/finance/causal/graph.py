from __future__ import annotations
import networkx as nx
from typing import List, Dict, Any, Optional
from datetime import datetime
from schemas.finance import (
    CausalNode, CausalEdge, Invoice, Customer, Supplier, 
    Obligation, GSTLiabilitySnapshot, MoneyPhysicsState
)

class CausalSpacetimeGraph:
    """
    Causal Spacetime Graph:
    Directed typed causal hypergraph representing every financial entity,
    liability propagation, and money flow vector.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes_data: Dict[str, CausalNode] = {}
        self.edges_data: List[CausalEdge] = []

    def clear(self):
        self.graph.clear()
        self.nodes_data.clear()
        self.edges_data.clear()

    def add_node(self, node: CausalNode):
        self.nodes_data[node.id] = node
        self.graph.add_node(
            node.id, 
            node_type=node.node_type, 
            label=node.label, 
            value=node.value,
            properties=node.properties
        )

    def add_edge(self, edge: CausalEdge):
        self.edges_data.append(edge)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation_type=edge.relation_type,
            weight=edge.weight,
            viscosity_days=edge.viscosity_days,
            is_counterfactual=edge.is_counterfactual,
            metadata=edge.metadata
        )

    def build_from_state(
        self,
        bank_cash: float,
        tax_vault: float,
        invoices: List[Invoice],
        customers: List[Customer],
        suppliers: List[Supplier],
        obligations: List[Obligation],
        gst_snapshot: GSTLiabilitySnapshot
    ):
        self.clear()

        # Core Financial Reservoirs
        bank_node = CausalNode(
            id="NODE-BANK-MAIN",
            node_type="BANK_ACCOUNT",
            label="Main Operational Bank Account",
            value=bank_cash,
            properties={"liquid": True, "currency": "INR"}
        )
        self.add_node(bank_node)

        vault_node = CausalNode(
            id="NODE-TAX-VAULT",
            node_type="TAX_VAULT",
            label="Intelligent Tax Vault (Ring-Fenced)",
            value=tax_vault,
            properties={"protected_statutory": True}
        )
        self.add_node(vault_node)

        gst_node = CausalNode(
            id="NODE-GST-LIABILITY",
            node_type="TAX_LIABILITY",
            label=f"GST GSTR-3B Liability ({gst_snapshot.period})",
            value=gst_snapshot.net_gst_cash_payable,
            properties={
                "due_date": gst_snapshot.gstr3b_due_date.isoformat(),
                "gst_on_unpaid": gst_snapshot.gst_on_unpaid_invoices
            }
        )
        self.add_node(gst_node)

        # Edge from Tax Vault to GST
        self.add_edge(CausalEdge(
            source_id="NODE-TAX-VAULT",
            target_id="NODE-GST-LIABILITY",
            relation_type="SHIELDS_AND_SATISFIES",
            weight=1.0,
            viscosity_days=0.0
        ))

        # Edge from Bank to GST (the drain)
        self.add_edge(CausalEdge(
            source_id="NODE-GST-LIABILITY",
            target_id="NODE-BANK-MAIN",
            relation_type="STATUTORY_GRAVITY_DRAIN",
            weight=1.0,
            viscosity_days=0.0
        ))

        # Customer Nodes
        cust_map = {c.id: c for c in customers}
        for cust in customers:
            c_node = CausalNode(
                id=f"NODE-CUST-{cust.id}",
                node_type="CUSTOMER",
                label=f"Customer: {cust.name}",
                value=cust.total_outstanding,
                properties={
                    "behavior_score": cust.payment_behavior_score,
                    "profile": cust.psychological_profile,
                    "delay_days": cust.typical_delay_days
                }
            )
            self.add_node(c_node)

        # Invoice Nodes
        for inv in invoices:
            inv_node = CausalNode(
                id=f"NODE-INV-{inv.id}",
                node_type="INVOICE",
                label=f"Invoice #{inv.invoice_number}",
                value=inv.total_amount,
                properties={
                    "base": inv.base_amount,
                    "gst": inv.gst_amount,
                    "status": inv.status,
                    "unpaid": inv.unpaid_cash,
                    "delay_pred": inv.delay_prediction_days
                }
            )
            self.add_node(inv_node)

            # Customer -> Invoice Edge
            self.add_edge(CausalEdge(
                source_id=f"NODE-CUST-{inv.customer_id}",
                target_id=f"NODE-INV-{inv.id}",
                relation_type="CONTROLS_PAYMENT_TIMING",
                weight=cust_map.get(inv.customer_id, Customer(id="", name="", gstin="", industry="", payment_behavior_score=50, psychological_profile="PROMPT_PAYER")).payment_behavior_score / 100.0,
                viscosity_days=inv.delay_prediction_days
            ))

            # Invoice -> Bank Cash Edge (Delayed liquidity)
            if inv.status != "PAID":
                self.add_edge(CausalEdge(
                    source_id=f"NODE-INV-{inv.id}",
                    target_id="NODE-BANK-MAIN",
                    relation_type="TRANSMITS_LIQUID_CASH",
                    weight=0.9,
                    viscosity_days=inv.delay_prediction_days
                ))

            # DEADLY TRAP EDGE: Invoice -> GST Liability (Instant accrual regardless of payment!)
            self.add_edge(CausalEdge(
                source_id=f"NODE-INV-{inv.id}",
                target_id="NODE-GST-LIABILITY",
                relation_type="TRIGGERS_INSTANT_TAX_ACCRUAL",
                weight=1.0,
                viscosity_days=0.0,
                metadata={"gst_accrued": inv.gst_amount, "paid_yet": inv.status == "PAID"}
            ))

        # Obligations
        for obl in obligations:
            obl_node = CausalNode(
                id=f"NODE-OBL-{obl.id}",
                node_type="LOAN_OBLIGATION",
                label=f"Obligation: {obl.name}",
                value=obl.amount,
                properties={"type": obl.obligation_type, "priority": obl.priority}
            )
            self.add_node(obl_node)

            self.add_edge(CausalEdge(
                source_id="NODE-BANK-MAIN",
                target_id=f"NODE-OBL-{obl.id}",
                relation_type="MUST_HONOR_OBLIGATION",
                weight=1.0,
                viscosity_days=0.0
            ))

    def trace_causal_chain(self, start_node_id: str, end_node_id: str) -> List[List[str]]:
        """
        Traces all directed causal paths from cause to effect.
        """
        try:
            paths = list(nx.all_simple_paths(self.graph, source=start_node_id, target=end_node_id, cutoff=5))
            return paths
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return []

    def export_graph_visualization(self) -> Dict[str, Any]:
        """
        Returns JSON-serializable node and edge list for interactive UI charts
        with dynamic topological coordinates and physics field charges.
        """
        nodes = []
        cust_idx = 0
        inv_idx = 0
        obl_idx = 0

        for n_id, n in self.nodes_data.items():
            # Calculate dynamic coordinate layout based on node type
            if n.node_type == "CUSTOMER":
                x, y = 120, 90 + (cust_idx * 90)
                charge = -0.5
                cust_idx += 1
            elif n.node_type == "INVOICE":
                x, y = 280, 90 + (inv_idx * 90)
                charge = 0.8
                inv_idx += 1
            elif n.node_type == "BANK_ACCOUNT":
                x, y = 480, 220
                charge = 1.0
            elif n.node_type == "TAX_VAULT":
                x, y = 480, 350
                charge = 0.9
            elif n.node_type == "TAX_LIABILITY":
                x, y = 520, 100
                charge = -1.0  # Gravitational drain
            elif n.node_type == "LOAN_OBLIGATION":
                x, y = 620, 220 + (obl_idx * 75)
                charge = -0.7
                obl_idx += 1
            else:
                x, y = 350, 200
                charge = 0.0

            nodes.append({
                "id": n.id,
                "label": n.label,
                "type": n.node_type,
                "value": n.value,
                "properties": n.properties,
                "x": x,
                "y": y,
                "charge": charge
            })
        
        edges = []
        for e in self.edges_data:
            edges.append({
                "source": e.source_id,
                "target": e.target_id,
                "relation": e.relation_type,
                "weight": e.weight,
                "viscosity_days": e.viscosity_days,
                "is_counterfactual": e.is_counterfactual
            })
            
        return {"nodes": nodes, "edges": edges}
