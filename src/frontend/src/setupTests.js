// src/setupTests.js
import '@testing-library/jest-dom';
import { vi } from 'vitest';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { status: 'ok' } })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}));

// --- Mocks para evitar dependências pesadas no JSDOM (Leaflet/WebGL/tiles) ---

vi.mock('leaflet/dist/leaflet.css', () => ({}));
vi.mock('leaflet/dist/images/marker-icon.png', () => ({ default: 'marker-icon.png' }));
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({ default: 'marker-shadow.png' }));

vi.mock('leaflet', async () => {
  // Mock mínimo para não quebrar import do App.
  const L = {
    icon: () => ({}),
    Marker: function Marker() {},
  };
  L.Marker.prototype = { options: {} };
  return { default: L };
});

vi.mock('react-leaflet', async () => {
  const React = await import('react');
  const Div = ({ children, ...props }) => React.createElement('div', props, children);

  return {
    MapContainer: Div,
    TileLayer: () => null,
    Circle: () => null,
    Marker: Div,
    Popup: Div,
    GeoJSON: () => null,
    Polyline: () => null,
    useMap: () => ({
      getContainer: () => ({ addEventListener: () => {}, removeEventListener: () => {} }),
      on: () => {},
      flyTo: () => {},
      mouseEventToLatLng: () => ({ lat: 0, lng: 0 }),
    }),
  };
});

// Mock da API para evitar bloqueio no Health Check durante os testes
vi.mock('./api', () => ({
  api: {
    checkHealth: vi.fn(() => Promise.resolve(true)),
    smartGeocode: vi.fn(),
  },
}));
