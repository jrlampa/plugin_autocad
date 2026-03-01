/**
 * src/services/SdkService.real.test.js
 *
 * Testes que executam o código real do SdkService.js (não o mock global).
 *
 * Estratégia:
 *   - vi.unmock() antes de importar → obtém o módulo REAL
 *   - Mocka global.fetch para interceptar chamadas HTTP do SisRuaClient
 *   - Testa cada método do SdkService: health, auth, jobs, elevation, AI, etc.
 *   - Testa o caminho WebView (IPC) e o fallback web para prepareOSM/prepareGeoJSON
 *
 * Coordenadas de teste: REF_2 = -22.15018, -42.92185 (MEMORY.MD)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Unmock ANTES da importação para usar o módulo real.
vi.unmock('./SdkService');

const { SdkService } = await import('./SdkService');

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

function mockFetch(body, ok = true) {
  global.fetch = vi.fn().mockResolvedValueOnce({
    ok,
    statusText: ok ? 'OK' : 'Internal Server Error',
    json: () => Promise.resolve(body),
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// Limpeza do chrome.webview entre testes
// ──────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  // Remove webview padrão para cada teste (evita vazamento de estado IPC)
  if (window.chrome) {
    try {
      delete window.chrome;
    } catch (_) {
      window.chrome = undefined;
    }
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ──────────────────────────────────────────────────────────────────────────────
// checkHealth
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.checkHealth (real)', () => {
  it('retorna dados de health quando fetch responde OK', async () => {
    mockFetch({ status: 'ok' });
    const result = await SdkService.checkHealth();
    expect(result).toEqual({ status: 'ok' });
  });

  it('chama o endpoint /api/v1/health', async () => {
    mockFetch({ status: 'ok' });
    await SdkService.checkHealth();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/health'),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('lança erro quando fetch não-ok', async () => {
    mockFetch({}, false);
    await expect(SdkService.checkHealth()).rejects.toThrow(/API Error/);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// checkHealthDetailed
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.checkHealthDetailed (real)', () => {
  it('retorna objeto com components', async () => {
    const resp = {
      status: 'healthy',
      components: {
        database: { status: 'up', latency_ms: 10 },
        cache: { status: 'up', latency_ms: 5 },
        external_apis: { status: 'up', details: {} },
      },
    };
    mockFetch(resp);
    const result = await SdkService.checkHealthDetailed();
    expect(result).toHaveProperty('components');
  });

  it('chama /api/v1/health/detailed', async () => {
    mockFetch({ status: 'healthy', components: {} });
    await SdkService.checkHealthDetailed();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health/detailed'),
      expect.any(Object)
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// authCheck
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.authCheck (real)', () => {
  it('retorna status ok', async () => {
    mockFetch({ status: 'ok' });
    const result = await SdkService.authCheck();
    expect(result).toEqual({ status: 'ok' });
  });

  it('chama /api/v1/auth/check', async () => {
    mockFetch({ status: 'ok' });
    await SdkService.authCheck();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/check'),
      expect.any(Object)
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// createPrepareJob
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.createPrepareJob (real)', () => {
  it('retorna job_id e status', async () => {
    mockFetch({ job_id: 'job-real-001', status: 'queued' });
    const result = await SdkService.createPrepareJob({
      kind: 'osm',
      latitude: -22.15018,
      longitude: -42.92185,
      radius: 500,
    });
    expect(result).toHaveProperty('job_id');
    expect(result).toHaveProperty('status');
  });

  it('testa raio 100m (REF_2)', async () => {
    mockFetch({ job_id: 'j1', status: 'queued' });
    await SdkService.createPrepareJob({
      kind: 'osm',
      latitude: -22.15018,
      longitude: -42.92185,
      radius: 100,
    });
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('testa raio 1000m (REF_2)', async () => {
    mockFetch({ job_id: 'j2', status: 'queued' });
    await SdkService.createPrepareJob({
      kind: 'osm',
      latitude: -22.15018,
      longitude: -42.92185,
      radius: 1000,
    });
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// queryElevation
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.queryElevation (real)', () => {
  it('retorna objeto com elevation_m para REF_2', async () => {
    mockFetch({ elevation_m: 850.0, latitude: -22.15018, longitude: -42.92185 });
    const result = await SdkService.queryElevation(-22.15018, -42.92185);
    expect(result).toHaveProperty('elevation_m');
  });

  it('chama /api/v1/tools/elevation/query com POST', async () => {
    mockFetch({ elevation_m: 900.0 });
    await SdkService.queryElevation(-22.15018, -42.92185);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/elevation/query'),
      expect.objectContaining({ method: 'POST' })
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// queryElevationProfile
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.queryElevationProfile (real)', () => {
  it('retorna objeto com elevations', async () => {
    mockFetch({ elevations: [850.0, 870.0, 890.0] });
    const result = await SdkService.queryElevationProfile([
      [-22.15018, -42.92185],
      [-22.14968, -42.92085],
    ]);
    expect(result).toHaveProperty('elevations');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// chatWithAI
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.chatWithAI (real)', () => {
  it('retorna campo response', async () => {
    mockFetch({ response: 'Olá! Sou o assistente sisRUA.' });
    const result = await SdkService.chatWithAI('Olá');
    expect(result).toHaveProperty('response');
  });

  it('aceita context e job_id', async () => {
    mockFetch({ response: 'Contexto recebido.' });
    const result = await SdkService.chatWithAI(
      'Quais features?',
      { fetch_audit_logs: true },
      'job-123'
    );
    expect(result.response).toBeTruthy();
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// prepareOSM — caminho WebView (IPC) e fallback web
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.prepareOSM (real)', () => {
  it('retorna orchestrated quando window.chrome.webview está disponível', async () => {
    window.chrome = { webview: { postMessage: vi.fn() } };
    const result = await SdkService.prepareOSM(-22.15018, -42.92185, 500);
    expect(result).toEqual({ status: 'orchestrated' });
    expect(window.chrome.webview.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'GENERATE_OSM' })
    );
  });

  it('chama a API diretamente quando webview não está disponível', async () => {
    mockFetch({ features: [], crs_out: 'EPSG:31984' });
    const result = await SdkService.prepareOSM(-22.15018, -42.92185, 500);
    expect(result).toBeDefined();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/prepare/osm'),
      expect.any(Object)
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// prepareGeoJSON — caminho WebView (IPC) e fallback web
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.prepareGeoJSON (real)', () => {
  it('retorna orchestrated quando window.chrome.webview disponível', async () => {
    window.chrome = { webview: { postMessage: vi.fn() } };
    const geojson = { type: 'FeatureCollection', features: [] };
    const result = await SdkService.prepareGeoJSON(geojson);
    expect(result).toEqual({ status: 'orchestrated' });
    expect(window.chrome.webview.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'IMPORT_GEOJSON' })
    );
  });

  it('chama a API diretamente quando webview não está disponível', async () => {
    mockFetch({ features: [], crs_out: 'EPSG:31984' });
    const result = await SdkService.prepareGeoJSON({ type: 'FeatureCollection', features: [] });
    expect(result).toBeDefined();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/prepare/geojson'),
      expect.any(Object)
    );
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// registerWebhook
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.registerWebhook (real)', () => {
  it('retorna webhook_id', async () => {
    mockFetch({ webhook_id: 'wh-real-1', status: 'active' });
    const result = await SdkService.registerWebhook('https://example.com/hook', ['CREATE']);
    expect(result).toHaveProperty('webhook_id');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// emitEvent
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService.emitEvent (real)', () => {
  it('retorna delivered após emitir evento', async () => {
    mockFetch({ delivered: 1, event_type: 'project_saved' });
    const result = await SdkService.emitEvent('project_saved', { project_id: 'p1' });
    expect(result).toHaveProperty('delivered');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Audit — createAuditLog, listAuditLogs, getAuditLog, verifyAuditLog
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService audit (real)', () => {
  it('createAuditLog retorna audit_id', async () => {
    mockFetch({ audit_id: 1, event_type: 'CREATE' });
    const result = await SdkService.createAuditLog({
      event_type: 'CREATE',
      entity_type: 'Project',
    });
    expect(result).toHaveProperty('audit_id');
  });

  it('listAuditLogs retorna array', async () => {
    mockFetch([{ audit_id: 1 }, { audit_id: 2 }]);
    const result = await SdkService.listAuditLogs();
    expect(Array.isArray(result)).toBe(true);
  });

  it('getAuditLog retorna objeto', async () => {
    mockFetch({ audit_id: 1, event_type: 'CREATE' });
    const result = await SdkService.getAuditLog('1');
    expect(result).toHaveProperty('audit_id');
  });

  it('verifyAuditLog retorna valid boolean', async () => {
    mockFetch({ valid: true, audit_id: 1 });
    const result = await SdkService.verifyAuditLog('1');
    expect(typeof result.valid).toBe('boolean');
  });

  it('verifyAllAuditLogs retorna total/valid/invalid', async () => {
    mockFetch({ total: 10, valid: 9, invalid: 1 });
    const result = await SdkService.verifyAllAuditLogs({ limit: 100 });
    expect(result).toHaveProperty('total');
    expect(result).toHaveProperty('valid');
    expect(result).toHaveProperty('invalid');
  });

  it('getAuditStats retorna total_logs', async () => {
    mockFetch({ total_logs: 42, event_counts: {} });
    const result = await SdkService.getAuditStats();
    expect(result).toHaveProperty('total_logs');
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// updateProject e getJob/cancelJob
// ──────────────────────────────────────────────────────────────────────────────

describe('SdkService projects/jobs (real)', () => {
  it('updateProject retorna dados do projeto', async () => {
    mockFetch({ project_id: 'p1', version: 2, project_name: 'Atualizado' });
    const result = await SdkService.updateProject('p1', { version: 1, project_name: 'Atualizado' });
    expect(result).toHaveProperty('version');
  });

  it('getJob retorna status do job', async () => {
    mockFetch({ job_id: 'job-001', status: 'completed', progress: 1.0 });
    const result = await SdkService.getJob('job-001');
    expect(result).toHaveProperty('status');
  });

  it('cancelJob retorna cancelled', async () => {
    mockFetch({ cancelled: true, job_id: 'job-001' });
    const result = await SdkService.cancelJob('job-001');
    expect(result.cancelled).toBe(true);
  });
});
