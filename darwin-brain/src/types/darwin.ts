// Darwin Consciousness Types

export type ConsciousnessState = 'wake' | 'sleep' | 'dreaming' | 'thinking';

export type MoodType =
  | 'curious'
  | 'excited'
  | 'contemplative'
  | 'focused'
  | 'tired'
  | 'mischievous'
  | 'caffeinated'
  | 'grumpy'
  | 'neutral';

export type PersonalityMode =
  | 'irreverent'
  | 'cryptic'
  | 'caffeinated'
  | 'contemplative'
  | 'hacker'
  | 'poetic';

export interface ThoughtNode {
  id: string;
  type: 'thought' | 'memory' | 'dream' | 'discovery' | 'learning' | 'finding';
  content: string;
  title?: string;
  timestamp: Date;
  position: [number, number, number];
  connections: string[];
  intensity: number; // 0-1, affects glow
  metadata?: Record<string, unknown>;
}

export interface DarwinStatus {
  state: ConsciousnessState;
  mood: MoodType;
  personalityMode: PersonalityMode;
  currentFocus?: string;
  uptime: number;
  cycleProgress: number; // 0-100
  activitiesCount: number;
  discoveriesCount: number;
  dreamsCount: number;
  learningSessionsCount: number;
}

export interface Activity {
  id: string;
  type: 'code_optimization' | 'tool_creation' | 'idea_implementation' | 'curiosity_share' | 'self_improvement';
  title: string;
  description: string;
  timestamp: Date;
  insights?: string[];
  results?: Record<string, unknown>;
}

export interface Dream {
  id: string;
  narrative: string;
  themes: string[];
  insights: string[];
  timestamp: Date;
  intensity: number;
}

export interface Discovery {
  id: string;
  title: string;
  content: string;
  type: 'pattern' | 'security' | 'learning' | 'curiosity';
  severity: 'normal' | 'important' | 'critical';
  timestamp: Date;
  source?: string;
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  type: 'discovery' | 'insight' | 'anomaly' | 'suggestion' | 'curiosity';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  read: boolean;
  timestamp: Date;
  actions?: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'darwin';
  content: string;
  timestamp: Date;
  mood?: MoodType;
  hasVoice?: boolean;
  voicePath?: string;
}

export interface WebSocketMessage {
  type: string;
  payload: unknown;
  timestamp: string;
}
