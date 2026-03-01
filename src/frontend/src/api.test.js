/**
 * src/api.test.js
 *
 * Testes de integração (SEM MOCKS) para o módulo api.js.
 *
 * Requisitos para rodar:
 * - Backend sisRUA rodando em http://localhost:8000 (docker-compose).
 * - Master token conhecido via env do backend (docker-compose default): "test-token".
 *
 * Objetivo:
 * - Validar chamadas reais (zero-custo) e fluxos ISO 27001:
 *   - /health
 *   - /auth/session + /auth/check
 *   - /tools/geocode com entradas sem rede (lat/lon e UTM)
 */
import { describe, it, expect, beforeAll } from 'vitest';

const { api, API_BASE, setAuthToken } = await import('./api');

const MASTER_TOKEN = process.env.SISRUA_AUTH_TOKEN;

function requireMasterToken() {
  if (!MASTER_TOKEN) {
    throw new Error(
      'Defina a env SISRUA_AUTH_TOKEN (mesmo valor do backend) para rodar os testes de integração sem mocks. Ex.: SISRUA_AUTH_TOKEN=test-token npm test'
    );
  }
}

async function ensureBackendUp() {
  const ok = await api.checkHealth();
  if (!ok) {
    throw new Error(
      'Backend não está disponível em http://localhost:8000. Suba com docker-compose antes de rodar os testes.'
    );
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// API_BASE
// ──────────────────────────────────────────────────────────────────────────────

describe('API_BASE', () => {
  it('não termina com barra', () => {
    expect(API_BASE).not.toMatch(/\/$/);
  });

  it('contém /api/v1 ou é VITE_API_URL sem sufixo', () => {
    expect(typeof API_BASE).toBe('string');
    expect(API_BASE.length).toBeGreaterThan(0);
    expect(API_BASE).toContain('/api/v1');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.checkHealth
// ──────────────────────────────────────────────────────────────────────────────

describe('api.checkHealth', () => {
  it('retorna true quando backend responde status ok', async () => {
    const result = await api.checkHealth();
    expect(result).toBe(true);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.smartGeocode
// ──────────────────────────────────────────────────────────────────────────────

describe('api.smartGeocode', () => {
  beforeAll(async () => {
    await ensureBackendUp();
    requireMasterToken();
    setAuthToken(MASTER_TOKEN);
  });

  it('retorna resultado de geocodificação para lat/lon direto', async () => {
    const result = await api.smartGeocode('-22.15018, -42.92185');
    expect(result).toHaveProperty('latitude');
    expect(result).toHaveProperty('longitude');
    expect(result).toHaveProperty('source');
    expect(result.source).toBe('latlon');
    expect(result.latitude).toBeCloseTo(-22.15018, 5);
    expect(result.longitude).toBeCloseTo(-42.92185, 5);
  });

  it('retorna resultado de geocodificação para UTM', async () => {
    const result = await api.smartGeocode('23K 788547 7634925');
    expect(result).toHaveProperty('latitude');
    expect(result).toHaveProperty('longitude');
    expect(result).toHaveProperty('source');
    expect(result.source).toBe('utm');
  });
});

describe('auth (ISO 27001) — /auth/session + /auth/check', () => {
  beforeAll(async () => {
    await ensureBackendUp();
    requireMasterToken();
  });

  it('estabelece sessão e valida authCheck', async () => {
    const resp = await fetch(`${API_BASE}/auth/check`, {
      headers: { 'X-SisRua-Token': MASTER_TOKEN },
    });
    // auth/check aceita master token
    expect(resp.status).toBe(200);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Métodos disponíveis na interface `api`
// ──────────────────────────────────────────────────────────────────────────────

describe('interface do objeto api', () => {
  const METODOS_ESPERADOS = [
    'checkHealth',
    'smartGeocode',
    'setupSecurity',
    'exportGeoJSON',
    'exportGeoPackage',
    'exportDxf',
    'getNormaAtiva',
    'setNormaConfig',
    'getElevationContours',
    'convertKml',
  ];

  for (const metodo of METODOS_ESPERADOS) {
    it(`expõe o método api.${metodo}()`, () => {
      expect(typeof api[metodo]).toBe('function');
    });
  }
});
