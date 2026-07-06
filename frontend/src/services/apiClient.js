/**
 * Client API centralisé : configure axios avec l'URL de base et
 * injecte automatiquement le token JWT s'il est présent.
 */
import axios from "axios";

// En déploiement "tout-en-un" (frontend + API sur le même domaine Vercel), l'URL
// relative /api/v1 suffit. Si le backend est hébergé séparément (ex: Docker sur
// Render/Railway/Fly.io pour conserver le scraping/OCR complets), définir
// VITE_API_BASE_URL au build pour pointer vers son URL absolue.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
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
