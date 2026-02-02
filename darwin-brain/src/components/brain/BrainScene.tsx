import { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
  OrbitControls,
  PerspectiveCamera,
  Stars,
} from '@react-three/drei';
import {
  EffectComposer,
  Bloom,
  ChromaticAberration,
  Vignette,
} from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';

import { ConsciousnessCore } from './ConsciousnessCore';
import { ParticleField, ThoughtParticles } from './ParticleField';
import { NeuralConnections } from './NeuralConnections';
import { ThoughtBubbles, ShowerThoughtDisplay } from './ThoughtBubbles';
import { FloatingThoughts, ThoughtStream } from './FloatingThoughts';
import { useDarwinStore } from '../../store/darwinStore';

// Loading indicator
function Loader() {
  return (
    <mesh>
      <sphereGeometry args={[0.5, 16, 16]} />
      <meshBasicMaterial color="#06b6d4" wireframe />
    </mesh>
  );
}

// Camera controller that responds to state changes
function CameraController() {
  return null;
}

// Orbit controls with settings from store
function SceneOrbitControls() {
  const autoRotate = useDarwinStore((state) => state.autoRotate);

  return (
    <OrbitControls
      enablePan={false}
      enableZoom={true}
      minDistance={4}
      maxDistance={20}
      autoRotate={autoRotate}
      autoRotateSpeed={0.3}
      dampingFactor={0.05}
      enableDamping
    />
  );
}

// Scene lighting based on consciousness state
function DynamicLighting() {
  const ambientRef = useRef<THREE.AmbientLight>(null);
  const directionalRef = useRef<THREE.DirectionalLight>(null);
  const status = useDarwinStore((state) => state.status);

  useFrame(() => {
    if (!ambientRef.current || !directionalRef.current) return;

    // Adjust lighting based on state
    const targetIntensity = status.state === 'sleep' ? 0.1 :
                            status.state === 'dreaming' ? 0.3 :
                            0.5;

    // Lerp to target
    ambientRef.current.intensity += (targetIntensity - ambientRef.current.intensity) * 0.02;
  });

  return (
    <>
      <ambientLight ref={ambientRef} intensity={0.3} color="#1e3a5f" />
      <directionalLight
        ref={directionalRef}
        position={[5, 5, 5]}
        intensity={0.5}
        color="#ffffff"
      />
      <pointLight position={[-5, -5, -5]} intensity={0.2} color="#6366f1" />
    </>
  );
}

// Post-processing effects
function Effects() {
  const status = useDarwinStore((state) => state.status);
  const bloomSetting = useDarwinStore((state) => state.bloomIntensity);

  // Base bloom from settings (0-100 mapped to 0-2)
  const baseBloom = (bloomSetting / 100) * 2;

  // State-based multiplier (dreaming/sleep adds extra bloom)
  const stateMultiplier = status.state === 'dreaming' ? 1.5 :
                          status.state === 'sleep' ? 1.2 :
                          1.0;

  const bloomIntensity = baseBloom * stateMultiplier;

  return (
    <EffectComposer>
      <Bloom
        intensity={bloomIntensity}
        luminanceThreshold={0.2}
        luminanceSmoothing={0.9}
        mipmapBlur
      />
      <ChromaticAberration
        blendFunction={BlendFunction.NORMAL}
        offset={[0.001, 0.001]}
      />
      <Vignette
        offset={0.3}
        darkness={0.7}
        eskil={false}
      />
    </EffectComposer>
  );
}

// Main scene content
function SceneContent() {
  const groupRef = useRef<THREE.Group>(null);
  const particleDensity = useDarwinStore((state) => state.particleDensity);

  // Calculate particle count from density setting (0-100 maps to 100-2000)
  const particleCount = Math.max(100, Math.round((particleDensity / 100) * 2000));

  // Subtle scene rotation
  useFrame((state) => {
    if (!groupRef.current) return;
    const time = state.clock.getElapsedTime();
    groupRef.current.rotation.y = Math.sin(time * 0.05) * 0.1;
  });

  return (
    <group ref={groupRef}>
      {/* Core consciousness orb */}
      <ConsciousnessCore />

      {/* Neural network connections */}
      <NeuralConnections nodeCount={40} />

      {/* Ambient particles - count based on settings */}
      <ParticleField count={particleCount} radius={12} />

      {/* Activity-based thought particles */}
      <ThoughtParticles />

      {/* Emerging thought bubbles */}
      <ThoughtBubbles />

      {/* Shower thought display */}
      <ShowerThoughtDisplay />

      {/* Floating thought words */}
      <FloatingThoughts />

      {/* Rapid thought stream during thinking */}
      <ThoughtStream />
    </group>
  );
}

// Background stars/space environment
function SpaceBackground() {
  const status = useDarwinStore((state) => state.status);

  // More stars during sleep/dream
  const starCount = status.state === 'sleep' ? 8000 :
                    status.state === 'dreaming' ? 10000 :
                    5000;

  return (
    <Stars
      radius={50}
      depth={50}
      count={starCount}
      factor={4}
      saturation={0.5}
      fade
      speed={status.state === 'dreaming' ? 2 : 0.5}
    />
  );
}

// Main Brain Scene Canvas
export function BrainScene() {
  return (
    <div className="absolute inset-0 z-0">
      <Canvas
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
        }}
        dpr={[1, 2]}
      >
        <color attach="background" args={['#030712']} />

        <PerspectiveCamera
          makeDefault
          position={[0, 2, 8]}
          fov={60}
          near={0.1}
          far={100}
        />

        <SceneOrbitControls />

        <Suspense fallback={<Loader />}>
          <CameraController />
          <DynamicLighting />
          <SpaceBackground />
          <SceneContent />
          <Effects />
        </Suspense>
      </Canvas>
    </div>
  );
}

export default BrainScene;
