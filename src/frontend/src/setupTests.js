// src/setupTests.js
import '@testing-library/jest-dom';
import { vi } from 'vitest';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { status: 'ok' } })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
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

// Mock do SdkService para evitar fetch failed no SdkTest component
vi.mock('./services/SdkService', () => ({
  SdkService: {
    checkHealth: vi.fn(() => Promise.resolve({ status: 'ok' })),
    checkHealthDetailed: vi.fn(() =>
      Promise.resolve({
        status: 'healthy',
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
