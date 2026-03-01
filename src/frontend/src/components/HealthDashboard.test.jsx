/**
 * src/components/HealthDashboard.test.jsx
 *
 * Testes unitários para o componente HealthDashboard.
 *
 * Estratégia:
 *   - Usa o mock global do SdkService (setupTests.js) que retorna dados saudáveis.
 *   - Testa os três estados: loading, error, healthy data.
 *   - Testa StatusIcon (ícones por status) e getStatusColor (classes CSS).
 *   - Testa botão "Tentar novamente" no estado de erro.
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import HealthDashboard from './HealthDashboard';
import { SdkService } from '../services/SdkService';

// Garante que os timers reais são restaurados após cada teste para evitar vazamento
afterEach(() => {
  vi.useRealTimers();
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado de carregamento inicial
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — estado de carregamento', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Congela a resposta para manter loading estado
    SdkService.checkHealthDetailed.mockReturnValue(new Promise(() => {}));
  });

  it('exibe texto de verificação enquanto carrega', () => {
    render(<HealthDashboard />);
    expect(screen.getByText(/verificando status/i)).toBeInTheDocument();
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado de erro
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — estado de erro', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockRejectedValue(new Error('Conexão recusada'));
  });

  it('exibe mensagem de erro após falha na API', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/não foi possível conectar/i)).toBeInTheDocument();
    });
  });

  it('exibe botão "Tentar novamente"', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /tentar novamente/i })).toBeInTheDocument();
    });
  });

  it('botão "Tentar novamente" chama checkHealthDetailed novamente', async () => {
    // Primeira chamada falha, segunda tem sucesso
    SdkService.checkHealthDetailed.mockRejectedValueOnce(new Error('Falha')).mockResolvedValueOnce({
      status: 'healthy',
      system_status: 'healthy',
      components: {
        database: { status: 'healthy', latency_ms: 10 },
        cache: { status: 'healthy', latency_ms: 5 },
        external_apis: { status: 'healthy', details: {} },
      },
    });

    render(<HealthDashboard />);

    // Aguarda estado de erro
    const btn = await screen.findByRole('button', { name: /tentar novamente/i });

    // Clica no botão de retry
    await act(async () => {
      fireEvent.click(btn);
    });

    // Deve ter chamado 2 vezes (inicial + retry)
    expect(SdkService.checkHealthDetailed).toHaveBeenCalledTimes(2);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado saudável (healthy)
// ──────────────────────────────────────────────────────────────────────────────

const _HEALTH_HEALTHY = {
  status: 'healthy',
  system_status: 'healthy',
  system_latency_ms: 25.3,
  components: {
    database: { status: 'healthy', latency_ms: 12.5, details: null },
    cache: { status: 'healthy', latency_ms: 3.2, details: null },
    external_apis: {
      status: 'healthy',
      latency_ms: null,
      details: { groq: true, opentopography: false },
    },
  },
};

describe('HealthDashboard — estado saudável', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockResolvedValue(_HEALTH_HEALTHY);
  });

  it('exibe "Status do Sistema" após carregamento', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Status do Sistema')).toBeInTheDocument();
    });
  });

  it('exibe Database na lista de componentes', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Database')).toBeInTheDocument();
    });
  });

  it('exibe Redis/Cache na lista de componentes', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Redis/Cache')).toBeInTheDocument();
    });
  });

  it('exibe External APIs na lista de componentes', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('External APIs')).toBeInTheDocument();
    });
  });

  it('exibe latência do banco de dados em ms', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('12.5ms')).toBeInTheDocument();
    });
  });

  it('exibe detalhes de APIs externas (CONFIGURADO / AUSENTE)', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('CONFIGURADO')).toBeInTheDocument();
      expect(screen.getByText('AUSENTE')).toBeInTheDocument();
    });
  });

  it('exibe "poucos segundos" no texto de atualização', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/poucos segundos/i)).toBeInTheDocument();
    });
  });

  it('chama checkHealthDetailed ao montar', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(SdkService.checkHealthDetailed).toHaveBeenCalledTimes(1);
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado degradado (degraded)
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — estado degradado', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockResolvedValue({
      ..._HEALTH_HEALTHY,
      system_status: 'degraded',
      components: {
        database: { status: 'healthy', latency_ms: 10, details: null },
        cache: { status: 'degraded', latency_ms: 250, details: 'Redis lento' },
        external_apis: { status: 'healthy', latency_ms: null, details: {} },
      },
    });
  });

  it('renderiza sem erro com sistema degradado', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Status do Sistema')).toBeInTheDocument();
    });
  });

  it('exibe status degraded no badge de sistema', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      // O badge exibe o system_status textualmente
      expect(screen.getByText('degraded')).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado não saudável (unhealthy) — getStatusColor linha 50
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — estado não saudável (unhealthy)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockResolvedValue({
      ..._HEALTH_HEALTHY,
      system_status: 'unhealthy',
      components: {
        database: { status: 'unhealthy', latency_ms: null, details: 'timeout' },
        cache: { status: 'unhealthy', latency_ms: null, details: 'down' },
        external_apis: { status: 'healthy', latency_ms: null, details: {} },
      },
    });
  });

  it('renderiza sem erros com sistema unhealthy (cobre getStatusColor linha 50)', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Status do Sistema')).toBeInTheDocument();
    });
  });

  it('exibe status unhealthy no badge', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('unhealthy')).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Status desconhecido — getStatusColor default (linha 52)
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — status desconhecido (default getStatusColor)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockResolvedValue({
      ..._HEALTH_HEALTHY,
      system_status: 'unknown_status',
      components: {
        database: { status: 'unknown_status', latency_ms: null, details: null },
        cache: { status: 'healthy', latency_ms: 5, details: null },
        external_apis: { status: 'healthy', latency_ms: null, details: {} },
      },
    });
  });

  it('renderiza sem erros com status desconhecido (cobre default linha 52)', async () => {
    render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Status do Sistema')).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Estado sem detalhe de APIs externas (details vazio)
// ──────────────────────────────────────────────────────────────────────────────

describe('HealthDashboard — External APIs sem detalhes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SdkService.checkHealthDetailed.mockResolvedValue({
      ..._HEALTH_HEALTHY,
      components: {
        database: { status: 'healthy', latency_ms: 10, details: null },
        cache: { status: 'healthy', latency_ms: 5, details: null },
        external_apis: { status: 'healthy', latency_ms: null, details: {} },
      },
    });
  });

  it('renderiza External APIs mesmo com details vazio', async () => {
    const { unmount } = render(<HealthDashboard />);
    await waitFor(() => {
      expect(screen.getByText('External APIs')).toBeInTheDocument();
    });
    unmount();
  });
});
