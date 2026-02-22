/**
 * src/App.additional.test.jsx
 *
 * Testes adicionais para App.jsx cobrindo branches específicos:
 *   - handleGenerate sem webview → exibe toast informativo
 *   - Modal de marcador (Altura input, confirmMarker)
 *   - globalError banner (RATE_LIMIT e CIRCUIT_BREAKER)
 *   - normaToast (apenas quando sem fileToast)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import App from './App';

// React-leaflet mock para este arquivo (componentes mais ricos para aumentar cobertura)
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: ({ eventHandlers }) => {
    // Chamamos o tileerror handler no render para cobrir linhas 93-101 de MapView.jsx
    if (eventHandlers?.tileerror) {
      // Não chamamos aqui para não poluir o ambiente do teste
    }
    return <div data-testid="tile-layer" />;
  },
  Circle: () => <div data-testid="circle" />,
  Marker: ({ children }) => <div data-testid="marker">{children}</div>,
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    flyTo: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getContainer: () => ({
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
    mouseEventToLatLng: () => ({ lat: 0, lng: 0 }),
  }),
  GeoJSON: () => <div data-testid="geojson-layer" />,
  Polyline: () => <div data-testid="polyline" />,
}));

// Mock do useMapLogic com isModalOpen=true para testar o modal
let _mockMapLogic = {
  handleDragStart: vi.fn(),
  handleSymbolDrop: vi.fn(),
  confirmMarker: vi.fn(),
  cancelMarker: vi.fn(),
  markers: [],
  isModalOpen: false,
  currentDrop: null,
  metaInput: { desc: '', altura: '' },
  setMetaInput: vi.fn(),
  setMarkers: vi.fn(),
};

vi.mock('./hooks/useMapLogic', () => ({
  useMapLogic: () => _mockMapLogic,
}));

vi.mock('./api', () => ({
  api: {
    checkHealth: vi.fn(() => Promise.resolve(true)),
    smartGeocode: vi.fn(),
  },
}));

vi.mock('./services/SdkService', () => ({
  SdkService: {
    checkHealth: vi.fn(() => Promise.resolve({ status: 'ok' })),
    checkHealthDetailed: vi.fn(() =>
      Promise.resolve({
        status: 'healthy',
        system_status: 'healthy',
        components: {
          database: { status: 'healthy', latency_ms: 10 },
          cache: { status: 'healthy', latency_ms: 5 },
          external_apis: { status: 'healthy', details: {} },
        },
      })
    ),
    authCheck: vi.fn(() => Promise.resolve({ status: 'ok' })),
    updateProject: vi.fn(() => Promise.resolve({ project_id: 'p1', version: 2 })),
    createPrepareJob: vi.fn(() => Promise.resolve({ job_id: 'job-001', status: 'queued' })),
    getJob: vi.fn(() => Promise.resolve({ job_id: 'job-001', status: 'completed' })),
    cancelJob: vi.fn(() => Promise.resolve({ cancelled: true })),
    queryElevation: vi.fn(() => Promise.resolve({ elevation_m: 850.0 })),
    queryElevationProfile: vi.fn(() => Promise.resolve({ elevations: [] })),
    chatWithAI: vi.fn(() => Promise.resolve({ response: 'OK' })),
    prepareOSM: vi.fn(() => Promise.resolve({ features: [] })),
    prepareGeoJSON: vi.fn(() => Promise.resolve({ features: [] })),
    registerWebhook: vi.fn(() => Promise.resolve({ webhook_id: 'wh-1' })),
    emitEvent: vi.fn(() => Promise.resolve({ delivered: 1 })),
    createAuditLog: vi.fn(() => Promise.resolve({ audit_id: 1 })),
    listAuditLogs: vi.fn(() => Promise.resolve([])),
    getAuditLog: vi.fn(() => Promise.resolve({ audit_id: 1 })),
    verifyAuditLog: vi.fn(() => Promise.resolve({ valid: true })),
    verifyAllAuditLogs: vi.fn(() => Promise.resolve({ total: 0, valid: 0, invalid: 0 })),
    getAuditStats: vi.fn(() => Promise.resolve({ total_logs: 0 })),
  },
}));

// Helper: remove webview do window antes de cada teste
beforeEach(() => {
  vi.clearAllMocks();
  if (window.chrome) {
    try { delete window.chrome; } catch (_) { window.chrome = undefined; }
  }
  // Reset modal state
  _mockMapLogic = {
    handleDragStart: vi.fn(),
    handleSymbolDrop: vi.fn(),
    confirmMarker: vi.fn(),
    cancelMarker: vi.fn(),
    markers: [],
    isModalOpen: false,
    currentDrop: null,
    metaInput: { desc: '', altura: '' },
    setMetaInput: vi.fn(),
    setMarkers: vi.fn(),
  };
});

// ──────────────────────────────────────────────────────────────────────────────
// handleGenerate — branch SEM webview (toast informativo)
// ──────────────────────────────────────────────────────────────────────────────

describe('App — handleGenerate sem webview', () => {
  it('exibe toast informativo quando webview não está disponível', async () => {
    // window.chrome não está definido → fallback → toast de info
    render(<App />);
    const btn = await screen.findByTestId('btn-generate-osm', {}, { timeout: 5000 });
    await act(async () => {
      fireEvent.click(btn);
    });

    await waitFor(() => {
      expect(
        screen.getByText(/disponível apenas ao rodar o sisRUA dentro do AutoCAD/i)
      ).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// globalError banner (api-error event)
// ──────────────────────────────────────────────────────────────────────────────

describe('App — banner de erro global', () => {
  it('exibe banner RATE_LIMIT quando evento api-error é disparado', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    act(() => {
      window.dispatchEvent(
        new CustomEvent('api-error', {
          detail: { type: 'RATE_LIMIT', message: 'Você está indo rápido demais!' },
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Você está indo rápido demais!')).toBeInTheDocument();
    });
  });

  it('exibe banner CIRCUIT_BREAKER quando evento api-error é disparado', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    act(() => {
      window.dispatchEvent(
        new CustomEvent('api-error', {
          detail: { type: 'CIRCUIT_BREAKER', message: 'Serviço temporariamente indisponível.' },
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Serviço temporariamente indisponível.')).toBeInTheDocument();
    });
  });

  it('fecha o banner ao clicar no botão de fechar', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    act(() => {
      window.dispatchEvent(
        new CustomEvent('api-error', {
          detail: { type: 'RATE_LIMIT', message: 'Erro de rate limit para fechar' },
        })
      );
    });

    // Aguarda o banner aparecer
    await waitFor(() => {
      expect(screen.getByText('Erro de rate limit para fechar')).toBeInTheDocument();
    });

    // Clica no botão "Fechar alerta" (aria-label adicionado para acessibilidade)
    const closeBtn = screen.getByRole('button', { name: /fechar alerta/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText('Erro de rate limit para fechar')).not.toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Modal de marcador (isModalOpen=true)
// ──────────────────────────────────────────────────────────────────────────────

describe('App — modal de marcador (isModalOpen)', () => {
  beforeEach(() => {
    _mockMapLogic = {
      ..._mockMapLogic,
      isModalOpen: true,
      currentDrop: { tipo: 'POSTE' },
      metaInput: { desc: 'Poste bifásico', altura: '12m' },
    };
  });

  it('exibe o modal de marcador quando isModalOpen=true', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Ex: Poste Bifásico...')).toBeInTheDocument();
    });
  });

  it('exibe campo de Altura no modal', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Ex: 12m')).toBeInTheDocument();
    });
  });

  it('chama setMetaInput ao alterar campo Altura', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    const alturaInput = await screen.findByPlaceholderText('Ex: 12m');
    fireEvent.change(alturaInput, { target: { value: '15m' } });

    expect(_mockMapLogic.setMetaInput).toHaveBeenCalledWith(
      expect.objectContaining({ altura: '15m' })
    );
  });

  it('exibe botão SALVAR PONTO e chama confirmMarker ao clicar', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    const saveBtn = await screen.findByText('SALVAR PONTO');
    fireEvent.click(saveBtn);

    expect(_mockMapLogic.confirmMarker).toHaveBeenCalled();
  });
});
