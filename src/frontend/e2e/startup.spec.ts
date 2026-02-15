import { test, expect } from './fixtures';

test.describe('Startup & Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should initialize and send APP_READY handshake', async ({ page, getLastMessage }) => {
    // 1. Verify app loads
    await expect(page.locator('text=sisRUA')).toBeVisible();

    // 2. Wait for backend health check to pass (simulated by app logic)
    // The app sends APP_READY when backend is healthy.
    // We might need to wait a bit as the real api.checkHealth() is running against the real backend (or failing if not running)

    // In CI backend is running.
    // Verify APP_READY was sent to host
    await expect
      .poll(
        async () => {
          const msg = await getLastMessage();
          return msg?.action;
        },
        { timeout: 10000 }
      )
      .toBe('APP_READY');
  });

  test('should handle authentication flow from Host', async ({ page, sendToWebView }) => {
    // 1. Simulate Host sending INIT_AUTH_TOKEN
    await sendToWebView('INIT_AUTH_TOKEN', { token: 'mock-jwt-token-123' });

    // 2. Verify UI reflects authenticated state/ready
    // (In current UI there isn't a visible "Logged In" indicator, but we can verify no error banner)
    await expect(page.locator('text=Erro de Autenticação')).not.toBeVisible();

    // 3. Verify console log or internal state if possible (Harder in E2E blackbox)
    // We can verify that subsequent API calls use the token if we mock network,
    // but for now, we assume success if no error toast appears.
  });

  test('should sync geolocation from Host', async ({ page, sendToWebView }) => {
    // 1. Send GEOLOCATION_SYNC
    const mockLoc = { latitude: -23.55052, longitude: -46.633308 };
    await sendToWebView('GEOLOCATION_SYNC', mockLoc);

    // 2. Verify Input updates
    const input = page.getByPlaceholder(/Buscar endereço/i);
    await expect(input).toHaveValue(
      `${mockLoc.latitude.toFixed(6)}, ${mockLoc.longitude.toFixed(6)}`
    );

    // 3. Verify Map Center (requires inspecting Leaflet internal state or visual snapshot,
    // strictly we verify the input update which is bound to coords state)
  });
});
