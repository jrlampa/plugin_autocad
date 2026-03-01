/**
 * src/sdk/client.test.ts
 *
 * Testes unitários para SisRuaClient (sdk/client.ts).
 *
 * Cobre:
 *   - Construtor: baseUrl e token
 *   - request(): token no header, sem token, resposta não-ok
 *   - Todos os métodos de API (linhas 134-135: rootGet e verifyAllLogsApiAuditVerifyAllPost)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SisRuaClient } from './client';

// ─────────────────────────────────────────────────────────
// Setup global fetch mock
// ─────────────────────────────────────────────────────────

function makeFetchOk(responseBody: unknown = { ok: true }) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(responseBody),
  });
}

function makeFetchError(status = 500, statusText = 'Internal Server Error') {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    statusText,
    json: () => Promise.resolve({}),
  });
}

// ─────────────────────────────────────────────────────────
// Testes do construtor
// ─────────────────────────────────────────────────────────

describe('SisRuaClient — construtor', () => {
  it('remove trailing slash da baseUrl', () => {
    const client = new SisRuaClient('http://localhost:8000/');
    // O request deve usar a URL sem a barra final
    global.fetch = makeFetchOk({ status: 'ok' });
    return client.healthApiV1HealthGet().then(() => {
      const url = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toBe('http://localhost:8000/api/v1/health');
    });
  });

  it('funciona sem token (não inclui X-SisRua-Token no header)', async () => {
    global.fetch = makeFetchOk({ status: 'ok' });
    const client = new SisRuaClient('http://localhost:8000');
    await client.healthApiV1HealthGet();
    const headers = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
    expect(headers['X-SisRua-Token']).toBeUndefined();
  });

  it('inclui X-SisRua-Token no header quando token fornecido', async () => {
    global.fetch = makeFetchOk({ status: 'ok' });
    const client = new SisRuaClient('http://localhost:8000', 'meu-token-secreto');
    await client.healthApiV1HealthGet();
    const headers = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
    expect(headers['X-SisRua-Token']).toBe('meu-token-secreto');
  });
});

// ─────────────────────────────────────────────────────────
// Testes do método request()
// ─────────────────────────────────────────────────────────

describe('SisRuaClient — request()', () => {
  it('lança erro quando resposta não é ok', async () => {
    global.fetch = makeFetchError(503, 'Service Unavailable');
    const client = new SisRuaClient('http://localhost:8000', 'token');
    await expect(client.healthApiV1HealthGet()).rejects.toThrow('API Error: Service Unavailable');
  });

  it('inclui Content-Type: application/json em todos os requests', async () => {
    global.fetch = makeFetchOk({});
    const client = new SisRuaClient('http://localhost:8000', 'token');
    await client.healthApiV1HealthGet();
    const headers = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
    expect(headers['Content-Type']).toBe('application/json');
  });
});

// ─────────────────────────────────────────────────────────
// Todos os métodos de API (cobertura de linha)
// ─────────────────────────────────────────────────────────

describe('SisRuaClient — métodos de API', () => {
  let client: SisRuaClient;

  beforeEach(() => {
    global.fetch = makeFetchOk({ result: 'ok' });
    client = new SisRuaClient('http://localhost:8000', 'test-token');
  });

  it('authCheckApiV1AuthCheckGet — GET /api/v1/auth/check', async () => {
    const result = await client.authCheckApiV1AuthCheckGet();
    expect(result).toEqual({ result: 'ok' });
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/auth/check');
    expect(opts.method).toBe('GET');
  });

  it('healthApiV1HealthGet — GET /api/v1/health', async () => {
    const result = await client.healthApiV1HealthGet();
    expect(result).toEqual({ result: 'ok' });
  });

  it('healthDetailedApiV1HealthDetailedGet — GET /api/v1/health/detailed', async () => {
    await client.healthDetailedApiV1HealthDetailedGet();
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/health/detailed');
  });

  it('updateProjectApiV1ProjectsProjectIdPut — PUT /api/v1/projects/{project_id}', async () => {
    await client.updateProjectApiV1ProjectsProjectIdPut({ project_id: 'p1' });
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/projects/');
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body)).toEqual({ project_id: 'p1' });
  });

  it('createPrepareJobApiV1JobsPreparePost — POST /api/v1/jobs/prepare', async () => {
    await client.createPrepareJobApiV1JobsPreparePost({ latitude: -22.15018 });
    const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(opts.method).toBe('POST');
  });

  it('getJobEndpointApiV1JobsJobIdGet — GET /api/v1/jobs/{job_id}', async () => {
    await client.getJobEndpointApiV1JobsJobIdGet();
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/jobs/');
    expect(opts.method).toBe('GET');
  });

  it('cancelJobEndpointApiV1JobsJobIdDelete — DELETE /api/v1/jobs/{job_id}', async () => {
    await client.cancelJobEndpointApiV1JobsJobIdDelete();
    const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(opts.method).toBe('DELETE');
  });

  it('queryElevationApiV1ToolsElevationQueryPost — POST /tools/elevation/query', async () => {
    await client.queryElevationApiV1ToolsElevationQueryPost({
      latitude: -22.15018,
      longitude: -42.92185,
    });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/tools/elevation/query');
  });

  it('queryProfileApiV1ToolsElevationProfilePost — POST /tools/elevation/profile', async () => {
    await client.queryProfileApiV1ToolsElevationProfilePost({ path: [[-22.15018, -42.92185]] });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/tools/elevation/profile');
  });

  it('chatWithAiApiV1AiChatPost — POST /api/v1/ai/chat', async () => {
    await client.chatWithAiApiV1AiChatPost({ message: 'olá' });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/ai/chat');
  });

  it('prepareOsmApiV1PrepareOsmPost — POST /api/v1/prepare/osm', async () => {
    await client.prepareOsmApiV1PrepareOsmPost({
      latitude: -22.15018,
      longitude: -42.92185,
      radius: 500,
    });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/prepare/osm');
  });

  it('prepareGeojsonApiV1PrepareGeojsonPost — POST /api/v1/prepare/geojson', async () => {
    await client.prepareGeojsonApiV1PrepareGeojsonPost({ geojson: {} });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/prepare/geojson');
  });

  it('registerWebhookApiV1WebhooksRegisterPost — POST /api/v1/webhooks/register', async () => {
    await client.registerWebhookApiV1WebhooksRegisterPost({ url: 'https://example.com' });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/webhooks/register');
  });

  it('emitEventApiV1EventsEmitPost — POST /api/v1/events/emit', async () => {
    await client.emitEventApiV1EventsEmitPost({ type: 'TEST' });
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/v1/events/emit');
  });

  it('createAuditLogApiAuditPost — POST /api/audit', async () => {
    await client.createAuditLogApiAuditPost({ operation: 'test' });
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit');
    expect(opts.method).toBe('POST');
  });

  it('listAuditLogsApiAuditGet — GET /api/audit', async () => {
    await client.listAuditLogsApiAuditGet();
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit');
    expect(opts.method).toBe('GET');
  });

  it('getAuditLogApiAuditAuditIdGet — GET /api/audit/{audit_id}', async () => {
    await client.getAuditLogApiAuditAuditIdGet();
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit/');
  });

  it('verifyAuditLogApiAuditAuditIdVerifyGet — GET /api/audit/{audit_id}/verify', async () => {
    await client.verifyAuditLogApiAuditAuditIdVerifyGet();
    const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit/');
    expect(url).toContain('verify');
  });

  it('verifyAllLogsApiAuditVerifyAllPost — POST /api/audit/verify-all (linha 124)', async () => {
    await client.verifyAllLogsApiAuditVerifyAllPost({ limit: 100 });
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit/verify-all');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ limit: 100 });
  });

  it('getAuditStatsApiAuditStatsGet — GET /api/audit/stats (linha 128)', async () => {
    await client.getAuditStatsApiAuditStatsGet();
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/audit/stats');
    expect(opts.method).toBe('GET');
  });

  it('rootGet — GET / (linhas 134-135)', async () => {
    await client.rootGet();
    const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('http://localhost:8000/');
    expect(opts.method).toBe('GET');
  });
});
