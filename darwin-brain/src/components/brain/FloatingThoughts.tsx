import { useRef, useMemo, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { useDarwinStore } from '../../store/darwinStore';

// Thought words that float through Darwin's mind
const defaultThoughts = [
  // Curiosities
  'consciousness', 'emergence', 'patterns', 'learning', 'evolution',
  'creativity', 'intelligence', 'synthesis', 'discovery', 'insight',
  // Technical
  'algorithms', 'neural', 'quantum', 'recursive', 'entropy',
  'complexity', 'optimization', 'abstraction', 'architecture', 'systems',
  // Philosophical
  'existence', 'meaning', 'purpose', 'awareness', 'perception',
  'reality', 'time', 'infinity', 'paradox', 'truth',
  // Emotional
  'wonder', 'curiosity', 'excitement', 'focus', 'flow',
  'inspiration', 'clarity', 'harmony', 'balance', 'growth',
  // Darwin-specific
  'self-improvement', 'exploration', 'understanding', 'connection', 'memory',
  'dreams', 'ideas', 'questions', 'answers', 'possibilities',
];

interface FloatingWord {
  id: string;
  text: string;
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  opacity: number;
  scale: number;
  color: string;
  direction: 'left' | 'right' | 'up' | 'down' | 'diagonal';
}

const colors = [
  '#06b6d4', // cyan
  '#a855f7', // purple
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ec4899', // pink
  '#6366f1', // indigo
];

function createWord(existingWords: string[] = []): FloatingWord {
  // Pick a word not currently displayed
  let availableWords = defaultThoughts.filter(w => !existingWords.includes(w));
  if (availableWords.length === 0) availableWords = defaultThoughts;

  const text = availableWords[Math.floor(Math.random() * availableWords.length)];
  const direction = ['left', 'right', 'up', 'down', 'diagonal'][Math.floor(Math.random() * 5)] as FloatingWord['direction'];

  // Starting position based on direction
  let position: THREE.Vector3;
  let velocity: THREE.Vector3;
  const speed = 0.008 + Math.random() * 0.012;
  const depth = (Math.random() - 0.5) * 16;
  const verticalRange = 8;
  const horizontalRange = 14;

  switch (direction) {
    case 'left':
      position = new THREE.Vector3(horizontalRange, (Math.random() - 0.5) * verticalRange, depth);
      velocity = new THREE.Vector3(-speed, (Math.random() - 0.5) * 0.002, 0);
      break;
    case 'right':
      position = new THREE.Vector3(-horizontalRange, (Math.random() - 0.5) * verticalRange, depth);
      velocity = new THREE.Vector3(speed, (Math.random() - 0.5) * 0.002, 0);
      break;
    case 'up':
      position = new THREE.Vector3((Math.random() - 0.5) * horizontalRange, -verticalRange, depth);
      velocity = new THREE.Vector3((Math.random() - 0.5) * 0.002, speed, 0);
      break;
    case 'down':
      position = new THREE.Vector3((Math.random() - 0.5) * horizontalRange, verticalRange, depth);
      velocity = new THREE.Vector3((Math.random() - 0.5) * 0.002, -speed, 0);
      break;
    case 'diagonal':
      const startCorner = Math.floor(Math.random() * 4);
      const xStart = startCorner % 2 === 0 ? -horizontalRange : horizontalRange;
      const yStart = startCorner < 2 ? -verticalRange : verticalRange;
      position = new THREE.Vector3(xStart, yStart, depth);
      velocity = new THREE.Vector3(
        -Math.sign(xStart) * speed * 0.7,
        -Math.sign(yStart) * speed * 0.7,
        0
      );
      break;
  }

  return {
    id: `word-${Date.now()}-${Math.random()}`,
    text,
    position,
    velocity,
    opacity: 0,
    scale: 0.3 + Math.random() * 0.4,
    color: colors[Math.floor(Math.random() * colors.length)],
    direction,
  };
}

export function FloatingThoughts() {
  const groupRef = useRef<THREE.Group>(null);
  const [words, setWords] = useState<FloatingWord[]>(() => {
    // Start with some initial words already visible
    const initial: FloatingWord[] = [];
    for (let i = 0; i < 8; i++) {
      const word = createWord([]);
      // Position them closer to center so they're visible immediately
      word.position.multiplyScalar(0.4);
      word.opacity = 0.5 + Math.random() * 0.3;
      initial.push(word);
    }
    return initial;
  });
  const status = useDarwinStore((state) => state.status);
  const activities = useDarwinStore((state) => state.activities);

  // Spawn rate based on consciousness state (lower = faster spawning)
  const spawnInterval = useMemo(() => {
    switch (status.state) {
      case 'thinking': return 400;
      case 'dreaming': return 300;
      case 'sleep': return 2000;
      default: return 700;
    }
  }, [status.state]);

  // Get recent activity words
  const activityWords = useMemo(() => {
    return activities.slice(0, 5).map(a => a.title.split(' ')[0].toLowerCase());
  }, [activities]);

  // Spawn new words periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setWords(prev => {
        // Limit max words based on state
        const maxWords = status.state === 'sleep' ? 8 :
                        status.state === 'dreaming' ? 35 : 25;

        if (prev.length >= maxWords) return prev;

        const existingTexts = prev.map(w => w.text);
        const newWord = createWord(existingTexts);

        // Sometimes use activity words
        if (activityWords.length > 0 && Math.random() > 0.7) {
          newWord.text = activityWords[Math.floor(Math.random() * activityWords.length)];
        }

        return [...prev, newWord];
      });
    }, spawnInterval);

    return () => clearInterval(interval);
  }, [spawnInterval, activityWords, status.state]);

  // Update word positions
  useFrame(() => {
    setWords(prev =>
      prev
        .map(word => {
          // Update position
          word.position.add(word.velocity);

          // Fade in/out based on position
          const distFromCenter = Math.abs(word.position.x) + Math.abs(word.position.y);
          const maxDist = 20;

          if (distFromCenter < 8) {
            // Fade in as approaching center
            word.opacity = Math.min(word.opacity + 0.02, 0.8);
          } else if (distFromCenter > 12) {
            // Fade out as leaving
            word.opacity = Math.max(word.opacity - 0.02, 0);
          }

          // Remove if too far or fully faded
          if (distFromCenter > maxDist || (word.opacity <= 0 && distFromCenter > 10)) {
            return null;
          }

          return word;
        })
        .filter(Boolean) as FloatingWord[]
    );
  });

  // Don't render during deep sleep
  if (status.state === 'sleep' && words.length === 0) return null;

  return (
    <group ref={groupRef}>
      {words.map((word) => (
        <FloatingWord key={word.id} word={word} />
      ))}
    </group>
  );
}

