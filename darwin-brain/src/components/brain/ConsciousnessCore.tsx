import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useDarwinStore } from '../../store/darwinStore';

// Color mappings for states and moods
const stateColors = {
  wake: new THREE.Color('#f59e0b'),
  sleep: new THREE.Color('#6366f1'),
  dreaming: new THREE.Color('#a855f7'),
  thinking: new THREE.Color('#06b6d4'),
};

const moodColors = {
  curious: new THREE.Color('#00d4ff'),
  excited: new THREE.Color('#f472b6'),
  contemplative: new THREE.Color('#818cf8'),
  focused: new THREE.Color('#10b981'),
  tired: new THREE.Color('#6b7280'),
  mischievous: new THREE.Color('#f97316'),
  caffeinated: new THREE.Color('#fbbf24'),
  grumpy: new THREE.Color('#ef4444'),
  neutral: new THREE.Color('#94a3b8'),
};

export function ConsciousnessCore() {
  const meshRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  const status = useDarwinStore((state) => state.status);

  // Calculate colors based on state and mood
  const { mainColor, glowColor, innerColor } = useMemo(() => {
    const stateColor = stateColors[status.state] || stateColors.wake;
    const mood = moodColors[status.mood] || moodColors.neutral;

    return {
      mainColor: stateColor,
      glowColor: mood,
      innerColor: new THREE.Color().lerpColors(stateColor, mood, 0.5),
    };
  }, [status.state, status.mood]);

  // Animation
  useFrame((state) => {
    const time = state.clock.getElapsedTime();

    if (meshRef.current) {
      // Breathing effect
      const breathe = status.state === 'sleep'
        ? Math.sin(time * 0.5) * 0.1 + 1
        : Math.sin(time * 1.5) * 0.05 + 1;
      meshRef.current.scale.setScalar(breathe);

      // Subtle rotation
      meshRef.current.rotation.y = time * 0.1;
      meshRef.current.rotation.z = Math.sin(time * 0.3) * 0.1;
    }

    if (innerRef.current) {
      // Inner core spins faster
      innerRef.current.rotation.y = time * 0.5;
      innerRef.current.rotation.x = time * 0.3;
    }

    if (glowRef.current) {
      // Pulsing glow
      const pulse = Math.sin(time * 2) * 0.3 + 0.7;
      glowRef.current.scale.setScalar(1.5 + pulse * 0.2);
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = pulse * 0.3;
    }
  });

  // Distortion amount based on state
  const distortAmount = useMemo(() => {
    switch (status.state) {
      case 'dreaming': return 0.6;
      case 'thinking': return 0.4;
      case 'sleep': return 0.2;
      default: return 0.3;
    }
  }, [status.state]);

  // Animation speed based on state
  const speed = useMemo(() => {
    switch (status.state) {
      case 'dreaming': return 3;
      case 'thinking': return 5;
      case 'sleep': return 1;
      default: return 2;
    }
  }, [status.state]);

  return (
    <group>
      {/* Outer Glow */}
      <Sphere ref={glowRef} args={[2, 32, 32]}>
        <meshBasicMaterial
          color={glowColor}
          transparent
          opacity={0.2}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Main Core */}
      <Sphere ref={meshRef} args={[1.2, 64, 64]}>
        <MeshDistortMaterial
          color={mainColor}
          emissive={mainColor}
          emissiveIntensity={0.5}
          roughness={0.2}
          metalness={0.8}
          distort={distortAmount}
          speed={speed}
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* Inner Core */}
      <Sphere ref={innerRef} args={[0.6, 32, 32]}>
        <meshStandardMaterial
          color={innerColor}
          emissive={innerColor}
          emissiveIntensity={1}
          roughness={0.1}
          metalness={0.9}
        />
      </Sphere>

      {/* Point Light from Core */}
      <pointLight
        color={glowColor}
        intensity={2}
        distance={10}
        decay={2}
      />
    </group>
  );
}

export default ConsciousnessCore;
