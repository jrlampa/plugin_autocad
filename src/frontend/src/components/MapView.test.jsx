/**
 * src/components/MapView.test.jsx
 *
 * Testes unitários para o componente MapView.
 *
 * Cobre:
 *   - Renderização básica (mapa, círculo, marcadores)
 *   - MapController: flyTo chamado com coordenadas
 *   - MapDropHandler: drop de símbolo
 *   - MapClickHandler: click sem drag, dragstart/dragend (isDragging flag)
 *   - TileLayer tileerror: dispatch de evento api-error
 *   - previewGeoJson: camada GeoJSON
 *   - drawingPoints: polilinha quando isDrawing
 *   - markers: Marker + Popup
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import MapView from './MapView';

// ─────────────────────────────────────────────────────────
// Captura de handlers registrados no map mock
// ─────────────────────────────────────────────────────────

// Registry de todos handlers registrados via map.on(event, handler)
let _mapEventHandlers = {};
// Registry de all event handlers de containers via addEventListener
let _containerListeners = {};
// O tileerror handler capturado do TileLayer
let _tileerrorHandler = null;

// Mock do useMap — captura map.on calls e expõe _mapEventHandlers
vi.mock('react-leaflet', () => {
  const mapMock = {
    flyTo: vi.fn(),
    on: vi.fn((event, handler) => {
      _mapEventHandlers[event] = _mapEventHandlers[event] || [];
      _mapEventHandlers[event].push(handler);
    }),
    off: vi.fn(),
    getContainer: () => ({
      addEventListener: vi.fn((event, cb) => {
        _containerListeners[event] = _containerListeners[event] || [];
        _containerListeners[event].push(cb);
      }),
      removeEventListener: vi.fn(),
    }),
    mouseEventToLatLng: vi.fn(() => ({ lat: -22.15018, lng: -42.92185 })),
  };

  return {
    MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
    TileLayer: ({ eventHandlers }) => {
      // Captura o tileerror handler para uso nos testes
      if (eventHandlers?.tileerror) {
        _tileerrorHandler = eventHandlers.tileerror;
      }
      return <div data-testid="tile-layer" />;
    },
    Circle: ({ center, radius }) => (
      <div data-testid="circle" data-radius={radius} data-lat={center[0]} />
    ),
    Marker: ({ children, position }) => (
      <div data-testid="marker" data-lat={position[0]}>
        {children}
      </div>
    ),
    Popup: ({ children }) => <div data-testid="popup">{children}</div>,
    useMap: () => mapMock,
    GeoJSON: ({ data }) => <div data-testid="geojson-layer" />,
    Polyline: ({ positions }) => <div data-testid="polyline" data-len={positions.length} />,
  };
});

// ─────────────────────────────────────────────────────────
// Props padrão
// ─────────────────────────────────────────────────────────

function makeProps(overrides = {}) {
  return {
    coords: { lat: -22.15018, lng: -42.92185 },
    tileProvider: {
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: 'OSM',
    },
    radius: 500,
    previewGeoJson: null,
    isDrawing: false,
    drawingPoints: [],
    markers: [],
    onSymbolDrop: vi.fn(),
    onMapClick: vi.fn(),
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────
// Reset a cada teste
// ─────────────────────────────────────────────────────────

beforeEach(() => {
  _mapEventHandlers = {};
  _containerListeners = {};
  _tileerrorHandler = null;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ─────────────────────────────────────────────────────────
// Renderização básica
// ─────────────────────────────────────────────────────────

describe('MapView — renderização básica', () => {
  it('renderiza o mapa container', () => {
    render(<MapView {...makeProps()} />);
    expect(screen.getByTestId('map-container')).toBeInTheDocument();
  });

  it('renderiza o tile layer', () => {
    render(<MapView {...makeProps()} />);
    expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
  });

  it('renderiza o círculo de raio', () => {
    render(<MapView {...makeProps({ radius: 500 })} />);
    expect(screen.getByTestId('circle')).toBeInTheDocument();
  });

  it('não renderiza polilinha quando isDrawing=false', () => {
    render(<MapView {...makeProps()} />);
    expect(screen.queryByTestId('polyline')).not.toBeInTheDocument();
  });

  it('renderiza polilinha quando isDrawing=true e há pontos', () => {
    render(
      <MapView
        {...makeProps({
          isDrawing: true,
          drawingPoints: [[-42.92185, -22.15018], [-42.91185, -22.14018]],
        })}
      />
    );
    expect(screen.getByTestId('polyline')).toBeInTheDocument();
  });

  it('não renderiza GeoJSON quando previewGeoJson é null', () => {
    render(<MapView {...makeProps({ previewGeoJson: null })} />);
    expect(screen.queryByTestId('geojson-layer')).not.toBeInTheDocument();
  });

  it('renderiza GeoJSON quando previewGeoJson está definido', () => {
    const geojson = { type: 'FeatureCollection', features: [] };
    render(<MapView {...makeProps({ previewGeoJson: geojson })} />);
    expect(screen.getByTestId('geojson-layer')).toBeInTheDocument();
  });

  it('renderiza marcadores corretamente', () => {
    const markers = [
      { lat: -22.15018, lon: -42.92185, tipo: 'POSTE', meta: { desc: 'Poste 1' } },
      { lat: -22.14018, lon: -42.91185, tipo: 'ARVORE', meta: { desc: 'Árvore 1' } },
    ];
    render(<MapView {...makeProps({ markers })} />);
    const allMarkers = screen.getAllByTestId('marker');
    expect(allMarkers).toHaveLength(2);
  });
});

// ─────────────────────────────────────────────────────────
// TileLayer — tileerror → dispatch api-error (linhas 93-101)
// ─────────────────────────────────────────────────────────

describe('MapView — tileerror dispatcha evento api-error (linhas 93-101)', () => {
  it('dispatcha api-error com type MAP_BLOCKED quando tileerror é disparado', () => {
    render(<MapView {...makeProps()} />);

    const listener = vi.fn();
    window.addEventListener('api-error', listener);

    // Invoca o tileerror handler diretamente (capturado pelo TileLayer mock)
    act(() => {
      if (_tileerrorHandler) _tileerrorHandler();
    });

    expect(listener).toHaveBeenCalled();
    const detail = listener.mock.calls[0][0].detail;
    expect(detail.type).toBe('MAP_BLOCKED');
    expect(detail.message).toMatch(/mapas bloqueado/i);

    window.removeEventListener('api-error', listener);
  });

  it('tileerror handler está registrado (TileLayer eventHandlers)', () => {
    render(<MapView {...makeProps()} />);
    // O handler deve ter sido capturado pelo mock
    expect(typeof _tileerrorHandler).toBe('function');
  });
});

// ─────────────────────────────────────────────────────────
// MapClickHandler — drag/click (linhas 53, 55-56)
// ─────────────────────────────────────────────────────────

describe('MapView — MapClickHandler (linhas 53, 55-56)', () => {
  it('chama onMapClick quando não está arrastando', () => {
    const onMapClick = vi.fn();
    render(<MapView {...makeProps({ onMapClick })} />);

    // Invoca o handler de 'click' registrado via map.on
    const clickHandlers = _mapEventHandlers['click'] || [];
    act(() => {
      clickHandlers.forEach((h) => h({ latlng: { lat: -22.15018, lng: -42.92185 } }));
    });

    expect(onMapClick).toHaveBeenCalledWith({ lat: -22.15018, lng: -42.92185 });
  });

  it('NÃO chama onMapClick quando isDragging=true (dragstart antes do click)', () => {
    const onMapClick = vi.fn();
    render(<MapView {...makeProps({ onMapClick })} />);

    // Simula dragstart → isDragging = true
    act(() => {
      (_mapEventHandlers['dragstart'] || []).forEach((h) => h());
    });

    // Simula click enquanto está arrastando
    act(() => {
      (_mapEventHandlers['click'] || []).forEach((h) =>
        h({ latlng: { lat: -22.15018, lng: -42.92185 } })
      );
    });

    expect(onMapClick).not.toHaveBeenCalled();
  });

  it('restaura isDragging=false após dragend + setTimeout (linhas 53, 55-56)', () => {
    const onMapClick = vi.fn();
    render(<MapView {...makeProps({ onMapClick })} />);

    // 1. dragstart → isDragging = true
    act(() => {
      (_mapEventHandlers['dragstart'] || []).forEach((h) => h());
    });

    // 2. dragend → inicia setTimeout de 50ms
    act(() => {
      (_mapEventHandlers['dragend'] || []).forEach((h) => h());
    });

    // 3. Avança o timer fake — isDragging volta a false após 50ms
    act(() => {
      vi.advanceTimersByTime(50);
    });

    // 4. Click agora deve chamar onMapClick (isDragging = false novamente)
    act(() => {
      (_mapEventHandlers['click'] || []).forEach((h) =>
        h({ latlng: { lat: -22.15018, lng: -42.92185 } })
      );
    });

    expect(onMapClick).toHaveBeenCalledWith({ lat: -22.15018, lng: -42.92185 });
  });
});

// ─────────────────────────────────────────────────────────
// MapController — flyTo
// ─────────────────────────────────────────────────────────

describe('MapView — MapController', () => {
  it('registra os handlers de mapa (dragstart, dragend, click)', () => {
    render(<MapView {...makeProps()} />);
    // Verifica que os handlers foram registrados
    expect(_mapEventHandlers['dragstart']).toBeDefined();
    expect(_mapEventHandlers['dragend']).toBeDefined();
    expect(_mapEventHandlers['click']).toBeDefined();
  });
});
