import axios from 'axios';

// ISO 27001 Security: Tokens are stored in private module scope, NOT in window global.
let _masterToken = null;
let _sessionToken = null;

export const setAuthToken = (token) => {
  _masterToken = token;
};

// --- Global Interceptor for Resilience & Auth ---
axios.interceptors.request.use((config) => {
  // ISO 27001: Prefer short-lived session token over master token
  const token = _sessionToken || _masterToken;
  if (token) {
    config.headers['X-SisRua-Token'] = token;
  }
  return config;
});

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;

      // ISO 27001: Session expired or invalid
      if (status === 401) {
        console.warn('Security: Session invalid or expired. Clearing credentials.');
        _sessionToken = null;
        _masterToken = null; // Wipe everything on auth error
      }

      // Dispatch custom events for UI to React
      if (status === 429) {
        window.dispatchEvent(
          new CustomEvent('api-error', {
            detail: {
              type: 'RATE_LIMIT',
              message: 'Você está indo rápido demais! Aguarde um momento.',
            },
          })
        );
      } else if (status === 503) {
        window.dispatchEvent(
          new CustomEvent('api-error', {
            detail: {
              type: 'CIRCUIT_BREAKER',
              message: 'Serviço temporariamente indisponível (Proteção ativa).',
            },
          })
        );
      }
    }
    return Promise.reject(error);
  }
);

// Em produção, usamos a mesma origem (porta dinâmica do backend).
// Em dev, você pode sobrescrever com VITE_API_URL.
export const API_BASE = (
  import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`
).replace(/\/+$/, '');

import { ResilienceService } from './services/ResilienceService';

export const api = {
  // Decifra entradas inteligentes (UTM, GMS, Lat/Lon)
  smartGeocode: async (text) => {
    return await ResilienceService.executeWithTracing('SMART_GEOCODE', async (context) => {
      // Guard with Circuit Breaker 'GEOCODE_API'
      return await ResilienceService.guard('GEOCODE_API', async () => {
        const response = await axios.get(`${API_BASE}/tools/geocode`, {
          params: { query: text },
          headers: { 'X-Trace-ID': context.traceId }, // Propagate Trace ID
        });
        return response.data;
      });
    });
  },

  checkHealth: async () => {
    // Health check usually bypasses CB to probe recovery, but we can trace it.
    try {
      return await ResilienceService.executeWithTracing('HEALTH_CHECK', async () => {
        const response = await axios.get(`${API_BASE}/health`, { timeout: 2000 });
        return response.data && response.data.status === 'ok';
      });
    } catch {
      return false;
    }
  },

  /**
   * ISO 27001: Exchanges the Master Token (from C#) for a short-lived Session Token.
   * This is called automatically when the token is received from the host.
   */
  setupSecurity: async (masterToken) => {
    try {
      const response = await axios.post(`${API_BASE}/auth/session`, {}, {
        headers: { 'X-SisRua-Token': masterToken }
      });
      const { session_token } = response.data;
      if (session_token) {
        _sessionToken = session_token;
        _masterToken = null; // IMPORTANT: Wipe master token once session is rotated
        console.log('ISO 27001: Session token established. Rotating credentials.');
        return true;
      }
      return false;
    } catch (err) {
      console.error('ISO 27001: Failed to establish secure session.', err);
      return false;
    }
  },

  /**
   * Enterprise: Export project to GeoJSON
   */
  exportGeoJSON: (projectId) => {
    window.open(`${API_BASE}/export/geojson/${projectId}`, '_blank');
  },

  /**
   * Enterprise: Export project to OGC GeoPackage
   */
  exportGeoPackage: (projectId) => {
    window.open(`${API_BASE}/export/geopackage/${projectId}`, '_blank');
  },
};
