import { render, screen, fireEvent, act } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App';
import React from 'react';

// Mock do react-leaflet para evitar erros de canvas/webgl no jsdom
vi.mock('react-leaflet', () => {
  return {
    MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
    TileLayer: () => <div data-testid="tile-layer" />,
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
  };
});

// Mock do useMapLogic
vi.mock('./hooks/useMapLogic', () => ({
  useMapLogic: () => ({
    handleDragStart: vi.fn(),
    handleSymbolDrop: vi.fn(),
    markers: [],
    isModalOpen: false,
    metaInput: {},
    setMetaInput: vi.fn(),
    confirmMarker: vi.fn(),
    cancelMarker: vi.fn(),
  }),
}));

// Mock do api.js
vi.mock('./api', () => ({
  api: {
    checkHealth: vi.fn(() => Promise.resolve(true)),
    smartGeocode: vi.fn(),
  },
}));

describe('App Integration (Rigorous)', () => {
  let postMessageMock;
  let messageListeners = [];

  beforeEach(() => {
    // Reset mocks e listeners
    postMessageMock = vi.fn();
    messageListeners = [];

    // Mock do window.chrome.webview
    window.chrome = {
      webview: {
        postMessage: postMessageMock,
        addEventListener: (event, handler) => {
          if (event === 'message') {
            messageListeners.push(handler);
          }
        },
        removeEventListener: (event, handler) => {
          if (event === 'message') {
            messageListeners = messageListeners.filter((h) => h !== handler);
          }
        },
      },
    };
  });

  afterEach(() => {
    delete window.chrome;
    vi.clearAllMocks();
  });

  // Helper para simular envio de mensagem do Host (C#) para o Frontend
  const simulateHostMessage = (data) => {
    const event = { data: JSON.stringify(data) };
    act(() => {
      messageListeners.forEach((handler) => handler(event));
    });
  };

  it('deve enviar mensagem GENERATE_OSM ao clicar no botão gerar', async () => {
    render(<App />);
    await screen.findByText(/sisRUA/i, {}, { timeout: 3000 });

    const btn = screen.getByTestId('btn-generate-osm');
    fireEvent.click(btn);

    expect(postMessageMock).toHaveBeenCalledTimes(1);
    const sentMsg = postMessageMock.mock.calls[0][0];

    expect(sentMsg.action).toBe('GENERATE_OSM');
    expect(sentMsg.data).toHaveProperty('latitude');
    expect(sentMsg.data).toHaveProperty('longitude');
    expect(sentMsg.data).toHaveProperty('radius');
  });

  it('deve atualizar UI ao receber JOB_PROGRESS (Processing -> Completed)', async () => {
    render(<App />);
    await screen.findByText(/sisRUA/i, {}, { timeout: 3000 });

    // 1. Iniciar processamento
    simulateHostMessage({
      action: 'JOB_PROGRESS',
      data: { status: 'processing', progress: 0.5, message: 'Baixando OSM...' },
    });

    // Validar visualização do progresso
    expect(await screen.findByText(/Processando/i)).toBeInTheDocument();
    expect(screen.getByText(/Baixando OSM/i)).toBeInTheDocument();

    // 2. Concluir processamento
    simulateHostMessage({
      action: 'JOB_PROGRESS',
      data: { status: 'completed', progress: 1.0, message: 'Sucesso' },
    });

    expect(await screen.findByText(/Concluído/i)).toBeInTheDocument();
  });

  it('deve mostrar preview e botão importar ao receber FILE_DROPPED do Host', async () => {
    render(<App />);
    await screen.findByText(/sisRUA/i, {}, { timeout: 3000 });

    const fakeGeoJson = {
      type: 'FeatureCollection',
      features: [
        { type: 'Feature', geometry: { type: 'Point', coordinates: [0, 0] }, properties: {} },
      ],
    };

    // Simular o C# enviando o conteúdo do arquivo que foi solto na Palette
    simulateHostMessage({
      action: 'FILE_DROPPED_GEOJSON',
      data: { content: JSON.stringify(fakeGeoJson) },
    });

    // Deve aparecer o botão de "Importar para o AutoCAD"
    const btnImport = await screen.findByTestId('btn-import-geojson');
    expect(btnImport).toBeInTheDocument();
    expect(screen.getByText(/Preview de Campo/i)).toBeInTheDocument();

    // Clicar no botão deve enviar mensagem de volta ao Host
    fireEvent.click(btnImport);

    expect(postMessageMock).toHaveBeenCalledTimes(1); // Pode ter sido resetado ou acumulado se o setup fosse diferente, mas aqui é novo render
    const sentMsg = postMessageMock.mock.calls[0][0];

    expect(sentMsg.action).toBe('IMPORT_GEOJSON');
    // Verifica se os dados enviados batem com o que foi recebido
    const sentData = JSON.parse(sentMsg.data);
    expect(sentData.type).toBe('FeatureCollection');
  });
});
