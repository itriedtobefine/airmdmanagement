import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Tables API
export const tablesApi = {
  getAll: () => api.get('/tables'),
  getById: (id) => api.get(`/tables/${id}`),
  create: (data) => api.post('/tables', data),
  update: (id, data) => api.put(`/tables/${id}`, data),
  delete: (id) => api.delete(`/tables/${id}`),
  getColumns: (tableId) => api.get(`/tables/${tableId}/columns`),
  getRecords: (tableId, skip = 0, limit = 100) => 
    api.get(`/tables/${tableId}/records?skip=${skip}&limit=${limit}`),
  importCSV: (tableId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/tables/${tableId}/import-csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  exportCSV: (tableId) => api.get(`/tables/${tableId}/export-csv`, {
    responseType: 'blob',
  }),
};

// Columns API
export const columnsApi = {
  create: (data) => api.post('/columns', data),
  update: (id, data) => api.put(`/columns/${id}`, data),
  delete: (id) => api.delete(`/columns/${id}`),
};

// Records API
export const recordsApi = {
  create: (data) => api.post('/records', data),
  update: (id, data) => api.put(`/records/${id}`, data),
  delete: (id) => api.delete(`/records/${id}`),
};

export default api;
