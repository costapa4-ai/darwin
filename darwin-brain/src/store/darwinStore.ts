import { create } from 'zustand';
import type {
  ThoughtNode,
  DarwinStatus,
  Activity,
  Dream,
  Discovery,
  Finding,
  ChatMessage,
} from '../types/darwin';

interface DarwinStore {
  // Connection State
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Consciousness State
  status: DarwinStatus;
  setStatus: (status: Partial<DarwinStatus>) => void;

  // Thought Nodes (The Brain)
  thoughts: ThoughtNode[];
  addThought: (thought: ThoughtNode) => void;
  removeThought: (id: string) => void;
  updateThought: (id: string, updates: Partial<ThoughtNode>) => void;
  focusedThoughtId: string | null;
  setFocusedThought: (id: string | null) => void;

  // Activities Feed
  activities: Activity[];
  addActivity: (activity: Activity) => void;

  // Dreams
  dreams: Dream[];
  addDream: (dream: Dream) => void;
  currentDream: Dream | null;
  setCurrentDream: (dream: Dream | null) => void;

  // Discoveries
  discoveries: Discovery[];
  addDiscovery: (discovery: Discovery) => void;

  // Findings
  findings: Finding[];
  setFindings: (findings: Finding[]) => void;
  unreadCount: number;

  // Chat
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;

  // Voice
  isSpeaking: boolean;
  setIsSpeaking: (speaking: boolean) => void;
  currentVoicePath: string | null;
  setCurrentVoicePath: (path: string | null) => void;

  // UI State
  showChat: boolean;
  toggleChat: () => void;
  showFindings: boolean;
  toggleFindings: () => void;
  showSettings: boolean;
  toggleSettings: () => void;
  cameraTarget: [number, number, number];
  setCameraTarget: (target: [number, number, number]) => void;
}

const initialStatus: DarwinStatus = {
  state: 'wake',
  mood: 'curious',
  personalityMode: 'irreverent',
  currentFocus: undefined,
  uptime: 0,
  cycleProgress: 0,
  activitiesCount: 0,
  discoveriesCount: 0,
  dreamsCount: 0,
  learningSessionsCount: 0,
};

export const useDarwinStore = create<DarwinStore>((set) => ({
  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Status
  status: initialStatus,
  setStatus: (status) =>
    set((state) => ({ status: { ...state.status, ...status } })),

  // Thoughts
  thoughts: [],
  addThought: (thought) =>
    set((state) => ({
      thoughts: [...state.thoughts.slice(-50), thought], // Keep last 50
    })),
  removeThought: (id) =>
    set((state) => ({
      thoughts: state.thoughts.filter((t) => t.id !== id),
    })),
  updateThought: (id, updates) =>
    set((state) => ({
      thoughts: state.thoughts.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
    })),
  focusedThoughtId: null,
  setFocusedThought: (id) => set({ focusedThoughtId: id }),

  // Activities
  activities: [],
  addActivity: (activity) =>
    set((state) => ({
      activities: [activity, ...state.activities.slice(0, 49)],
    })),

  // Dreams
  dreams: [],
  addDream: (dream) =>
    set((state) => ({
      dreams: [dream, ...state.dreams.slice(0, 19)],
    })),
  currentDream: null,
  setCurrentDream: (dream) => set({ currentDream: dream }),

  // Discoveries
  discoveries: [],
  addDiscovery: (discovery) =>
    set((state) => ({
      discoveries: [discovery, ...state.discoveries.slice(0, 49)],
    })),

  // Findings
  findings: [],
  setFindings: (findings) =>
    set({
      findings,
      unreadCount: findings.filter((f) => !f.read).length,
    }),
  unreadCount: 0,

  // Chat
  messages: [],
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),

  // Voice
  isSpeaking: false,
  setIsSpeaking: (speaking) => set({ isSpeaking: speaking }),
  currentVoicePath: null,
  setCurrentVoicePath: (path) => set({ currentVoicePath: path }),

  // UI
  showChat: false,
  toggleChat: () => set((state) => ({ showChat: !state.showChat })),
  showFindings: false,
  toggleFindings: () => set((state) => ({ showFindings: !state.showFindings })),
  showSettings: false,
  toggleSettings: () => set((state) => ({ showSettings: !state.showSettings })),
  cameraTarget: [0, 0, 0],
  setCameraTarget: (target) => set({ cameraTarget: target }),
}));

// Selectors for performance
export const selectStatus = (state: DarwinStore) => state.status;
export const selectThoughts = (state: DarwinStore) => state.thoughts;
export const selectActivities = (state: DarwinStore) => state.activities;
export const selectDreams = (state: DarwinStore) => state.dreams;
