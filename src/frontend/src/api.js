import axios from 'axios';

// ISO 27001 Security: Tokens are stored in private module scope, NOT in window global.
let _masterToken = null;
let _sessionToken = null;

export const setAuthToken = (token) => {
  _masterToken = token;
};

// ============================================================================
// CRITICAL FIX: Auth header injection is handled by WebView2 (SisRuaPalette.cs:421)
// The C# layer automatically injects 'X-SisRua-Token' for ALL backend requests.
// DO NOT add the header here in axios - it will OVERWRITE the WebView2 token!
// Previously, this interceptor was overwriting the valid WebView2 token with
// expired session tokens, causing 401 errors.
// ============================================================================

/* DISABLED - WebView2 handles authentication
axios.interceptors.request.use((config) => {
  const token = _sessionToken || _masterToken;
  if (token) {
    config.headers['X-SisRua-Token'] = token;
  }
  return config;
});
*/


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
      const response = await axios.post(
        `${API_BASE}/auth/session`,
        {},
        {
          headers: { 'X-SisRua-Token': masterToken },
        }
      );
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

  /**
   * Enterprise: Export project to DXF (ABNT NBR 14166 / 2.5D)
   */
  exportDxf: (projectId) => {
    window.open(`${API_BASE}/export/dxf/${projectId}`, '_blank');
  },

  /**
   * ANEEL/PRODIST: Retorna a norma técnica ativa.
   */
  getNormaAtiva: async () => {
    const response = await axios.get(`${API_BASE}/normas/ativas`);
    return response.data;
  },

  /**
   * ANEEL/PRODIST: Configura a norma técnica ativa (ABNT ou PRODIST).
   * @param {{ ativa: boolean, concessionaria: string, classe_tensao: string, numero_processo: string }} payload
   */
  setNormaConfig: async (payload) => {
    const response = await axios.post(`${API_BASE}/normas/config`, payload);
    return response.data;
  },

  /**
   * Ferramentas: Gera curvas de nível para uma área delimitada.
   * @param {number} minLat - Latitude mínima da área
   * @param {number} minLon - Longitude mínima da área
   * @param {number} maxLat - Latitude máxima da área
   * @param {number} maxLon - Longitude máxima da área
   * @param {number} interval - Intervalo de contorno em metros (padrão: 10)
   * @returns {{ contours: Array, interval: number, count: number }}
   */
  getElevationContours: async (minLat, minLon, maxLat, maxLon, interval = 10.0) => {
    return await ResilienceService.executeWithTracing('ELEVATION_CONTOURS', async (context) => {
      return await ResilienceService.guard('ELEVATION_API', async () => {
        const response = await axios.post(
          `${API_BASE}/tools/elevation/contours`,
          { min_lat: minLat, min_lon: minLon, max_lat: maxLat, max_lon: maxLon, interval },
          { headers: { 'X-Trace-ID': context.traceId } },
        );
        return response.data;
      });
    });
  },

  /**
   * GIS: Converte conteúdo KML para GeoJSON via backend.
   * @param {string} content - Conteúdo XML do arquivo KML
   */
  convertKml: async (content) => {
    return await ResilienceService.executeWithTracing('CONVERT_KML', async (context) => {
      const response = await axios.post(
        `${API_BASE}/gis/convert/kml`,
        { content },
        { headers: { 'X-Trace-ID': context.traceId } }
      );
      return response.data;
    });
  },

  /**
   * Blocos CAD: Lista os blocos de infraestrutura elétrica disponíveis.
   * @param {{ tipo?: string, tensao?: string }} [filtros] - Filtros opcionais
   * @returns {{ blocos: Array, total: number }}
   */
  listBlocks: async (filtros = {}) => {
    const params = {};
    if (filtros.tipo) params.tipo = filtros.tipo;
    if (filtros.tensao) params.tensao = filtros.tensao;
    const response = await axios.get(`${API_BASE}/blocks`, { params });
    return response.data;
  },

  /**
   * Blocos CAD: Retorna metadados de um bloco específico.
   * @param {string} nome - Nome do bloco (ex.: POSTE_CONCRETO_BF)
   */
  getBlock: async (nome) => {
    const response = await axios.get(`${API_BASE}/blocks/${encodeURIComponent(nome)}`);
    return response.data;
  },
};
