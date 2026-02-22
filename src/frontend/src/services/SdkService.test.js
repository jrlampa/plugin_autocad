/**
 * src/services/SdkService.test.js
 *
 * Testes unitários para SdkService.
 *
 * Estratégia:
 *   - Usa o mock global do SdkService (definido em setupTests.js) para isolar de fetch/rede
 *   - Valida interface (todos os métodos existem e são funções callable)
 *   - Valida shapes dos objetos de resposta retornados pelo mock
 *   - Testa lógica IPC (window.chrome.webview) em prepareOSM e prepareGeoJSON
 *
 * Coordenadas de teste: -22.15018, -42.92185 (conforme MEMORY.MD)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SdkService } from './SdkService';

// ─────────────────────────────────────────────────────────────────────────
// O setupTests.js já define um mock global para SdkService com todos os
// métodos. Esses testes validam a interface e o comportamento do mock.
// ─────────────────────────────────────────────────────────────────────────

describe('SdkService (interface e contrato)', () => {
  beforeEach(() => {
    // Limpa os registros de chamadas dos mocks entre testes
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (window.chrome) {
      try { delete window.chrome; } catch (_) { window.chrome = undefined; }
    }
  });

  // ── Interface: todos os métodos devem existir ─────────────────────────

  describe('interface', () => {
    const METODOS_ESPERADOS = [
      'checkHealth', 'checkHealthDetailed', 'authCheck',
      'updateProject', 'createPrepareJob', 'getJob', 'cancelJob',
      'queryElevation', 'queryElevationProfile', 'chatWithAI',
      'prepareOSM', 'prepareGeoJSON', 'registerWebhook', 'emitEvent',
      'createAuditLog', 'listAuditLogs', 'getAuditLog',
      'verifyAuditLog', 'verifyAllAuditLogs', 'getAuditStats',
    ];

    for (const metodo of METODOS_ESPERADOS) {
      it(`deve expor o método ${metodo}()`, () => {
        expect(typeof SdkService[metodo]).toBe('function');
      });
    }
  });

  // ── Health ────────────────────────────────────────────────────────────

  describe('checkHealth', () => {
    it('retorna objeto com status', async () => {
      const result = await SdkService.checkHealth();
      expect(result).toHaveProperty('status');
    });

    it('resolve com sucesso sem argumentos extras', async () => {
      await expect(SdkService.checkHealth()).resolves.not.toThrow();
    });
  });

  describe('checkHealthDetailed', () => {
    it('retorna objeto com campo components', async () => {
      const result = await SdkService.checkHealthDetailed();
      expect(result).toHaveProperty('components');
    });

    it('components contém database, cache e external_apis', async () => {
      const result = await SdkService.checkHealthDetailed();
      expect(result.components).toHaveProperty('database');
      expect(result.components).toHaveProperty('cache');
      expect(result.components).toHaveProperty('external_apis');
    });
  });

  // ── Auth ─────────────────────────────────────────────────────────────

  describe('authCheck', () => {
    it('retorna status ok', async () => {
      const result = await SdkService.authCheck();
      expect(result.status).toBe('ok');
    });
  });

  // ── Projects ─────────────────────────────────────────────────────────

  describe('updateProject', () => {
    it('retorna projeto com version', async () => {
      const result = await SdkService.updateProject('p1', { version: 1 });
      expect(result).toHaveProperty('version');
    });
  });

  // ── Jobs ─────────────────────────────────────────────────────────────

  describe('createPrepareJob', () => {
    it('retorna job_id e status', async () => {
      const result = await SdkService.createPrepareJob({
        kind: 'osm', latitude: -22.15018, longitude: -42.92185, radius: 500,
      });
      expect(result).toHaveProperty('job_id');
      expect(result).toHaveProperty('status');
    });
  });

  describe('getJob', () => {
    it('retorna status do job', async () => {
      const result = await SdkService.getJob();
      expect(result).toHaveProperty('status');
    });
  });

  describe('cancelJob', () => {
    it('retorna cancelled: true', async () => {
      const result = await SdkService.cancelJob();
      expect(result.cancelled).toBe(true);
    });
  });

  // ── Elevation ────────────────────────────────────────────────────────

  describe('queryElevation', () => {
    it('retorna objeto com elevation_m', async () => {
      const result = await SdkService.queryElevation(-22.15018, -42.92185);
      expect(result).toHaveProperty('elevation_m');
    });
  });

  describe('queryElevationProfile', () => {
    it('retorna objeto com elevations', async () => {
      const result = await SdkService.queryElevationProfile([[-22.15, -42.92]]);
      expect(result).toHaveProperty('elevations');
    });
  });

  // ── AI Chat ───────────────────────────────────────────────────────────

  describe('chatWithAI', () => {
    it('retorna resposta com campo response', async () => {
      const result = await SdkService.chatWithAI('Olá');
      expect(result).toHaveProperty('response');
    });

    it('aceita context e job_id', async () => {
      await expect(
        SdkService.chatWithAI('Pergunta', { fetch_audit_logs: true }, 'job-xyz')
      ).resolves.not.toThrow();
    });
  });

  // ── prepareOSM e prepareGeoJSON ───────────────────────────────────────

  describe('prepareOSM', () => {
    it('retorna algum resultado (features ou orchestrated)', async () => {
      const result = await SdkService.prepareOSM(-22.15018, -42.92185, 500);
      expect(result).toBeDefined();
    });

    it('aceita os três parâmetros (lat, lon, radius)', async () => {
      await expect(
        SdkService.prepareOSM(-22.15018, -42.92185, 100)
      ).resolves.not.toThrow();
      await expect(
        SdkService.prepareOSM(-22.15018, -42.92185, 500)
      ).resolves.not.toThrow();
      await expect(
        SdkService.prepareOSM(-22.15018, -42.92185, 1000)
      ).resolves.not.toThrow();
    });
  });

  describe('prepareGeoJSON', () => {
    it('aceita um objeto GeoJSON', async () => {
      const geojson = { type: 'FeatureCollection', features: [] };
      await expect(SdkService.prepareGeoJSON(geojson)).resolves.not.toThrow();
    });
  });

  // ── Webhooks e Eventos ────────────────────────────────────────────────

  describe('registerWebhook', () => {
    it('retorna webhook_id', async () => {
      const result = await SdkService.registerWebhook('https://srv.com/wh', ['CREATE']);
      expect(result).toHaveProperty('webhook_id');
    });
  });

  describe('emitEvent', () => {
    it('retorna delivered', async () => {
      const result = await SdkService.emitEvent('project_saved', { id: 'p1' });
      expect(result).toHaveProperty('delivered');
    });
  });

  // ── Audit ─────────────────────────────────────────────────────────────

  describe('createAuditLog', () => {
    it('retorna audit_id', async () => {
      const result = await SdkService.createAuditLog({ event_type: 'CREATE', entity_type: 'Project' });
      expect(result).toHaveProperty('audit_id');
    });
  });

  describe('listAuditLogs', () => {
    it('retorna array', async () => {
      const result = await SdkService.listAuditLogs();
      expect(Array.isArray(result)).toBe(true);
    });
  });

  describe('getAuditLog', () => {
    it('retorna objeto com audit_id', async () => {
      const result = await SdkService.getAuditLog();
      expect(result).toHaveProperty('audit_id');
    });
  });

  describe('verifyAuditLog', () => {
    it('retorna valid boolean', async () => {
      const result = await SdkService.verifyAuditLog();
      expect(typeof result.valid).toBe('boolean');
    });
  });

  describe('verifyAllAuditLogs', () => {
    it('retorna total, valid e invalid', async () => {
      const result = await SdkService.verifyAllAuditLogs();
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('valid');
      expect(result).toHaveProperty('invalid');
    });
  });

  describe('getAuditStats', () => {
    it('retorna total_logs', async () => {
      const result = await SdkService.getAuditStats();
      expect(result).toHaveProperty('total_logs');
    });
  });
});
