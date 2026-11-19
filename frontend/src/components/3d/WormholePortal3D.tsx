"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

function WormholeCore({ isActivating = false }: { isActivating?: boolean }) {
  const tunnelRef = useRef<THREE.Group>(null!);
  const particlesRef = useRef<THREE.Points>(null!);
  const ringCount = 18;

  // Generate particle vortex through the wormhole tunnel
  const particleCount = 750;
  const { positions, speeds } = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    const spd = new Float32Array(particleCount);
    for (let i = 0; i < particleCount; i++) {
      const radius = 0.8 + Math.random() * 2.2;
      const angle = Math.random() * Math.PI * 2;
      const z = (Math.random() - 0.5) * 12;
      pos[i * 3] = radius * Math.cos(angle);
      pos[i * 3 + 1] = radius * Math.sin(angle);
      pos[i * 3 + 2] = z;
      spd[i] = 0.05 + Math.random() * 0.12;
    }
    return { positions: pos, speeds: spd };
  }, []);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const speedMultiplier = isActivating ? 4.5 : 1.0;

    // Rotate the tunnel structure
    if (tunnelRef.current) {
      tunnelRef.current.rotation.z = t * 0.4 * speedMultiplier;
    }

    // Animate particles through the tunnel
    if (particlesRef.current) {
      const posArray = particlesRef.current.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        // Move particle forward in Z axis (teleportation effect)
        posArray[i * 3 + 2] += speeds[i] * speedMultiplier;
        if (posArray[i * 3 + 2] > 6) {
          posArray[i * 3 + 2] = -6;
        }
      }
      particlesRef.current.geometry.attributes.position.needsUpdate = true;
      particlesRef.current.rotation.z = -t * 0.2 * speedMultiplier;
    }
  });

  return (
    <group>
      {/* Concentric Wormhole Rings forming the portal horizon */}
      <group ref={tunnelRef}>
        {Array.from({ length: ringCount }).map((_, idx) => {
          const zPos = (idx - ringCount / 2) * 0.65;
          const radius = 1.3 + Math.sin((idx / ringCount) * Math.PI) * 1.2;
          const isCore = idx % 2 === 0;
          return (
            <mesh key={idx} position={[0, 0, zPos]}>
              <torusGeometry args={[radius, 0.035, 16, 64]} />
              <meshStandardMaterial
                color={isCore ? "#22d3ee" : "#10b981"}
                emissive={isCore ? "#06b6d4" : "#059669"}
                emissiveIntensity={isActivating ? 2.5 : 1.2}
                transparent
                opacity={0.65}
                roughness={0.1}
                metalness={0.9}
              />
            </mesh>
          );
        })}
      </group>

      {/* High-Velocity Particle Flow */}
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={positions.length / 3}
            array={positions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={isActivating ? 0.08 : 0.045}
          color="#38bdf8"
          transparent
          opacity={0.8}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Internal Portal Beams */}
      <pointLight color="#22d3ee" intensity={isActivating ? 5.0 : 2.5} distance={12} />
      <pointLight color="#10b981" intensity={isActivating ? 4.0 : 2.0} distance={10} position={[0, 0, -2]} />
    </group>
  );
}

export default function WormholePortalCanvas({ isActivating = false }: { isActivating?: boolean }) {
  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 50 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.3} />
        <Float speed={isActivating ? 4 : 1.5} rotationIntensity={0.3} floatIntensity={0.5}>
          <WormholeCore isActivating={isActivating} />
        </Float>
      </Canvas>
    </div>
  );
}
