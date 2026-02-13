import { test, expect } from './fixtures';

test.describe('Resilience & Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
  });

  test('should display Rate Limit banner on 429 error', async ({ page }) => {
    // 1. Mock 429 on Geocode (Correct endpoint: tools/geocode)
    await page.route('**/api/v1/tools/geocode*', async (route) => {
      await route.fulfill({
        status: 429,
        body: JSON.stringify({ detail: 'Rate limit exceeded' }),
      });
    });

    // 2. Trigger Geocode
    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await searchInput.fill('Rate Limit Test');
    await searchInput.press('Enter');

    // 3. Verify Error Banner
    // Banner text: "Você está indo rápido demais!" (from api.js)
    await expect(page.locator('text=Você está indo rápido demais!')).toBeVisible({ timeout: 5000 });
  });

  test('should activate Circuit Breaker on 503 error', async ({ page }) => {
    // 1. Mock 503 on Geocode
    await page.route('**/api/v1/tools/geocode*', async (route) => {
      await route.fulfill({
        status: 503,
        body: JSON.stringify({ detail: 'Service Unavailable' }),
      });
    });

    // 2. Trigger Geocode
    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await searchInput.fill('Circuit Breaker Test');
    await searchInput.press('Enter');

    // 3. Verify Error Banner
    // Banner text: "Serviço temporariamente indisponível" (from api.js)
    await expect(page.locator('text=Serviço temporariamente indisponível')).toBeVisible({
      timeout: 5000,
    });
  });
});
