"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, OrbitControls, Sphere, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

function OrganismCore({ healthScore = 38 }: { healthScore?: number }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const wireRef = useRef<THREE.Mesh>(null!);
  const particlesRef = useRef<THREE.Points>(null!);
  const ringRef = useRef<THREE.Group>(null!);

  // Dynamic color palette based on organism health
  const colors = useMemo(() => {
    if (healthScore >= 75) {
      return { core: "#10b981", emissive: "#059669", aura: "#34d399", speed: 1.2 };
    } else if (healthScore >= 50) {
      return { core: "#f59e0b", emissive: "#d97706", aura: "#fbbf24", speed: 1.8 };
    } else {
      return { core: "#f43f5e", emissive: "#e11d48", aura: "#fb7185", speed: 2.4 };
    }
  }, [healthScore]);

  // Generate particle cloud representing Rupee flow
  const particleCount = 650;
  const particlePositions = useMemo(() => {
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const radius = 2.2 + Math.random() * 1.8;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
    }
    return positions;
  }, []);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    // Heartbeat pulsation
    const pulse = 1 + Math.sin(t * colors.speed * 2) * 0.08;
    if (meshRef.current) {
      meshRef.current.scale.set(pulse, pulse, pulse);
      meshRef.current.rotation.y = t * 0.25;
      meshRef.current.rotation.x = Math.sin(t * 0.15) * 0.2;
    }
    if (wireRef.current) {
      wireRef.current.rotation.y = -t * 0.35;
      wireRef.current.rotation.z = Math.cos(t * 0.2) * 0.2;
    }
    if (particlesRef.current) {
      particlesRef.current.rotation.y = t * 0.12;
      particlesRef.current.rotation.x = Math.sin(t * 0.08) * 0.15;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.3;
      ringRef.current.rotation.x = 1.1 + Math.sin(t * 0.2) * 0.1;
    }
  });

  return (
    <group>
      {/* Central Living Fluid Nucleus */}
      <Sphere ref={meshRef} args={[1.35, 64, 64]}>
        <MeshDistortMaterial
          color={colors.core}
          emissive={colors.emissive}
          emissiveIntensity={0.65}
          distort={0.42}
          speed={colors.speed}
          roughness={0.2}
          metalness={0.8}
          transparent
          opacity={0.88}
        />
      </Sphere>

      {/* Outer Causal Wireframe Shell */}
      <Sphere ref={wireRef} args={[1.65, 24, 24]}>
        <meshStandardMaterial
          color="#22d3ee"
          wireframe
          transparent
          opacity={0.28}
          roughness={0.1}
          metalness={0.9}
        />
      </Sphere>

      {/* Orbiting Rupee / Capital Conservation Rings */}
      <group ref={ringRef}>
        <mesh>
          <torusGeometry args={[2.5, 0.025, 16, 100]} />
          <meshStandardMaterial
            color="#22d3ee"
            emissive="#06b6d4"
            emissiveIntensity={1.2}
            transparent
            opacity={0.7}
          />
        </mesh>
        <mesh rotation={[Math.PI / 3, 0, 0]}>
          <torusGeometry args={[2.8, 0.018, 16, 100]} />
          <meshStandardMaterial
            color="#10b981"
            emissive="#059669"
            emissiveIntensity={1.0}
            transparent
            opacity={0.6}
          />
        </mesh>
      </group>

      {/* Swarming Capital Rupee Particles */}
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={particlePositions.length / 3}
            array={particlePositions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.045}
          color={colors.aura}
          transparent
          opacity={0.75}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Internal Atmospheric Glow Light */}
      <pointLight color={colors.core} intensity={2.5} distance={10} />
      <pointLight color="#22d3ee" intensity={1.5} distance={8} position={[2, 3, 2]} />
    </group>
  );
}

export default function FinancialOrganismCanvas({
  healthScore = 38,
  interactive = true,
}: {
  healthScore?: number;
  interactive?: boolean;
}) {
  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing">
      <Canvas
        camera={{ position: [0, 0, 5.8], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 5]} intensity={1.2} />
        <directionalLight position={[-10, -10, -5]} color="#22d3ee" intensity={0.8} />

        <Float speed={2} rotationIntensity={0.6} floatIntensity={0.8}>
          <OrganismCore healthScore={healthScore} />
        </Float>

        {interactive && (
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate
            autoRotateSpeed={0.8}
            maxPolarAngle={Math.PI / 1.7}
            minPolarAngle={Math.PI / 2.5}
          />
        )}
      </Canvas>
    </div>
  );
}
