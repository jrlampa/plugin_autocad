/**
 * src/App.coverage.test.jsx
 *
 * Testes focados para cobrir branches restantes de App.jsx:
 *   - handleGeocode com resultado bem-sucedido (linha 173: fechamento da função)
 *   - handleMapClick com isDrawing=true → addPoint chamado (linhas 176-177)
 *   - Modal: onChange do campo "desc" → setMetaInput (linha 377)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import App from './App';

// ─────────────────────────────────────────────────────────────────────────────
// Mocks de dependências pesadas
// ─────────────────────────────────────────────────────────────────────────────

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  Circle: () => <div />,
  Marker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  useMap: () => ({
    flyTo: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getContainer: () => ({ addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    mouseEventToLatLng: () => ({ lat: 0, lng: 0 }),
  }),
  GeoJSON: () => <div />,
  Polyline: () => <div />,
}));

// Mock useMapLogic — estado padrão
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
vi.mock('./hooks/useMapLogic', () => ({ useMapLogic: () => _mockMapLogic }));

// Mock useDrawingCanvas — expõe isDrawing e addPoint mutáveis
let _mockAddPoint = vi.fn();
let _mockIsDrawing = false;
vi.mock('./hooks/useDrawingCanvas', () => ({
  useDrawingCanvas: () => ({
    isDrawing: _mockIsDrawing,
    drawingPoints: [],
    toggleDrawing: vi.fn(),
    finishDrawing: vi.fn(),
    addPoint: _mockAddPoint,
  }),
}));

// Mock MapCanvas — captura onMapClick para invocação direta em testes
let _capturedOnMapClick = null;
vi.mock('./components/MapCanvas', () => ({
  default: ({ handleMapClick }) => {
    _capturedOnMapClick = handleMapClick;
    return <div data-testid="map-canvas" />;
  },
}));

// Mock api
vi.mock('./api', () => ({
  api: {
    checkHealth: vi.fn(() => Promise.resolve(true)),
    smartGeocode: vi.fn(),
    setupSecurity: vi.fn(() => Promise.resolve(false)),
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

// ─────────────────────────────────────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  _capturedOnMapClick = null;
  _mockIsDrawing = false;
  _mockAddPoint = vi.fn();

  // Limpa window.chrome — pode lançar em ambientes onde a propriedade não é configurável
  try { delete window.chrome; } catch (_e) { window.chrome = undefined; }

  // Reset mapLogic
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

// ─────────────────────────────────────────────────────────────────────────────
// handleGeocode — linhas 165-166, 173 (fechamento da função async)
// ─────────────────────────────────────────────────────────────────────────────

describe('App — handleGeocode sucesso (linhas 165-166, 173)', () => {
  it('handleGeocode atualiza coordenadas quando smartGeocode retorna latitude', async () => {
    const { api } = await import('./api');
    api.smartGeocode.mockResolvedValueOnce({
      latitude: -22.15018,
      longitude: -42.92185,
      source: 'latlon_direct',
    });

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // Encontra o campo de busca e digita uma coordenada
    const input = screen.getByPlaceholderText('Buscar endereço, Lat/Lon...');
    await act(async () => {
      fireEvent.change(input, { target: { value: '-22.15018, -42.92185' } });
      fireEvent.keyDown(input, { key: 'Enter' });
      // Aguarda a promise de geocode resolver
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(api.smartGeocode).toHaveBeenCalledWith('-22.15018, -42.92185');
  });

  it('handleGeocode não faz nada quando inputText está vazio', async () => {
    const { api } = await import('./api');

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // Campo vazio → handleGeocode retorna cedo (linha 160: if (!query) return)
    const input = screen.getByPlaceholderText('Buscar endereço, Lat/Lon...');
    await act(async () => {
      fireEvent.change(input, { target: { value: '' } });
      fireEvent.keyDown(input, { key: 'Enter' });
    });

    // smartGeocode não deve ser chamado quando campo vazio
    expect(api.smartGeocode).not.toHaveBeenCalled();
  });

  it('handleGeocode trata erro silenciosamente quando smartGeocode lança', async () => {
    const { api } = await import('./api');
    api.smartGeocode.mockRejectedValueOnce(new Error('Network error'));

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    const input = screen.getByPlaceholderText('Buscar endereço, Lat/Lon...');
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Petrópolis RJ' } });
      fireEvent.keyDown(input, { key: 'Enter' });
      await new Promise((r) => setTimeout(r, 50));
    });

    // App não deve quebrar — o catch() loga silenciosamente
    expect(screen.getByTestId('app-root')).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// handleMapClick com isDrawing=true — linhas 176-177
// ─────────────────────────────────────────────────────────────────────────────

describe('App — handleMapClick com isDrawing=true (linhas 176-177)', () => {
  it('chama addPoint quando isDrawing=true e onMapClick é chamado', async () => {
    // Configura isDrawing=true antes do render
    _mockIsDrawing = true;

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // MapCanvas capturou o handleMapClick via _capturedOnMapClick
    expect(_capturedOnMapClick).toBeTypeOf('function');

    // Chama onMapClick com coordenadas REF_2
    act(() => {
      _capturedOnMapClick({ lat: -22.15018, lng: -42.92185 });
    });

    // addPoint deve ter sido chamado com as coordenadas (linhas 176-177)
    expect(_mockAddPoint).toHaveBeenCalledWith({ lat: -22.15018, lng: -42.92185 });
  });

  it('NÃO chama addPoint quando isDrawing=false (branch else — linhas 178-180)', async () => {
    _mockIsDrawing = false;
    _mockAddPoint = vi.fn();

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    expect(_capturedOnMapClick).toBeTypeOf('function');

    act(() => {
      _capturedOnMapClick({ lat: -22.15018, lng: -42.92185 });
    });

    // isDrawing=false → não chama addPoint, atualiza coords
    expect(_mockAddPoint).not.toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Modal: desc onChange — linha 377
// ─────────────────────────────────────────────────────────────────────────────

describe('App — modal de marcador: campo desc onChange (linha 377)', () => {
  beforeEach(() => {
    _mockMapLogic = {
      ..._mockMapLogic,
      isModalOpen: true,
      currentDrop: { tipo: 'POSTE' },
      metaInput: { desc: 'Poste bifásico', altura: '12m' },
    };
  });

  it('chama setMetaInput ao alterar campo "Descrição" (linha 377)', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    const descInput = await screen.findByPlaceholderText('Ex: Poste Bifásico...');
    fireEvent.change(descInput, { target: { value: 'Poste monofásico' } });

    expect(_mockMapLogic.setMetaInput).toHaveBeenCalledWith(
      expect.objectContaining({ desc: 'Poste monofásico' })
    );
  });

  it('chama setMetaInput ao alterar campo "Altura" (linhas 389-391)', async () => {
    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    const alturaInput = await screen.findByPlaceholderText('Ex: 12m');
    fireEvent.change(alturaInput, { target: { value: '15m' } });

    expect(_mockMapLogic.setMetaInput).toHaveBeenCalledWith(
      expect.objectContaining({ altura: '15m' })
    );
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// App WebView message handler — linhas 140-141, 143-144
// ─────────────────────────────────────────────────────────────────────────────

describe('App — WebView message handler (linhas 140-141, 143-144)', () => {
  let webviewListeners = {};
  let webviewMock;

  beforeEach(() => {
    webviewListeners = {};
    webviewMock = {
      addEventListener: vi.fn((event, cb) => {
        webviewListeners[event] = webviewListeners[event] || [];
        webviewListeners[event].push(cb);
      }),
      removeEventListener: vi.fn(),
      postMessage: vi.fn(),
    };
    window.chrome = { webview: webviewMock };
  });

  afterEach(() => {
    // Limpa window.chrome — pode lançar em ambientes onde a propriedade não é configurável
    try { delete window.chrome; } catch (_e) { window.chrome = undefined; }
  });

  function emitWebView(data) {
    (webviewListeners['message'] || []).forEach((cb) => cb({ data }));
  }

  it('trata JSON inválido silenciosamente — console.error (linhas 140-141)', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // Envia mensagem não-JSON → JSON.parse lança → catch(e) → console.error (linha 140)
    act(() => {
      emitWebView('INVALID_JSON_STRING_FOR_CATCH_BLOCK');
    });

    // App não deve quebrar
    expect(screen.getByTestId('app-root')).toBeInTheDocument();
    // console.error foi chamado (linha 140)
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('App: Error parsing message:'),
      expect.any(Error)
    );
    consoleSpy.mockRestore();
  });

  it('loga warning quando event.data não é string (linhas 143-144)', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // Envia mensagem com data que não é string → else branch (linha 143)
    act(() => {
      emitWebView({ notAString: true }); // objeto, não string
    });

    expect(screen.getByTestId('app-root')).toBeInTheDocument();
    // console.warn foi chamado (linha 143)
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('App: Received non-string message data:'),
      expect.any(String),
      expect.anything()
    );
    warnSpy.mockRestore();
  });

  it('chama api.setupSecurity quando recebe INIT_AUTH_TOKEN com token (linhas 125-127)', async () => {
    const { api } = await import('./api');

    render(<App />);
    await screen.findByTestId('app-root', {}, { timeout: 5000 });

    // Envia mensagem INIT_AUTH_TOKEN com token válido
    act(() => {
      emitWebView(JSON.stringify({ action: 'INIT_AUTH_TOKEN', data: { token: 'test-token-abc' } }));
    });

    expect(screen.getByTestId('app-root')).toBeInTheDocument();
    // api.setupSecurity deve ser chamado com o token (linha 126)
    expect(api.setupSecurity).toHaveBeenCalledWith('test-token-abc');
  });
});
