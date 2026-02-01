import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useDarwinStore } from '../../store/darwinStore';

interface ParticleFieldProps {
  count?: number;
  radius?: number;
}

export function ParticleField({ count = 2000, radius = 15 }: ParticleFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const status = useDarwinStore((state) => state.status);

  // Generate particle positions
  const { positions, colors, sizes } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Spherical distribution with concentration toward center
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = Math.pow(Math.random(), 0.5) * radius; // More particles near center

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);

      // Vary colors
      const colorChoice = Math.random();
      if (colorChoice < 0.3) {
        // Cyan
        colors[i * 3] = 0;
        colors[i * 3 + 1] = 0.8;
        colors[i * 3 + 2] = 1;
      } else if (colorChoice < 0.6) {
        // Purple
        colors[i * 3] = 0.6;
        colors[i * 3 + 1] = 0.3;
        colors[i * 3 + 2] = 1;
      } else {
        // White/Blue
        colors[i * 3] = 0.8;
        colors[i * 3 + 1] = 0.9;
        colors[i * 3 + 2] = 1;
      }

      // Vary sizes
      sizes[i] = Math.random() * 0.05 + 0.01;
    }

    return { positions, colors, sizes };
  }, [count, radius]);

  // Animation
  useFrame((state) => {
    if (!pointsRef.current) return;

    const time = state.clock.getElapsedTime();
    const geometry = pointsRef.current.geometry;
    const positionAttr = geometry.getAttribute('position') as THREE.BufferAttribute;

    // Speed based on consciousness state
    const speed = status.state === 'sleep' ? 0.1 :
                  status.state === 'dreaming' ? 0.3 :
                  status.state === 'thinking' ? 0.5 : 0.2;

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      const x = positions[i3];
      const y = positions[i3 + 1];
      const z = positions[i3 + 2];

      // Calculate distance from center
      const dist = Math.sqrt(x * x + y * y + z * z);

      // Orbital motion
      const angle = time * speed * (1 / (dist + 1));

      // Apply rotation around Y axis
      const newX = x * Math.cos(angle) - z * Math.sin(angle);
      const newZ = x * Math.sin(angle) + z * Math.cos(angle);

      // Add some vertical oscillation
      const newY = y + Math.sin(time * 0.5 + i * 0.1) * 0.05;

      positionAttr.setXYZ(i, newX, newY, newZ);
    }

    positionAttr.needsUpdate = true;

    // Rotate the whole field slowly
    pointsRef.current.rotation.y = time * 0.02;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colors, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        vertexColors
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// Thought Particles - emerge from the core when Darwin has a thought
export function ThoughtParticles() {
  const groupRef = useRef<THREE.Group>(null);
  const activities = useDarwinStore((state) => state.activities);

  // Create particles for recent activities
  const particles = useMemo(() => {
    return activities.slice(0, 10).map((activity, i) => ({
      id: activity.id,
      position: [
        Math.sin(i * 0.7) * 3,
        Math.cos(i * 0.5) * 2 + 1,
        Math.sin(i * 1.2) * 3,
      ] as [number, number, number],
      color: activity.type === 'curiosity_share' ? '#a855f7' :
             activity.type === 'self_improvement' ? '#ef4444' :
             activity.type === 'idea_implementation' ? '#3b82f6' :
             '#06b6d4',
      scale: 0.2 + Math.random() * 0.1,
    }));
  }, [activities]);

  useFrame((state) => {
    if (!groupRef.current) return;
    const time = state.clock.getElapsedTime();

    groupRef.current.children.forEach((child, i) => {
      // Float effect
      child.position.y += Math.sin(time + i) * 0.001;
      child.rotation.y = time * 0.5;
    });
  });

  return (
    <group ref={groupRef}>
      {particles.map((p) => (
        <mesh key={p.id} position={p.position}>
          <icosahedronGeometry args={[p.scale, 0]} />
          <meshStandardMaterial
            color={p.color}
            emissive={p.color}
            emissiveIntensity={0.5}
            roughness={0.3}
            metalness={0.7}
          />
        </mesh>
      ))}
    </group>
  );
}

export default ParticleField;
