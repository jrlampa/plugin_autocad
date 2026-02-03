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

      // ISO 27001: Session expired
      if (status === 401 && _sessionToken) {
        console.warn('Session expired. Attempting re-authentication...');
        _sessionToken = null;
        // Trigger setupSecurity again if needed or notify user
      }
      // ... rest of the interceptor logic

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
        console.log('ISO 27001: Session token established. Rotating credentials.');

        // Security: Remove master token from local module scope once rotated
        _masterToken = null;
        return true;
      }
    } catch (err) {
      console.error('ISO 27001: Failed to establish secure session.', err);
      return false;
    }
  }
};
