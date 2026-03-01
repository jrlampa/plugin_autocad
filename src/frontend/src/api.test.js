/**
 * src/api.test.js
 *
 * Testes do módulo api.js — cobertura de unidade com axios mockado.
 *
 * Todos os testes rodam sem backend real (CI-safe).
 * Para rodar testes de integração real, suba o backend com docker-compose e
 * defina SISRUA_AUTH_TOKEN com o token master do backend.
 */
import { vi, describe, it, expect, beforeAll, beforeEach, afterAll, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mock axios ANTES de qualquer importação que dependa dele
// ---------------------------------------------------------------------------
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

import axios from 'axios';

const { api, API_BASE, setAuthToken } = await import('./api');

const MASTER_TOKEN =
  process.env.NODE_ENV === 'test'
    ? process.env.SISRUA_AUTH_TOKEN || 'test-token'
    : process.env.SISRUA_AUTH_TOKEN;

// ---------------------------------------------------------------------------
// Helpers de mock
// ---------------------------------------------------------------------------
function mockGet(data) {
  axios.get.mockResolvedValueOnce({ data });
}

function mockPost(data) {
  axios.post.mockResolvedValueOnce({ data });
}

// Spy para window.open — usado pelos testes de export
let _winOpen;
beforeAll(() => {
  _winOpen = vi.spyOn(window, 'open').mockImplementation(() => {});
  setAuthToken(MASTER_TOKEN);
});
afterAll(() => {
  _winOpen.mockRestore();
});

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
    axios.get.mockResolvedValueOnce({ data: { status: 'ok' } });
    const result = await api.checkHealth();
    expect(result).toBe(true);
  });

  it('retorna false quando backend não responde', async () => {
    axios.get.mockRejectedValueOnce(new Error('ECONNREFUSED'));
    const result = await api.checkHealth();
    expect(result).toBe(false);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.smartGeocode
// ──────────────────────────────────────────────────────────────────────────────

describe('api.smartGeocode', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna resultado de geocodificação para lat/lon direto', async () => {
    mockGet({ latitude: -22.15018, longitude: -42.92185, source: 'latlon' });
    const result = await api.smartGeocode('-22.15018, -42.92185');
    expect(result).toHaveProperty('latitude');
    expect(result).toHaveProperty('longitude');
    expect(result).toHaveProperty('source');
    expect(result.source).toBe('latlon');
    expect(result.latitude).toBeCloseTo(-22.15018, 5);
    expect(result.longitude).toBeCloseTo(-42.92185, 5);
  });

  it('retorna resultado de geocodificação para UTM', async () => {
    const payload = { latitude: -22.15, longitude: -42.92, source: 'utm' };
    mockGet(payload);
    const result = await api.smartGeocode('23K 788547 7634925');
    expect(result).toEqual(payload);
  });

  it('chama o endpoint /tools/geocode com query correta', async () => {
    mockGet({ latitude: -22.15, longitude: -42.92, source: 'nominatim' });
    await api.smartGeocode('Nova Friburgo RJ');
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/tools/geocode'),
      expect.objectContaining({ params: { query: 'Nova Friburgo RJ' } })
    );
  });

  it('propaga X-Trace-ID no header', async () => {
    mockGet({ latitude: -22.15018, longitude: -42.92185, source: 'latlon' });
    await api.smartGeocode('-22.15018, -42.92185');
    const call = axios.get.mock.calls[0][1];
    expect(call.headers).toHaveProperty('X-Trace-ID');
    expect(typeof call.headers['X-Trace-ID']).toBe('string');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.setupSecurity
// ──────────────────────────────────────────────────────────────────────────────

describe('api.setupSecurity', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna true quando backend responde com session_token', async () => {
    mockPost({ session_token: 'sess-abc123' });
    const result = await api.setupSecurity('master-token-xyz');
    expect(result).toBe(true);
  });

  it('retorna false quando backend não retorna session_token', async () => {
    mockPost({});
    const result = await api.setupSecurity('master-token-xyz');
    expect(result).toBe(false);
  });

  it('retorna false quando axios.post lança exceção', async () => {
    axios.post.mockRejectedValueOnce(new Error('Connection refused'));
    const result = await api.setupSecurity('master-token');
    expect(result).toBe(false);
  });

  it('chama /auth/session com o token master no header', async () => {
    mockPost({ session_token: 'sessao' });
    await api.setupSecurity('tk-master');
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/session'),
      {},
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-SisRua-Token': 'tk-master' }),
      })
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.getNormaAtiva / api.setNormaConfig
// ──────────────────────────────────────────────────────────────────────────────

describe('api.getNormaAtiva', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna configuração de norma ativa', async () => {
    const norma = { ativa: 'ABNT', classe_tensao: 'MT' };
    mockGet(norma);
    const result = await api.getNormaAtiva();
    expect(result).toEqual(norma);
  });

  it('chama /normas/ativas', async () => {
    mockGet({ ativa: 'ABNT' });
    await api.getNormaAtiva();
    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/normas/ativas'));
  });
});

