import axios, { AxiosResponse } from 'axios';

// Base API configuration
const API_BASE = import.meta.env.PROD
  ? '/api'
  : import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30 second timeout for file uploads
  withCredentials: true,
});

// Request interceptor for logging and auth
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('Response Error:', error.response?.status, error.response?.data);
    
    if (error.response?.status === 401) {
      // Redirect to login on authentication failure
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default api;
