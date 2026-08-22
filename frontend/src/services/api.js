import axios from 'axios';

// Resolve base API URL:
// 1. Vite environment variable VITE_API_URL (if provided)
// 2. Production fallback to Render backend
// 3. Development fallback to localhost:8000/api
import axios from 'axios';

// Resolve base API URL
const getBaseURL = () => {
  let url = import.meta.env.VITE_API_URL;

  if (!url) {
    url = import.meta.env.PROD
      ? 'https://ai-business-agent-ui7z.onrender.com/api'
      : 'http://localhost:8000/api';
  }

  return url.replace(/\/$/, '');
};

const api = axios.create({
  baseURL: getBaseURL(),
});

export default api;

  return url.replace(/\/$/, '');
};
  url = url.trim().replace(/\/+$/, '');
  if (!url.endsWith('/api')) {
    url = `${url}/api`;
  }
  return url;
};

const api = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json'
  }
});
// Request interceptor for injecting JWT token
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

// Response interceptor for handling 401 unauth
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn('Session expired or unauthorized token detected. Cleaning token.');
      if (localStorage.getItem('token')) {
        localStorage.removeItem('token');
      }
    }
    return Promise.reject(error);
  }
);

export default api;