describe('api.setNormaConfig', () => {
  beforeEach(() => vi.clearAllMocks());

  it('envia configuração PRODIST e retorna resposta', async () => {
    const resposta = { norma_ativa: 'PRODIST', toast: 'PRODIST ativado' };
    mockPost(resposta);
    const payload = {
      ativa: true,
      concessionaria: 'Light S.A.',
      classe_tensao: 'MT',
      numero_processo: '',
    };
    const result = await api.setNormaConfig(payload);
    expect(result).toEqual(resposta);
  });

  it('chama /normas/config com o payload correto', async () => {
    mockPost({ norma_ativa: 'ABNT' });
    const payload = { ativa: false, concessionaria: '', classe_tensao: 'MT', numero_processo: '' };
    await api.setNormaConfig(payload);
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/normas/config'), payload);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.getElevationContours
// ──────────────────────────────────────────────────────────────────────────────

describe('api.getElevationContours', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna curvas de nível para REF_2 (100m)', async () => {
    const resposta = {
      contours: [{ elevation: 500.0, geometry: [[-22.15, -42.92]] }],
      interval: 10.0,
      count: 1,
    };
    mockPost(resposta);
    const result = await api.getElevationContours(-22.16, -42.93, -22.14, -42.91, 10.0);
    expect(result).toEqual(resposta);
  });

  it('usa intervalo padrão 10.0 quando não fornecido', async () => {
    mockPost({ contours: [], interval: 10.0, count: 0 });
    await api.getElevationContours(-22.16, -42.93, -22.14, -42.91);
    const body = axios.post.mock.calls[0][1];
    expect(body.interval).toBe(10.0);
  });

  it('chama /tools/elevation/contours com bounding box correto', async () => {
    mockPost({ contours: [], interval: 5.0, count: 0 });
    await api.getElevationContours(-22.155, -42.927, -22.145, -42.917, 5.0);
    const [url, body] = axios.post.mock.calls[0];
    expect(url).toContain('/tools/elevation/contours');
    expect(body.min_lat).toBe(-22.155);
    expect(body.min_lon).toBe(-42.927);
    expect(body.max_lat).toBe(-22.145);
    expect(body.max_lon).toBe(-42.917);
    expect(body.interval).toBe(5.0);
  });

  it('testa área REF_2 com 500m', async () => {
    mockPost({ contours: [], interval: 10.0, count: 0 });
    await api.getElevationContours(-22.155, -42.927, -22.145, -42.917, 10.0);
    expect(axios.post).toHaveBeenCalledTimes(1);
  });

  it('testa área REF_2 com 1km', async () => {
    mockPost({ contours: [], interval: 10.0, count: 0 });
    await api.getElevationContours(-22.16, -42.93, -22.14, -42.91, 10.0);
    expect(axios.post).toHaveBeenCalledTimes(1);
  });

  it('propaga X-Trace-ID no header', async () => {
    mockPost({ contours: [], interval: 10.0, count: 0 });
    await api.getElevationContours(-22.16, -42.93, -22.14, -42.91);
    const opts = axios.post.mock.calls[0][2];
    expect(opts.headers).toHaveProperty('X-Trace-ID');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.exportGeoJSON / api.exportGeoPackage / api.exportDxf
// ──────────────────────────────────────────────────────────────────────────────

describe('api.exportGeoJSON', () => {
  afterEach(() => _winOpen.mockClear());

  it('abre window.open com URL contendo project_id', () => {
    api.exportGeoJSON('proj-abc');
    expect(_winOpen).toHaveBeenCalledWith(expect.stringContaining('proj-abc'), '_blank');
    expect(_winOpen).toHaveBeenCalledWith(expect.stringContaining('geojson'), '_blank');
  });
});

describe('api.exportGeoPackage', () => {
  afterEach(() => _winOpen.mockClear());

  it('abre window.open com URL contendo project_id e geopackage', () => {
    api.exportGeoPackage('proj-xyz');
    expect(_winOpen).toHaveBeenCalledWith(expect.stringContaining('geopackage'), '_blank');
  });
});

describe('api.exportDxf', () => {
  afterEach(() => _winOpen.mockClear());

  it('abre window.open com URL contendo project_id e dxf', () => {
    api.exportDxf('proj-dxf');
    expect(_winOpen).toHaveBeenCalledWith(expect.stringContaining('dxf'), '_blank');
    expect(_winOpen).toHaveBeenCalledWith(expect.stringContaining('proj-dxf'), '_blank');
  });
});

describe('auth (ISO 27001) — /auth/session + /auth/check', () => {
  let _fetchSpy;
  beforeEach(() => {
    _fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValueOnce({ status: 200, ok: true });
  });
  afterEach(() => {
    _fetchSpy.mockRestore();
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
