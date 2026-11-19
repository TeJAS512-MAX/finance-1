"use client";

import React, { useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Html, Line } from "@react-three/drei";
import * as THREE from "three";

interface GraphNodeData {
  id: string;
  label: string;
  sublabel: string;
  type: "CUSTOMER" | "INVOICE" | "BANK" | "VAULT" | "BLACKHOLE" | "OBLIGATION";
  position: [number, number, number];
  color: string;
  emissive: string;
  value: string;
}

const NODES_DATA: GraphNodeData[] = [
  {
    id: "cust-reliance",
    label: "Reliance Infra",
    sublabel: "35d delay pred",
    type: "CUSTOMER",
    position: [-3.2, 1.6, 0],
    color: "#f59e0b",
    emissive: "#d97706",
    value: "35d latency",
  },
  {
    id: "cust-lt",
    label: "L&T Fab",
    sublabel: "28d delay pred",
    type: "CUSTOMER",
    position: [-3.2, -1.2, 0],
    color: "#f59e0b",
    emissive: "#d97706",
    value: "28d latency",
  },
  {
    id: "inv-1042",
    label: "Inv #1042",
    sublabel: "₹14.75L",
    type: "INVOICE",
    position: [-1.2, 1.4, 0.4],
    color: "#06b6d4",
    emissive: "#0891b2",
    value: "₹14.75 Lakhs",
  },
  {
    id: "inv-1043",
    label: "Inv #1043",
    sublabel: "₹9.50L",
    type: "INVOICE",
    position: [-1.2, -1.0, 0.4],
    color: "#06b6d4",
    emissive: "#0891b2",
    value: "₹9.50 Lakhs",
  },
  {
    id: "bank-cash",
    label: "Bank Cash",
    sublabel: "₹1.85 Lakhs",
    type: "BANK",
    position: [1.2, 0, 0],
    color: "#10b981",
    emissive: "#059669",
    value: "₹1.85 Lakhs",
  },
  {
    id: "tax-vault",
    label: "Tax Vault",
    sublabel: "₹35,000",
    type: "VAULT",
    position: [1.2, -1.8, 0.5],
    color: "#22d3ee",
    emissive: "#06b6d4",
    value: "₹35,000",
  },
  {
    id: "gst-singularity",
    label: "GST BLACK HOLE",
    sublabel: "₹2.85L (20 Nov)",
    type: "BLACKHOLE",
    position: [1.8, 1.8, 0],
    color: "#f43f5e",
    emissive: "#e11d48",
    value: "-₹1.53L Singularity",
  },
  {
    id: "sbi-emi",
    label: "SBI Loan EMI",
    sublabel: "₹88,000",
    type: "OBLIGATION",
    position: [3.4, -0.6, 0.3],
    color: "#8b5cf6",
    emissive: "#7c3aed",
    value: "₹88,000 due 18 Nov",
  },
];

const EDGES_DATA: { from: [number, number, number]; to: [number, number, number]; color: string; isDrain?: boolean }[] = [
  // Customer to Invoices
  { from: [-3.2, 1.6, 0], to: [-1.2, 1.4, 0.4], color: "#f59e0b" },
  { from: [-3.2, -1.2, 0], to: [-1.2, -1.0, 0.4], color: "#f59e0b" },
  // Invoices to Bank
  { from: [-1.2, 1.4, 0.4], to: [1.2, 0, 0], color: "#06b6d4" },
  { from: [-1.2, -1.0, 0.4], to: [1.2, 0, 0], color: "#06b6d4" },
  // Invoice to GST Singularity (Accrual Trap Vector)
  { from: [-1.2, 1.4, 0.4], to: [1.8, 1.8, 0], color: "#f43f5e", isDrain: true },
  { from: [-1.2, -1.0, 0.4], to: [1.8, 1.8, 0], color: "#f43f5e", isDrain: true },
  // GST Singularity pulling Bank Cash
  { from: [1.8, 1.8, 0], to: [1.2, 0, 0], color: "#f43f5e", isDrain: true },
  // Bank to Tax Vault
  { from: [1.2, 0, 0], to: [1.2, -1.8, 0.5], color: "#22d3ee" },
  // Bank to SBI EMI
  { from: [1.2, 0, 0], to: [3.4, -0.6, 0.3], color: "#8b5cf6" },
];

