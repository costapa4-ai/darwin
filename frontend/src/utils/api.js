import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export const createTask = async (taskData) => {
  const response = await api.post('/api/tasks', taskData);
  return response.data;
};

export const getTask = async (taskId) => {
  const response = await api.get(`/api/tasks/${taskId}`);
  return response.data;
};

export const listTasks = async () => {
  const response = await api.get('/api/tasks');
  return response.data;
};

export const getGenerations = async (taskId) => {
  const response = await api.get(`/api/generations/${taskId}`);
  return response.data;
};

export const getMetrics = async () => {
  const response = await api.get('/api/metrics');
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get('/api/health');
  return response.data;
};
