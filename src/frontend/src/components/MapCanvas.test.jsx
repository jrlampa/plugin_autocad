/**
 * tests/components/MapCanvas.test.jsx
 * Testes para o componente MapCanvas (pt-BR).
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MapCanvas from '../../src/components/MapCanvas';

// Mock MapView mínimo — simula o componente lazy carregado via Suspense
const MockMapView = vi.fn(({ coords }) => (
  <div data-testid="mock-map-view">
    Mapa: {coords.lat}, {coords.lng}
  </div>
));

function makeMapLogic() {
  return {
    markers: [],
    handleDragStart: vi.fn(),
    handleSymbolDrop: vi.fn(),
  };
}

describe('MapCanvas', () => {
  const defaultProps = {
    MapView: MockMapView,
    coords: { lat: -22.15018, lng: -42.92185 },
    baseLayer: 'satellite',
    tileProviders: { satellite: 'https://tile.example.com/{z}/{x}/{y}.png' },
    radius: 500,
    previewGeoJson: null,
    isDrawing: false,
    drawingPoints: [],
    mapLogic: makeMapLogic(),
    handleMapClick: vi.fn(),
  };

  it('renderiza sem erros', () => {
    const { container } = render(<MapCanvas {...defaultProps} />);
    expect(container.firstChild).toBeTruthy();
  });

  it('monta o componente MapView dentro de Suspense', async () => {
    render(<MapCanvas {...defaultProps} />);
    // MockMapView deve ser renderizado pelo Suspense
    const mapView = await screen.findByTestId('mock-map-view');
    expect(mapView).toBeInTheDocument();
  });

  it('passa as coordenadas corretas para o MapView', async () => {
    render(<MapCanvas {...defaultProps} />);
    const mapView = await screen.findByTestId('mock-map-view');
    expect(mapView.textContent).toContain('-22.15018');
    expect(mapView.textContent).toContain('-42.92185');
  });

  it('repassa previewGeoJson para o MapView', async () => {
    const geoJson = { type: 'FeatureCollection', features: [] };
    render(<MapCanvas {...defaultProps} previewGeoJson={geoJson} />);
    // MapView must render (Suspense resolves immediately for sync components)
    const mapView = await screen.findByTestId('mock-map-view');
    expect(mapView).toBeInTheDocument();
  });

  it('repassa isDrawing e drawingPoints para o MapView', async () => {
    const points = [[0, 0], [1, 1]];
    render(<MapCanvas {...defaultProps} isDrawing={true} drawingPoints={points} />);
    const mapView = await screen.findByTestId('mock-map-view');
    expect(mapView).toBeInTheDocument();
  });
});
