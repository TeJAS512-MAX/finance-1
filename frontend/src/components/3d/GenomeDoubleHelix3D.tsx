"use client";

import React, { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

interface GenomeScoreProps {
  score?: number;
}

function HelixStructure({ score = 38 }: GenomeScoreProps) {
  const groupRef = useRef<THREE.Group>(null!);
  const pairCount = 20;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (groupRef.current) {
      groupRef.current.rotation.y = t * 0.45;
      groupRef.current.position.y = Math.sin(t * 0.8) * 0.12;
    }
  });

  const genomeColors = ["#10b981", "#22d3ee", "#f59e0b", "#8b5cf6", "#38bdf8"];

  return (
    <group ref={groupRef}>
      {Array.from({ length: pairCount }).map((_, i) => {
        const y = (i - pairCount / 2) * 0.28;
        const angle = i * 0.35;
        const radius = 1.1;

        const x1 = Math.cos(angle) * radius;
        const z1 = Math.sin(angle) * radius;
        const x2 = -x1;
        const z2 = -z1;

        const color = genomeColors[i % genomeColors.length];

        return (
          <group key={i}>
            {/* Strand Node A */}
            <mesh position={[x1, y, z1]}>
              <sphereGeometry args={[0.08, 16, 16]} />
              <meshStandardMaterial
                color={score >= 60 ? "#10b981" : color}
                emissive={score >= 60 ? "#059669" : color}
                emissiveIntensity={1.2}
              />
            </mesh>

            {/* Connecting Base Pair Rung */}
            <mesh position={[0, y, 0]} rotation={[0, -angle, Math.PI / 2]}>
              <cylinderGeometry args={[0.02, 0.02, radius * 2, 8]} />
              <meshStandardMaterial
                color="#64748b"
                transparent
                opacity={0.45}
                roughness={0.5}
              />
            </mesh>

            {/* Strand Node B */}
            <mesh position={[x2, y, z2]}>
              <sphereGeometry args={[0.08, 16, 16]} />
              <meshStandardMaterial
                color={score >= 60 ? "#22d3ee" : color}
                emissive={score >= 60 ? "#06b6d4" : color}
                emissiveIntensity={1.2}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

export default function GenomeDoubleHelixCanvas({ score = 38 }: GenomeScoreProps) {
  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing">
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[5, 5, 5]} intensity={1.5} />
        <pointLight position={[-5, -5, -5]} color="#22d3ee" intensity={1.0} />

        <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.3}>
          <HelixStructure score={score} />
        </Float>

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate={false}
          maxPolarAngle={Math.PI / 1.8}
          minPolarAngle={Math.PI / 2.2}
        />
      </Canvas>
    </div>
  );
}
