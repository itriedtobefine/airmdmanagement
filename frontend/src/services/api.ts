import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const metadataService = {
  getEntity: async (entityCode: string) => {
    const response = await api.get(`/meta/entities/${entityCode}`);
    return response.data;
  },
  
  createEntity: async (data: { entity_code: string; entity_name: string; json_schema: any; description?: string }) => {
    const response = await api.post('/meta/entities', data);
    return response.data;
  },
  
  updateEntity: async (entityCode: string, data: { entity_code: string; entity_name: string; json_schema: any; description?: string }) => {
    const response = await api.put(`/meta/entities/${entityCode}`, data);
    return response.data;
  },
  
  activateVersion: async (entityCode: string, version: number) => {
    const response = await api.post(`/meta/entities/${entityCode}/activate`, { version });
    return response.data;
  },
  
  getVersions: async (entityCode: string) => {
    const response = await api.get(`/meta/entities/${entityCode}/versions`);
    return response.data;
  },
};

export const recordService = {
  getRecords: async (entityCode: string, params?: { page?: number; limit?: number; sort_by?: string; sort_order?: string }) => {
    const response = await api.get(`/data/${entityCode}`, { params });
    return response.data;
  },
  
  getRecord: async (entityCode: string, recordId: string) => {
    const response = await api.get(`/data/${entityCode}/${recordId}`);
    return response.data;
  },
  
  createRecord: async (entityCode: string, data: any) => {
    const response = await api.post(`/data/${entityCode}`, { data });
    return response.data;
  },
  
  updateRecord: async (entityCode: string, recordId: string, data: any, version: number) => {
    const response = await api.put(`/data/${entityCode}/${recordId}`, { data, version });
    return response.data;
  },
  
  deleteRecord: async (entityCode: string, recordId: string) => {
    const response = await api.delete(`/data/${entityCode}/${recordId}`);
    return response.data;
  },
  
  getHistory: async (entityCode: string, recordId: string) => {
    const response = await api.get(`/data/${entityCode}/${recordId}/history`);
    return response.data;
  },
  
  restoreRecord: async (entityCode: string, recordId: string, targetVersion: number) => {
    const response = await api.post(`/data/${entityCode}/${recordId}/restore`, null, {
      params: { target_version: targetVersion },
    });
    return response.data;
  },
};

export default api;
