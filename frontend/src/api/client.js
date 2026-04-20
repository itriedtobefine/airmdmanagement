import axios from 'axios';

const API_BASE_URL = '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Users API
export const usersApi = {
  getAll: () => apiClient.get('/users/'),
  getById: (id) => apiClient.get(`/users/${id}`),
  create: (data) => apiClient.post('/users/', data),
  update: (id, data) => apiClient.put(`/users/${id}`, data),
  delete: (id) => apiClient.delete(`/users/${id}`),
};

// Projects API
export const projectsApi = {
  getAll: () => apiClient.get('/projects/'),
  getById: (id) => apiClient.get(`/projects/${id}`),
  getSummary: (id) => apiClient.get(`/projects/${id}/summary`),
  create: (data) => apiClient.post('/projects/', data),
  update: (id, data) => apiClient.put(`/projects/${id}`, data),
  delete: (id) => apiClient.delete(`/projects/${id}`),
};

// Tasks API
export const tasksApi = {
  getAll: (projectId = null) => {
    const url = projectId ? `/tasks/?project_id=${projectId}` : '/tasks/';
    return apiClient.get(url);
  },
  getById: (id) => apiClient.get(`/tasks/${id}`),
  getSummary: (id) => apiClient.get(`/tasks/${id}/summary`),
  create: (data) => apiClient.post('/tasks/', data),
  update: (id, data) => apiClient.put(`/tasks/${id}`, data),
  delete: (id) => apiClient.delete(`/tasks/${id}`),
};

// Time Entries API
export const timeEntriesApi = {
  start: (data) => apiClient.post('/time-entries/start/', data),
  stop: (entryId) => apiClient.post('/time-entries/stop/', { entry_id: entryId }),
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.projectId) queryParams.append('project_id', params.projectId);
    if (params.taskId) queryParams.append('task_id', params.taskId);
    if (params.userId) queryParams.append('user_id', params.userId);
    return apiClient.get(`/time-entries/?${queryParams.toString()}`);
  },
  getSummary: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.projectId) queryParams.append('project_id', params.projectId);
    if (params.taskId) queryParams.append('task_id', params.taskId);
    if (params.userId) queryParams.append('user_id', params.userId);
    return apiClient.get(`/time-entries/summary/?${queryParams.toString()}`);
  },
  getById: (id) => apiClient.get(`/time-entries/${id}`),
  delete: (id) => apiClient.delete(`/time-entries/${id}`),
};

export default apiClient;
