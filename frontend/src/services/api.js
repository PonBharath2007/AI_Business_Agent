import axios from 'axios';

const rawBaseURL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'https://ai-business-agent-ui7z.onrender.com/api' : 'http://localhost:8000/api');

const cleanBaseURL = (rawBaseURL || '').replace(/\/+$/, '');
export const API_URL = cleanBaseURL.endsWith('/api') ? cleanBaseURL : `${cleanBaseURL}/api`;

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
    }

    return Promise.reject(error);
  }
);

export default api;

// SMS Queue & Android Gateway API Helpers
export const sendSms = (data) => api.post('/sms/send', data);
export const getPendingSms = () => api.get('/sms/pending');
export const getSmsLogs = (params) => api.get('/sms', { params });
export const getSmsDetails = (smsId) => api.get(`/sms/${smsId}`);
export const claimSms = (smsId) => api.post(`/sms/${smsId}/claim`);