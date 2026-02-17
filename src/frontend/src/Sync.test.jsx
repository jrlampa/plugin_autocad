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

    // Wait for app to be fully loaded (backend ready)
    await screen.findByTestId('app-root', {}, { timeout: 5000 });
    await screen.findByText(/sisRUA/i, {}, { timeout: 3000 });

    // Simular o recebimento de mensagem da WebView
    // O App.jsx usa window.chrome.webview.addEventListener('message', ...)
    // Precisamos disparar o evento no objeto mockado.

    // Pega todos os callbacks registrados para 'message'
    const messageCalls = window.chrome.webview.addEventListener.mock.calls.filter(
      (call) => call[0] === 'message'
    );

    expect(messageCalls.length).toBeGreaterThan(0);

    act(() => {
      // Dispara o evento para TODOS os listeners registrados
      messageCalls.forEach(([, callback]) => {
        callback({
          data: JSON.stringify({
            action: 'GEOLOCATION_SYNC',
            data: { latitude: -23.5505, longitude: -46.6333 },
          }),
        });
      });
    });

    // O App.jsx formata com 6 casas decimais: `${lat.toFixed(6)}, ${lng.toFixed(6)}`
    // -23.550500, -46.633300
    const input = screen.getByPlaceholderText(/Buscar endereço, Lat\/Lon.../i);

    // Aguardar a atualização do estado
    await screen.findByDisplayValue('-23.550500, -46.633300', {}, { timeout: 3000 });

    expect(input.value).toBe('-23.550500, -46.633300');
  });
});
