import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { QuadraticBezierLine } from '@react-three/drei';
import * as THREE from 'three';
import { useDarwinStore } from '../../store/darwinStore';

interface NeuralConnectionsProps {
  nodeCount?: number;
}

// Generate random positions for neural nodes
function generateNodePositions(count: number, radius: number): THREE.Vector3[] {
  const positions: THREE.Vector3[] = [];

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = (Math.random() * 0.5 + 0.5) * radius;

    positions.push(
      new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      )
    );
  }

  return positions;
}

// Generate connections between nearby nodes
function generateConnections(
  positions: THREE.Vector3[],
  maxDistance: number,
  maxConnections: number
): [number, number][] {
  const connections: [number, number][] = [];

  for (let i = 0; i < positions.length; i++) {
    let connectionCount = 0;

    for (let j = i + 1; j < positions.length && connectionCount < maxConnections; j++) {
      const dist = positions[i].distanceTo(positions[j]);

      if (dist < maxDistance && Math.random() > 0.5) {
        connections.push([i, j]);
        connectionCount++;
      }
    }
  }

  return connections;
}

export function NeuralConnections({ nodeCount = 30 }: NeuralConnectionsProps) {
  const groupRef = useRef<THREE.Group>(null);
  const status = useDarwinStore((state) => state.status);

  // Generate neural network structure
  const { nodes, connections } = useMemo(() => {
    const nodes = generateNodePositions(nodeCount, 6);
    const connections = generateConnections(nodes, 4, 3);
    return { nodes, connections };
  }, [nodeCount]);

  // Color based on state
  const connectionColor = useMemo(() => {
    switch (status.state) {
      case 'dreaming': return '#a855f7';
      case 'sleep': return '#6366f1';
      case 'thinking': return '#06b6d4';
      default: return '#3b82f6';
    }
  }, [status.state]);

  // Animation
  useFrame((state) => {
    if (!groupRef.current) return;
    const time = state.clock.getElapsedTime();

    // Subtle pulsing rotation
    groupRef.current.rotation.y = Math.sin(time * 0.1) * 0.1;
    groupRef.current.rotation.x = Math.cos(time * 0.15) * 0.05;
  });

  return (
    <group ref={groupRef}>
      {/* Neural Nodes */}
      {nodes.map((pos, i) => (
        <NeuralNode
          key={`node-${i}`}
          position={pos}
          index={i}
          color={connectionColor}
        />
      ))}

      {/* Connections */}
      {connections.map(([i, j], idx) => (
        <NeuralConnection
          key={`conn-${idx}`}
          start={nodes[i]}
          end={nodes[j]}
          color={connectionColor}
          index={idx}
        />
      ))}
    </group>
  );
}

interface NeuralNodeProps {
  position: THREE.Vector3;
  index: number;
  color: string;
}

function NeuralNode({ position, index, color }: NeuralNodeProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.getElapsedTime();

    // Pulsing scale
    const pulse = Math.sin(time * 2 + index * 0.5) * 0.2 + 1;
    meshRef.current.scale.setScalar(pulse);
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.8}
        transparent
        opacity={0.8}
      />
    </mesh>
  );
}

interface NeuralConnectionProps {
  start: THREE.Vector3;
  end: THREE.Vector3;
  color: string;
  index: number;
}

function NeuralConnection({ start, end, color, index }: NeuralConnectionProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const lineRef = useRef<any>(null);

  // Calculate midpoint with some offset for curve
  const midPoint = useMemo(() => {
    const mid = new THREE.Vector3().lerpVectors(start, end, 0.5);
    // Add perpendicular offset for curve
    const offset = new THREE.Vector3(
      (Math.random() - 0.5) * 0.5,
      (Math.random() - 0.5) * 0.5,
      (Math.random() - 0.5) * 0.5
    );
    return mid.add(offset);
  }, [start, end]);

  useFrame((state) => {
    if (!lineRef.current) return;
    const time = state.clock.getElapsedTime();

    // Pulsing opacity for "signal" effect
    if (lineRef.current.material) {
      lineRef.current.material.opacity = Math.sin(time * 3 + index) * 0.3 + 0.4;
    }
  });

  return (
    <QuadraticBezierLine
      ref={lineRef}
      start={start}
      end={end}
      mid={midPoint}
      color={color}
      lineWidth={1}
      transparent
      opacity={0.4}
    />
  );
}

// Signal Pulses - particles that travel along connections
export function SignalPulses() {
  const groupRef = useRef<THREE.Group>(null);
  const status = useDarwinStore((state) => state.status);

  // Only show when active
  if (status.state === 'sleep') return null;

  return (
    <group ref={groupRef}>
      {/* Signal particles would be animated here */}
    </group>
  );
}

export default NeuralConnections;