function CausalNodeMesh({
  node,
  isSelected,
  onSelect,
}: {
  node: GraphNodeData;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (node.type === "BLACKHOLE" && meshRef.current) {
      const pulse = 1 + Math.sin(t * 3.5) * 0.15;
      meshRef.current.scale.set(pulse, pulse, pulse);
    }
  });

  return (
    <group position={node.position}>
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => setHovered(false)}
      >
        {node.type === "INVOICE" ? (
          <boxGeometry args={[0.7, 0.4, 0.2]} />
        ) : (
          <sphereGeometry args={[node.type === "BLACKHOLE" ? 0.55 : 0.42, 32, 32]} />
        )}
        <meshStandardMaterial
          color={node.color}
          emissive={node.emissive}
          emissiveIntensity={hovered || isSelected ? 2.0 : 1.1}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Node Label Text */}
      <Text
        position={[0, 0.65, 0]}
        fontSize={0.2}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        font="https://fonts.gstatic.com/s/inter/v12/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2"
      >
        {node.label}
      </Text>
      <Text
        position={[0, 0.42, 0]}
        fontSize={0.14}
        color={node.color}
        anchorX="center"
        anchorY="middle"
      >
        {node.sublabel}
      </Text>

      {/* Hover Info Tooltip */}
      {(hovered || isSelected) && (
        <Html position={[0, -0.65, 0]} center distanceFactor={8}>
          <div className="px-3 py-1.5 rounded-lg bg-black/90 border border-slate-700 text-xs shadow-2xl whitespace-nowrap pointer-events-none">
            <span className="font-bold text-white block">{node.label}</span>
            <span className="text-slate-300 font-mono text-[11px]">{node.value}</span>
          </div>
        </Html>
      )}
    </group>
  );
}

function CausalEdge({
  from,
  to,
  color,
  isDrain = false,
}: {
  from: [number, number, number];
  to: [number, number, number];
  color: string;
  isDrain?: boolean;
}) {
  const curvePoints = React.useMemo(() => {
    const p1 = new THREE.Vector3(...from);
    const p2 = new THREE.Vector3(...to);
    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    mid.y += isDrain ? 0.35 : 0.15; // Arc curvature

    const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
    return curve.getPoints(24);
  }, [from, to, isDrain]);

  return (
    <Line
      points={curvePoints}
      color={color}
      lineWidth={isDrain ? 2.5 : 1.5}
      transparent
      opacity={isDrain ? 0.85 : 0.45}
    />
  );
}

export default function CausalGraphCanvas({
  onSelectNode,
}: {
  onSelectNode?: (nodeId: string) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<string | null>("gst-singularity");

  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing bg-black/40 rounded-2xl border border-panelborder overflow-hidden">
      <Canvas
        camera={{ position: [0, 0, 7.5], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[0, 0, 6]} intensity={1.5} />

        <group>
          {/* Causal Edges */}
          {EDGES_DATA.map((edge, idx) => (
            <CausalEdge
              key={idx}
              from={edge.from}
              to={edge.to}
              color={edge.color}
              isDrain={edge.isDrain}
            />
          ))}

          {/* Causal Nodes */}
          {NODES_DATA.map((node) => (
            <CausalNodeMesh
              key={node.id}
              node={node}
              isSelected={selectedNode === node.id}
              onSelect={() => {
                setSelectedNode(node.id);
                if (onSelectNode) onSelectNode(node.id);
              }}
            />
          ))}
        </group>

        <OrbitControls
          enableZoom={true}
          enablePan={true}
          maxDistance={12}
          minDistance={4}
          maxPolarAngle={Math.PI / 1.7}
          minPolarAngle={Math.PI / 2.5}
        />
      </Canvas>
    </div>
  );
}
