"use client";

import React, { useRef, useState, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Html, Line } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { useAetherStore, Live3DNode, Live3DEdge } from "@/lib/store";

function CausalNodeMesh({
  node,
  isSelected,
  onSelect,
}: {
  node: Live3DNode;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [hovered, setHovered] = useState(false);

  const isBlackHole = node.type === "BLACKHOLE" || node.type === "TAX_LIABILITY";
  const isInvoice = node.type === "INVOICE";

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
      if (isBlackHole) {
        const pulse = (node.scale || 1.3) * (1 + Math.sin(t * 3.5) * 0.12);
        meshRef.current.scale.set(pulse, pulse, pulse);
      } else {
        const scale = node.scale || 1;
        const bob = Math.sin(t * 2 + node.position[0]) * 0.05;
        meshRef.current.position.y = bob;
        meshRef.current.scale.set(scale, scale, scale);
      }
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
        {isInvoice ? (
          <boxGeometry args={[0.7, 0.42, 0.22]} />
        ) : (
          <sphereGeometry args={[isBlackHole ? 0.55 : 0.4, 32, 32]} />
        )}
        <meshStandardMaterial
          color={node.color}
          emissive={node.emissive}
          emissiveIntensity={hovered || isSelected ? 2.4 : 1.2}
          roughness={0.2}
          metalness={0.85}
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

      {/* Hover / Select Info Tooltip */}
      {(hovered || isSelected) && (
        <Html position={[0, -0.68, 0]} center distanceFactor={8}>
          <div className="px-3.5 py-2 rounded-xl bg-black/95 border border-slate-700 text-xs shadow-2xl whitespace-nowrap pointer-events-none backdrop-blur-md">
            <span className="font-bold text-white block">{node.label}</span>
            <span className="text-slate-300 font-mono text-[11px]">{node.value}</span>
            <div className="text-[10px] text-accentcyan mt-0.5">Click to focus camera</div>
          </div>
        </Html>
      )}
    </group>
  );
}

function AnimatedCausalEdge({ edge }: { edge: Live3DEdge }) {
  const particleRef = useRef<THREE.Mesh>(null!);

  const { curve, curvePoints } = useMemo(() => {
    const p1 = new THREE.Vector3(...edge.from);
    const p2 = new THREE.Vector3(...edge.to);
    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    mid.y += edge.isDrain ? 0.35 : 0.15; // Arc curvature

    const c = new THREE.QuadraticBezierCurve3(p1, mid, p2);
    return { curve: c, curvePoints: c.getPoints(24) };
  }, [edge.from, edge.to, edge.isDrain]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (particleRef.current) {
      const speed = edge.isDrain ? 0.8 : 0.45;
      const progress = (t * speed) % 1;
      const pt = curve.getPoint(progress);
      particleRef.current.position.copy(pt);
    }
  });

  return (
    <group>
      <Line
        points={curvePoints}
        color={edge.color}
        lineWidth={edge.isDrain ? 2.5 : 1.5}
        transparent
        opacity={edge.isDrain ? 0.85 : 0.45}
      />
      {/* Traveling Money Particle */}
      <mesh ref={particleRef}>
        <sphereGeometry args={[edge.isDrain ? 0.06 : 0.045, 12, 12]} />
        <meshBasicMaterial color={edge.color} />
      </mesh>
    </group>
  );
}

function CameraRig() {
  const controlsRef = useRef<OrbitControlsImpl>(null!);
  const cameraTarget = useAetherStore((s) => s.cameraTarget);

  useFrame((state) => {
    if (controlsRef.current) {
      const targetVec = new THREE.Vector3(...cameraTarget);
      controlsRef.current.target.lerp(targetVec, 0.06);

      // Gentle camera follow
      const desiredCamPos = new THREE.Vector3(
        cameraTarget[0] * 0.4,
        cameraTarget[1] * 0.4,
        7.2
      );
      state.camera.position.lerp(desiredCamPos, 0.04);
      controlsRef.current.update();
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      enableZoom={true}
      enablePan={true}
      maxDistance={12}
      minDistance={4}
      maxPolarAngle={Math.PI / 1.7}
      minPolarAngle={Math.PI / 2.5}
    />
  );
}

export default function CausalGraphCanvas({
  onSelectNode,
}: {
  onSelectNode?: (nodeId: string) => void;
}) {
  const nodes = useAetherStore((s) => s.nodes);
  const edges = useAetherStore((s) => s.edges);
  const selectedNodeId = useAetherStore((s) => s.selectedNodeId);
  const selectNode = useAetherStore((s) => s.selectNode);

  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing bg-black/40 rounded-2xl border border-panelborder overflow-hidden">
      <Canvas
        camera={{ position: [0, 0, 7.5], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.55} />
        <pointLight position={[0, 0, 6]} intensity={1.8} />

        <group>
          {/* Animated Causal Edges with Rupee particle flow */}
          {edges.map((edge) => (
            <AnimatedCausalEdge key={edge.id} edge={edge} />
          ))}

          {/* Interactive Causal Nodes */}
          {nodes.map((node) => (
            <CausalNodeMesh
              key={node.id}
              node={node}
              isSelected={selectedNodeId === node.id}
              onSelect={() => {
                selectNode(node.id);
                if (onSelectNode) onSelectNode(node.id);
              }}
            />
          ))}
        </group>

        <CameraRig />
      </Canvas>
    </div>
  );
}