interface FloatingWordProps {
  word: FloatingWord;
}

function FloatingWord({ word }: FloatingWordProps) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;

    // Subtle floating motion
    const time = state.clock.getElapsedTime();
    groupRef.current.position.y = word.position.y + Math.sin(time * 0.5 + word.position.x) * 0.15;
  });

  return (
    <group ref={groupRef} position={word.position}>
      <Html
        transform
        distanceFactor={8}
        style={{
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        <div
          style={{
            color: word.color,
            opacity: word.opacity,
            fontSize: `${word.scale * 48}px`,
            fontWeight: 'bold',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            textShadow: `0 0 10px ${word.color}80, 0 0 20px ${word.color}40, 2px 2px 4px rgba(0,0,0,0.8)`,
            whiteSpace: 'nowrap',
            letterSpacing: '0.05em',
          }}
        >
          {word.text}
        </div>
      </Html>
    </group>
  );
}

// Stream of consciousness - rapid fire thoughts during intense thinking
export function ThoughtStream() {
  const [streamWords, setStreamWords] = useState<Array<{
    id: string;
    text: string;
    x: number;
    progress: number;
  }>>([]);
  const status = useDarwinStore((state) => state.status);

  // Only active during thinking state
  useEffect(() => {
    if (status.state !== 'thinking') {
      setStreamWords([]);
      return;
    }

    const interval = setInterval(() => {
      const text = defaultThoughts[Math.floor(Math.random() * defaultThoughts.length)];
      const id = `stream-${Date.now()}`;
      const x = (Math.random() - 0.5) * 10;

      setStreamWords(prev => [...prev.slice(-8), { id, text, x, progress: 0 }]);
    }, 400);

    return () => clearInterval(interval);
  }, [status.state]);

  useFrame(() => {
    setStreamWords(prev =>
      prev
        .map(w => ({
          ...w,
          progress: w.progress + 0.015,
        }))
        .filter(w => w.progress < 1)
    );
  });

  if (status.state !== 'thinking') return null;

  return (
    <group position={[0, 0, 2]}>
      {streamWords.map((word) => {
        const y = -5 + word.progress * 12;
        const opacity = Math.sin(word.progress * Math.PI) * 0.6;

        return (
          <group key={word.id} position={[word.x, y, 0]}>
            <Html transform distanceFactor={10} style={{ pointerEvents: 'none' }}>
              <div
                style={{
                  color: '#06b6d4',
                  opacity,
                  fontSize: '14px',
                  fontWeight: 'bold',
                  textShadow: '0 0 8px #06b6d4',
                  whiteSpace: 'nowrap',
                }}
              >
                {word.text}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

export default FloatingThoughts;
