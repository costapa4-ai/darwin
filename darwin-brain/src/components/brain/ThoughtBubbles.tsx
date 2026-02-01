import { useRef, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, Billboard } from '@react-three/drei';
import * as THREE from 'three';
import { useDarwinStore } from '../../store/darwinStore';
import { motion } from 'framer-motion';

interface ThoughtBubble {
  id: string;
  content: string;
  type: 'thought' | 'discovery' | 'dream' | 'curiosity';
  position: THREE.Vector3;
  createdAt: number;
  velocity: THREE.Vector3;
}

const typeColors = {
  thought: '#06b6d4',
  discovery: '#10b981',
  dream: '#a855f7',
  curiosity: '#f59e0b',
};

const typeEmojis = {
  thought: '💭',
  discovery: '🔍',
  dream: '🌙',
  curiosity: '🤔',
};

export function ThoughtBubbles() {
  const groupRef = useRef<THREE.Group>(null);
  const [bubbles, setBubbles] = useState<ThoughtBubble[]>([]);
  const activities = useDarwinStore((state) => state.activities);
  const discoveries = useDarwinStore((state) => state.discoveries);

  // Create bubbles from new activities/discoveries
  useEffect(() => {
    if (activities.length > 0) {
      const latest = activities[0];
      const newBubble: ThoughtBubble = {
        id: latest.id,
        content: latest.title || 'New thought...',
        type: 'thought',
        position: new THREE.Vector3(
          (Math.random() - 0.5) * 2,
          -1,
          (Math.random() - 0.5) * 2
        ),
        createdAt: Date.now(),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.01,
          0.02 + Math.random() * 0.01,
          (Math.random() - 0.5) * 0.01
        ),
      };

      setBubbles((prev) => [...prev.slice(-5), newBubble]);
    }
  }, [activities.length]);

  useEffect(() => {
    if (discoveries.length > 0) {
      const latest = discoveries[0];
      const newBubble: ThoughtBubble = {
        id: latest.id,
        content: latest.title,
        type: 'discovery',
        position: new THREE.Vector3(
          (Math.random() - 0.5) * 2,
          -1,
          (Math.random() - 0.5) * 2
        ),
        createdAt: Date.now(),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.01,
          0.025,
          (Math.random() - 0.5) * 0.01
        ),
      };

      setBubbles((prev) => [...prev.slice(-5), newBubble]);
    }
  }, [discoveries.length]);

  // Update bubble positions
  useFrame(() => {
    const now = Date.now();

    setBubbles((prev) =>
      prev
        .map((bubble) => {
          const age = now - bubble.createdAt;

          // Remove old bubbles
          if (age > 10000) return null;

          // Update position
          bubble.position.add(bubble.velocity);

          // Slow down vertical velocity
          bubble.velocity.y *= 0.995;

          return bubble;
        })
        .filter(Boolean) as ThoughtBubble[]
    );
  });

  return (
    <group ref={groupRef}>
      {bubbles.map((bubble) => (
        <ThoughtBubbleItem
          key={bubble.id}
          bubble={bubble}
        />
      ))}
    </group>
  );
}

interface ThoughtBubbleItemProps {
  bubble: ThoughtBubble;
}

function ThoughtBubbleItem({ bubble }: ThoughtBubbleItemProps) {
  const age = Date.now() - bubble.createdAt;
  const opacity = Math.max(0, 1 - age / 10000);
  const color = typeColors[bubble.type];
  const emoji = typeEmojis[bubble.type];

  return (
    <Billboard position={bubble.position} follow lockX={false} lockY={false} lockZ={false}>
      <Html
        transform
        occlude
        style={{
          pointerEvents: 'none',
          opacity,
          transition: 'opacity 0.3s',
        }}
      >
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          className="px-3 py-2 rounded-lg text-sm max-w-[200px] text-center"
          style={{
            background: `linear-gradient(135deg, ${color}20, ${color}10)`,
            border: `1px solid ${color}40`,
            backdropFilter: 'blur(8px)',
            color: '#fff',
            boxShadow: `0 0 20px ${color}30`,
          }}
        >
          <span className="mr-1">{emoji}</span>
          <span className="text-xs">{bubble.content}</span>
        </motion.div>
      </Html>
    </Billboard>
  );
}

// Shower Thought Display - Special component for shower thoughts
export function ShowerThoughtDisplay() {
  const [thought, setThought] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  // Listen for shower thoughts from WebSocket or periodic fetch
  useEffect(() => {
    // This would be connected to WebSocket events
    const interval = setInterval(async () => {
      // Random chance to show a thought (for demo)
      if (Math.random() > 0.95 && !visible) {
        try {
          const response = await fetch('/api/v1/consciousness/shower-thought');
          const data = await response.json();
          if (data.thought) {
            setThought(data.thought);
            setVisible(true);
            setTimeout(() => setVisible(false), 8000);
          }
        } catch {
          // Ignore errors
        }
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [visible]);

  if (!visible || !thought) return null;

  return (
    <Billboard position={[0, 3, 0]}>
      <Html transform occlude>
        <motion.div
          initial={{ scale: 0, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0, y: -20 }}
          className="px-4 py-3 rounded-xl text-center max-w-[300px]"
          style={{
            background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(59, 130, 246, 0.2))',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            backdropFilter: 'blur(12px)',
            color: '#fff',
            boxShadow: '0 0 30px rgba(168, 85, 247, 0.3)',
          }}
        >
          <div className="text-lg mb-1">🚿💭</div>
          <div className="text-sm italic">"{thought}"</div>
          <div className="text-xs mt-2 opacity-60">- Darwin's shower thought</div>
        </motion.div>
      </Html>
    </Billboard>
  );
}

export default ThoughtBubbles;
