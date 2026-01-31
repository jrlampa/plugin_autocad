import { render, screen, act } from '@testing-library/react';
import App from './App';
import { vi, describe, it, expect, beforeAll } from 'vitest';

describe('Geolocation Sync integration', () => {
  beforeAll(() => {
    // Mock window.chrome.webview
    if (!window.chrome) window.chrome = {};
    if (!window.chrome.webview) {
      window.chrome.webview = {
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        postMessage: vi.fn(),
      };
    }
  });

  it('updates coordinates when GEOLOCATION_SYNC is received', async () => {
    render(<App />);
    await screen.findByText(/sisRUA/i, {}, { timeout: 3000 });

    // Simular o recebimento de mensagem da WebView
    // O App.jsx usa window.chrome.webview.addEventListener('message', ...)
    // Precisamos disparar o evento no objeto mockado.

    // Pega a função de callback registrada
    const [[eventName, callback]] = window.chrome.webview.addEventListener.mock.calls.filter(
      (call) => call[0] === 'message'
    );

    expect(eventName).toBe('message');

    act(() => {
      callback({
        data: JSON.stringify({
          action: 'GEOLOCATION_SYNC',
          data: { latitude: -23.5505, longitude: -46.6333 },
        }),
      });
    });

    // O App.jsx formata com 6 casas decimais: `${lat.toFixed(6)}, ${lng.toFixed(6)}`
    // -23.550500, -46.633300
    const input = screen.getByPlaceholderText(/Buscar endereço, Lat\/Lon.../i);
    expect(input.value).toBe('-23.550500, -46.633300');
  });
});
