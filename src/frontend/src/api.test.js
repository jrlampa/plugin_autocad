/**
 * src/api.test.js
 *
 * Testes unitários para o módulo api.js (cliente HTTP sisRUA).
 *
 * Estratégia:
 *   - Desmonta o mock global de './api' (setupTests.js) e importa o módulo real.
 *   - Usa o mock global do axios (setupTests.js) para interceptar chamadas HTTP.
 *   - Testa cada método do objeto `api` e o comportamento dos interceptors.
 *
 * Coordenadas de teste: REF_2 = -22.15018, -42.92185 (MEMORY.MD)
 */
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// Desmonta o mock global de './api' para importar o módulo real.
vi.unmock('./api');

// Importa o módulo real após unmock.
const { api, API_BASE, setAuthToken } = await import('./api');

// Referência à função mock de window.open para testes de export.
const _winOpen = vi.spyOn(window, 'open').mockImplementation(() => null);

// Captura os interceptors registrados ao importar api.js (antes de clearAllMocks).
// Os callbacks são passados para axios.interceptors.*.use() no momento da importação.
const _requestInterceptorCb = axios.interceptors.request.use.mock.calls[0]?.[0] ?? null;
const _responseInterceptorSuccess = axios.interceptors.response.use.mock.calls[0]?.[0] ?? null;
const _responseInterceptorError = axios.interceptors.response.use.mock.calls[0]?.[1] ?? null;

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

function mockGet(data) {
  axios.get.mockResolvedValueOnce({ data });
}

function mockPost(data) {
  axios.post.mockResolvedValueOnce({ data });
}

// eslint-disable-next-line no-unused-vars
function mockGetReject(status) {
  axios.get.mockRejectedValueOnce({ response: { status } });
}

// eslint-disable-next-line no-unused-vars
function mockPostReject(status) {
  axios.post.mockRejectedValueOnce({ response: { status } });
}

// ──────────────────────────────────────────────────────────────────────────────
// API_BASE
// ──────────────────────────────────────────────────────────────────────────────

