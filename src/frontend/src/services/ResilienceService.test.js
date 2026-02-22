/**
 * src/services/ResilienceService.test.js
 *
 * Testes unitários para ResilienceService (Circuit Breaker + Tracing).
 *
 * Cobre:
 *  - Circuit Breaker: estados CLOSED → OPEN → HALF_OPEN → CLOSED
 *  - Tracing: executeWithTracing em sucesso e falha
 *  - guard(): ação bem-sucedida, falhas consecutivas até OPEN, recuperação HALF_OPEN
 *  - Evento CustomEvent 'api-error' quando circuit abre
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResilienceService } from './ResilienceService';

describe('ResilienceService', () => {
  beforeEach(() => {
    // Reseta o registry interno entre testes recriando o módulo
    vi.resetModules();
  });

  // ── executeWithTracing ────────────────────────

  describe('executeWithTracing', () => {
    it('retorna resultado da ação em caso de sucesso', async () => {
      const action = vi.fn().mockResolvedValue('resposta');
      const result = await ResilienceService.executeWithTracing('OP_SUCESSO', action);
      expect(result).toBe('resposta');
      expect(action).toHaveBeenCalledTimes(1);
    });

    it('propaga erro da ação em caso de falha', async () => {
      const action = vi.fn().mockRejectedValue(new Error('backend offline'));
      await expect(
        ResilienceService.executeWithTracing('OP_FALHA', action)
      ).rejects.toThrow('backend offline');
    });

    it('passa contexto de traceId para a ação', async () => {
      let receivedCtx;
      const action = vi.fn().mockImplementation((ctx) => {
        receivedCtx = ctx;
        return Promise.resolve(42);
      });
      await ResilienceService.executeWithTracing('OP_TRACING', action);
      expect(receivedCtx).toHaveProperty('traceId');
      expect(typeof receivedCtx.traceId).toBe('string');
    });
  });

  // ── guard() / Circuit Breaker ─────────────────

  describe('guard (Circuit Breaker)', () => {
    it('permite ação quando circuito está CLOSED', async () => {
      const action = vi.fn().mockResolvedValue('ok');
      // Usa nome único para isolar o estado do circuito
      const result = await ResilienceService.guard('CB_CLOSED_TEST', action);
      expect(result).toBe('ok');
    });

    it('propaga erro da ação quando circuito está CLOSED', async () => {
      const action = vi.fn().mockRejectedValue(new Error('falha'));
      await expect(ResilienceService.guard('CB_PROP_TEST', action)).rejects.toThrow('falha');
    });

    it('abre circuito após 3 falhas consecutivas (threshold padrão)', async () => {
      const action = vi.fn().mockRejectedValue(new Error('timeout'));
      const name = 'CB_OPEN_TEST_' + Date.now();

      // 3 falhas → circuito OPEN
      for (let i = 0; i < 3; i++) {
        await expect(ResilienceService.guard(name, action)).rejects.toThrow();
      }

      // Próxima chamada deve falhar com CircuitBreaker OPEN
      await expect(ResilienceService.guard(name, () => Promise.resolve('ok'))).rejects.toThrow(
        /OPEN/
      );
    });

    it('dispara evento CustomEvent api-error quando circuito abre', async () => {
      const events = [];
      window.addEventListener('api-error', (e) => events.push(e.detail));

      const action = vi.fn().mockRejectedValue(new Error('timeout'));
      const name = 'CB_EVENT_TEST_' + Date.now();

      for (let i = 0; i < 3; i++) {
        await expect(ResilienceService.guard(name, action)).rejects.toThrow();
      }

      window.removeEventListener('api-error', (e) => events.push(e.detail));
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('CIRCUIT_BREAKER_OPEN');
      expect(events[0].message).toContain(name);
    });

    it('transiciona de OPEN para HALF_OPEN após timeout expirar', async () => {
      const name = 'CB_HALF_OPEN_TEST_' + Date.now();

      // Força abertura do circuito
      const failing = vi.fn().mockRejectedValue(new Error('err'));
      for (let i = 0; i < 3; i++) {
        await expect(ResilienceService.guard(name, failing)).rejects.toThrow();
      }

      // Simula passagem do tempo (nextAttempt no passado)
      const { ResilienceService: rs } = await import('./ResilienceService');
      // Manipula nextAttempt via acesso interno ao registry
      // Como o registry é módulo-local, manipulamos pelo comportamento:
      // Mockamos Date.now para retornar um tempo futuro
      const realNow = Date.now;
      Date.now = vi.fn().mockReturnValue(realNow() + 100000);

      // Agora deve aceitar ação (HALF_OPEN) e voltar para CLOSED em caso de sucesso
      const success = vi.fn().mockResolvedValue('recuperado');
      const result = await ResilienceService.guard(name, success);
      expect(result).toBe('recuperado');

      Date.now = realNow;
    });
  });

  // ── Fallback de traceId sem crypto.randomUUID (linha 72) ────────────────────

  describe('executeWithTracing — fallback traceId (linha 72)', () => {
    it('usa Math.random como fallback quando crypto.randomUUID não está disponível', async () => {
      // Salva e remove crypto.randomUUID para forçar o fallback
      const original = crypto.randomUUID;
      delete crypto.randomUUID;

      let receivedCtx;
      const action = vi.fn().mockImplementation((ctx) => {
        receivedCtx = ctx;
        return Promise.resolve('ok');
      });

      const result = await ResilienceService.executeWithTracing('OP_FALLBACK_TRACE', action);

      expect(result).toBe('ok');
      // traceId gerado via Math.random (linha 72) — é string não-vazia
      expect(typeof receivedCtx.traceId).toBe('string');
      expect(receivedCtx.traceId.length).toBeGreaterThan(0);

      // Restaura
      crypto.randomUUID = original;
    });
  });
});
