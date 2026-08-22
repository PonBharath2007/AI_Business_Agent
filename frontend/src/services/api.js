import axios from 'axios';

const getBaseURL = () => {
  let url = import.meta.env.VITE_API_URL;

  if (!url) {
    url = import.meta.env.PROD
      ? 'https://ai-business-agent-ui7z.onrender.com/api'
      : 'http://localhost:8000/api';
  }

  url = url.trim().replace(/\/+$/, '');

  if (!url.endsWith('/api')) {
    url = `${url}/api`;
  }

  return url;
};

const api = axios.create({
  baseURL: getBaseURL(),
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