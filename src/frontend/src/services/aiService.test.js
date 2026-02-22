/**
 * src/services/aiService.test.js
 *
 * Testes unitários para aiService.sendMessage.
 * Cobre:
 *  - Resposta bem-sucedida (200 + data.response)
 *  - Resposta de erro HTTP (não-200 → mensagem amigável)
 *  - Exceção de rede (fetch lança erro → mensagem amigável)
 *  - Token de auth lido do localStorage
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ─────────────────────────────────────────────
// Mock da dependência api.js (API_BASE)
// ─────────────────────────────────────────────
vi.mock('../api', () => ({
  API_BASE: 'http://localhost:8000/api/v1',
}));

describe('aiService', () => {
  let aiService;

  beforeEach(async () => {
    vi.resetModules();
    ({ aiService } = await import('./aiService'));

    // Configura localStorage com token mock
    localStorage.setItem('sisrua_token', 'test-token-session4');
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  // ── Sucesso ──────────────────────────────────

  it('retorna resposta da IA quando o backend responde 200', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'Olá! Sou a IA do sisRUA.' }),
    });

    const result = await aiService.sendMessage('Olá');
    expect(result).toBe('Olá! Sou a IA do sisRUA.');
  });

  it('envia token do localStorage no header X-SisRua-Token', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'OK' }),
    });

    await aiService.sendMessage('Teste');

    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers['X-SisRua-Token']).toBe('test-token-session4');
  });

  it('envia mensagem e contexto no corpo da requisição', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'Resposta' }),
    });

    const context = { fetch_audit_logs: true };
    await aiService.sendMessage('Quais projetos?', context);

    const [, options] = global.fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.message).toBe('Quais projetos?');
    expect(body.context).toEqual(context);
  });

  // ── Erro HTTP ────────────────────────────────

  it('retorna mensagem amigável quando backend retorna não-200', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    });

    const result = await aiService.sendMessage('Teste');
    expect(result).toContain('Desculpe');
  });

  // ── Erro de rede ─────────────────────────────

  it('retorna mensagem amigável quando fetch lança erro de rede', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    const result = await aiService.sendMessage('Teste');
    expect(result).toContain('Erro de conexão');
  });

  // ── Sem token ────────────────────────────────

  it('envia requisição mesmo sem token no localStorage', async () => {
    localStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'OK sem token' }),
    });

    const result = await aiService.sendMessage('Sem token');

    const [, options] = global.fetch.mock.calls[0];
    expect(options.headers['X-SisRua-Token']).toBe('');
    expect(result).toBe('OK sem token');
  });
});