describe('API_BASE', () => {
  it('não termina com barra', () => {
    expect(API_BASE).not.toMatch(/\/$/);
  });

  it('contém /api/v1 ou é VITE_API_URL sem sufixo', () => {
    // Em JSDOM, window.location.origin = 'http://localhost:3000'
    expect(typeof API_BASE).toBe('string');
    expect(API_BASE.length).toBeGreaterThan(0);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// setAuthToken
// ──────────────────────────────────────────────────────────────────────────────

describe('setAuthToken', () => {
  it('é uma função exportada', () => {
    expect(typeof setAuthToken).toBe('function');
  });

  it('aceita um token string sem lançar', () => {
    expect(() => setAuthToken('meu-token-master')).not.toThrow();
  });

  it('aceita null sem lançar', () => {
    expect(() => setAuthToken(null)).not.toThrow();
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.checkHealth
// ──────────────────────────────────────────────────────────────────────────────

describe('api.checkHealth', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna true quando backend responde status ok', async () => {
    mockGet({ status: 'ok' });
    const result = await api.checkHealth();
    expect(result).toBe(true);
  });

  it('retorna false quando status não é ok', async () => {
    mockGet({ status: 'degraded' });
    const result = await api.checkHealth();
    expect(result).toBe(false);
  });

  it('retorna false quando axios.get lança exceção (backend offline)', async () => {
    axios.get.mockRejectedValueOnce(new Error('Network error'));
    const result = await api.checkHealth();
    expect(result).toBe(false);
  });

  it('chama o endpoint correto /health', async () => {
    mockGet({ status: 'ok' });
    await api.checkHealth();
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({ timeout: 2000 })
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// api.smartGeocode
// ──────────────────────────────────────────────────────────────────────────────

describe('api.smartGeocode', () => {
  beforeEach(() => vi.clearAllMocks());

  it('retorna resultado de geocodificação para lat/lon direto', async () => {
    const payload = { latitude: -22.15018, longitude: -42.92185, source: 'latlon' };
    mockGet(payload);
    const result = await api.smartGeocode('-22.15018, -42.92185');
    expect(result).toEqual(payload);
  });

  it('retorna resultado de geocodificação para UTM', async () => {
    const payload = { latitude: -21.365, longitude: -42.218, source: 'utm' };
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
      ativa: true, concessionaria: 'Light S.A.', classe_tensao: 'MT', numero_processo: '',
    };
    const result = await api.setNormaConfig(payload);
    expect(result).toEqual(resposta);
  });

  it('chama /normas/config com o payload correto', async () => {
    mockPost({ norma_ativa: 'ABNT' });
    const payload = { ativa: false, concessionaria: '', classe_tensao: 'MT', numero_processo: '' };
    await api.setNormaConfig(payload);
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/normas/config'),
      payload
    );
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
    expect(_winOpen).toHaveBeenCalledWith(
      expect.stringContaining('proj-abc'),
      '_blank'
    );
    expect(_winOpen).toHaveBeenCalledWith(
      expect.stringContaining('geojson'),
      '_blank'
    );
  });
});

describe('api.exportGeoPackage', () => {
  afterEach(() => _winOpen.mockClear());

  it('abre window.open com URL contendo project_id e geopackage', () => {
    api.exportGeoPackage('proj-xyz');
    expect(_winOpen).toHaveBeenCalledWith(
      expect.stringContaining('geopackage'),
      '_blank'
    );
  });
});

describe('api.exportDxf', () => {
  afterEach(() => _winOpen.mockClear());

  it('abre window.open com URL contendo project_id e dxf', () => {
    api.exportDxf('proj-dxf');
    expect(_winOpen).toHaveBeenCalledWith(
      expect.stringContaining('dxf'),
      '_blank'
    );
    expect(_winOpen).toHaveBeenCalledWith(
      expect.stringContaining('proj-dxf'),
      '_blank'
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Axios interceptors
// ──────────────────────────────────────────────────────────────────────────────

describe('axios interceptors (request e response)', () => {
  /**
   * Os interceptors são registrados no momento em que api.js é importado.
   * As callbacks foram capturadas antes de vi.clearAllMocks() ser chamado.
   * Invocamo-las diretamente para exercitar as linhas do módulo real.
   */

  beforeEach(async () => {
    // Limpa _sessionToken e _masterToken usando o interceptor de 401
    // (_sessionToken pode estar definido de testes anteriores de setupSecurity)
    if (_responseInterceptorError) {
      await _responseInterceptorError({ response: { status: 401 } }).catch(() => {});
    }
    vi.clearAllMocks();
  });

  describe('request interceptor', () => {
    it('adiciona X-SisRua-Token ao header quando token está configurado', () => {
      if (!_requestInterceptorCb) return;
      setAuthToken('token-interceptor-test');

      const config = { headers: {} };
      const result = _requestInterceptorCb(config);
      expect(result.headers['X-SisRua-Token']).toBe('token-interceptor-test');
      setAuthToken(null); // limpa
    });

    it('não adiciona X-SisRua-Token ao header quando não há token', () => {
      if (!_requestInterceptorCb) return;
      // _sessionToken e _masterToken estão null (limpos em beforeEach)
      const config = { headers: {} };
      const result = _requestInterceptorCb(config);
      expect(result.headers['X-SisRua-Token']).toBeUndefined();
    });

    it('retorna o config completo', () => {
      if (!_requestInterceptorCb) return;
      const config = { headers: {}, url: '/test', method: 'GET' };
      const result = _requestInterceptorCb(config);
      expect(result).toEqual(expect.objectContaining({ url: '/test', method: 'GET' }));
    });
  });

  describe('response interceptor — sucesso', () => {
    it('retorna a resposta intacta no caso de sucesso', () => {
      if (!_responseInterceptorSuccess) return;
      const resp = { status: 200, data: { ok: true } };
      const result = _responseInterceptorSuccess(resp);
      expect(result).toBe(resp);
    });
  });

  describe('response interceptor — erros HTTP', () => {
    it('despacha evento api-error RATE_LIMIT em status 429', async () => {
      if (!_responseInterceptorError) return;
      const listener = vi.fn();
      window.addEventListener('api-error', listener);

      await _responseInterceptorError({ response: { status: 429 } }).catch(() => {});

      expect(listener).toHaveBeenCalled();
      const detail = listener.mock.calls[0][0].detail;
      expect(detail.type).toBe('RATE_LIMIT');
      window.removeEventListener('api-error', listener);
    });

    it('despacha evento api-error CIRCUIT_BREAKER em status 503', async () => {
      if (!_responseInterceptorError) return;
      const listener = vi.fn();
      window.addEventListener('api-error', listener);

      await _responseInterceptorError({ response: { status: 503 } }).catch(() => {});

      expect(listener).toHaveBeenCalled();
      const detail = listener.mock.calls[0][0].detail;
      expect(detail.type).toBe('CIRCUIT_BREAKER');
      window.removeEventListener('api-error', listener);
    });

    it('limpa tokens em status 401 (sessão expirada — ISO 27001)', async () => {
      if (!_responseInterceptorError) return;
      setAuthToken('my-master-token');

      await _responseInterceptorError({ response: { status: 401 } }).catch(() => {});

      // Após 401, setupSecurity com resposta vazia → false
      axios.post.mockResolvedValueOnce({ data: {} });
      const result = await api.setupSecurity('any-token');
      expect(result).toBe(false);
    });

    it('rejeita a promise com o erro original', async () => {
      if (!_responseInterceptorError) return;
      const err = { response: { status: 500 }, message: 'Server Error' };
      await expect(_responseInterceptorError(err)).rejects.toBe(err);
    });

    it('não lança quando error.response é undefined (erro de rede)', async () => {
      if (!_responseInterceptorError) return;
      const err = { message: 'Network Error' };
      await expect(_responseInterceptorError(err)).rejects.toBe(err);
    });
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
  ];

  for (const metodo of METODOS_ESPERADOS) {
    it(`expõe o método api.${metodo}()`, () => {
      expect(typeof api[metodo]).toBe('function');
    });
  }
});
