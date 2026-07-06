/**
 * Client API centralisé : configure axios avec l'URL de base et
 * injecte automatiquement le token JWT s'il est présent.
 */
import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
    return Promise.reject(error);
  }
);

export default apiClient;
