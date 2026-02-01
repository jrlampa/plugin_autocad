import axios from 'axios';

// --- Global Interceptor for Resilience ---
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;

      // Dispatch custom events for UI to React
      if (status === 429) {
        window.dispatchEvent(new CustomEvent('api-error', {
          detail: { type: 'RATE_LIMIT', message: 'Você está indo rápido demais! Aguarde um momento.' }
        }));
      } else if (status === 503) {
        window.dispatchEvent(new CustomEvent('api-error', {
          detail: { type: 'CIRCUIT_BREAKER', message: 'Serviço temporariamente indisponível (Proteção ativa).' }
        }));
      }
    }
    return Promise.reject(error);
  }
);

// Em produção, usamos a mesma origem (porta dinâmica do backend).
// Em dev, você pode sobrescrever com VITE_API_URL.
const API_BASE = (import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`).replace(
  /\/+$/,
  ''
);

export const api = {
  // Decifra entradas inteligentes (UTM, GMS, Lat/Lon)
  smartGeocode: async (text) => {
    const response = await axios.get(`${API_BASE}/tools/geocode`, {
      params: { query: text },
    });
    return response.data;
  },

  checkHealth: async () => {
    try {
      const response = await axios.get(`${API_BASE}/health`, { timeout: 2000 });
      return response.data && response.data.status === 'ok';
    } catch {
      return false;
    }
  },
};
