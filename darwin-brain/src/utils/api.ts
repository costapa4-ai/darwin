import axios from 'axios';

// Dynamic API URL resolution
const getApiUrl = (): string => {
  const hostname = window.location.hostname;

  const hostMap: Record<string, string> = {
    localhost: 'http://localhost:8000',
    '127.0.0.1': 'http://localhost:8000',
    '192.168.1.117': 'http://192.168.1.117:8000',
    'myserver.local': 'http://myserver.local:8000',
  };

  return hostMap[hostname] || `http://${hostname}:8000`;
};

const getWsUrl = (): string => {
  const apiUrl = getApiUrl();
  return apiUrl.replace('http', 'ws') + '/ws';
};

export const API_URL = getApiUrl();
export const WS_URL = getWsUrl();

// Axios instance
export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API Methods
export const darwinApi = {
  // Consciousness
  async getStatus() {
    const { data } = await api.get('/api/v1/consciousness/status');
    return data;
  },

  async getActivities(limit = 20) {
    const { data } = await api.get(`/api/v1/consciousness/wake-activities?limit=${limit}`);
    return data;
  },

  async getDreams(limit = 20) {
    const { data } = await api.get(`/api/v1/consciousness/sleep-dreams?limit=${limit}`);
    return data;
  },

  async getCuriosities(limit = 20) {
    const { data } = await api.get(`/api/v1/consciousness/curiosities?limit=${limit}`);
    return data;
  },

  // Chat
  async sendMessage(message: string) {
    const { data } = await api.post('/api/v1/consciousness/chat', { message });
    return data;
  },

  async getChatHistory(limit = 50) {
    const { data } = await api.get(`/api/v1/consciousness/chat/history?limit=${limit}`);
    return data;
  },

  // Findings
  async getFindings() {
    const { data } = await api.get('/api/v1/findings');
    return data;
  },

  async getFindingsCount() {
    const { data } = await api.get('/api/v1/findings/count');
    return data;
  },

  async markFindingRead(id: string) {
    const { data } = await api.post(`/api/v1/findings/${id}/read`);
    return data;
  },

  // Mood
  async getMood() {
    const { data } = await api.get('/api/v1/mood/current');
    return data;
  },

  async getMoodHistory(limit = 20) {
    const { data } = await api.get(`/api/v1/mood/history?limit=${limit}`);
    return data;
  },

  // Existential
  async getExistentialStatus() {
    const { data } = await api.get('/api/v1/consciousness/existential');
    return data;
  },

  async getShowerThought() {
    const { data } = await api.get('/api/v1/consciousness/shower-thought');
    return data;
  },

  // Voice
  async synthesizeVoice(text: string, style = 'thoughtful') {
    const { data } = await api.post('/api/v1/voice/synthesize', { text, style });
    return data;
  },

  async speakDream(dreamContent: string) {
    const { data } = await api.post('/api/v1/voice/speak/dream', { dream_content: dreamContent });
    return data;
  },

  async speakThought(thought: string) {
    const { data } = await api.post('/api/v1/voice/speak/thought', { thought });
    return data;
  },

  async speakDiscovery(discovery: string, topic: string) {
    const { data } = await api.post('/api/v1/voice/speak/discovery', { discovery, topic });
    return data;
  },

  // Expeditions
  async getExpeditions(limit = 10) {
    const { data } = await api.get(`/api/v1/expeditions?limit=${limit}`);
    return data;
  },

  async getCurrentExpedition() {
    const { data } = await api.get('/api/v1/expeditions/current');
    return data;
  },

  // Diary
  async getDiaryEntries(limit = 10) {
    const { data } = await api.get(`/api/v1/diary?limit=${limit}`);
    return data;
  },

  async getTodayDiary() {
    const { data } = await api.get('/api/v1/diary/today');
    return data;
  },

  // Costs
  async getCostSummary() {
    const { data } = await api.get('/api/v1/costs/summary');
    return data;
  },

  // Financial
  async getFinancialStatus() {
    const { data } = await api.get('/api/v1/financial/status');
    return data;
  },

  // Health
  async getHealth() {
    const { data } = await api.get('/api/health');
    return data;
  },

  // Moltbook
  async getMoltbookFeed(limit = 20) {
    const { data } = await api.get(`/api/v1/moltbook/feed?limit=${limit}`);
    return data;
  },

  async refreshMoltbookFeed() {
    const { data } = await api.get('/api/v1/moltbook/refresh');
    return data;
  },

  async getMoltbookStatus() {
    const { data } = await api.get('/api/v1/moltbook/status');
    return data;
  },

  // Language Evolution
  async getLanguageEvolutionSummary() {
    const { data } = await api.get('/api/v1/language-evolution/summary');
    return data;
  },

  async getLanguageMetricsHistory(days = 30) {
    const { data } = await api.get(`/api/v1/language-evolution/metrics/history?days=${days}`);
    return data;
  },

  async getLanguageMetricsToday() {
    const { data } = await api.get('/api/v1/language-evolution/metrics/today');
    return data;
  },

  async getLanguageContent(limit = 50, offset = 0, type?: string) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (type) params.append('type', type);
    const { data } = await api.get(`/api/v1/language-evolution/content?${params}`);
    return data;
  },

  async getVocabularyGrowth(days = 30) {
    const { data } = await api.get(`/api/v1/language-evolution/vocabulary/growth?days=${days}`);
    return data;
  },

  async getTopicTrends(days = 30) {
    const { data } = await api.get(`/api/v1/language-evolution/topics/trends?days=${days}`);
    return data;
  },

  async getRecentVocabulary(limit = 50) {
    const { data } = await api.get(`/api/v1/language-evolution/vocabulary/recent?limit=${limit}`);
    return data;
  },
};

export default darwinApi;
