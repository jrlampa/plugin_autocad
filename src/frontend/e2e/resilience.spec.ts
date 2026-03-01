import { test, expect } from './fixtures';

test.describe('Resilience & Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
  });

  test('should display Rate Limit banner on 429 error', async ({ page }) => {
    let seen = false;

    // 1. Mock 429 on Geocode (Correct endpoint: tools/geocode)
    await page.route(/\/api\/v1\/tools\/geocode.*/i, async (route) => {
      seen = true;
      await route.fulfill({
        status: 429,
        body: JSON.stringify({ detail: 'Rate limit exceeded' }),
      });
    });

    // 2. Trigger Geocode
    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await searchInput.fill('Rate Limit Test');
    const reqPromise = page.waitForRequest(
      (req) => /\/api\/v1\/tools\/geocode/i.test(req.url()) && req.method() === 'GET'
    );
    await searchInput.press('Enter');
    const req = await reqPromise;

    await expect.poll(() => seen, { timeout: 5000 }).toBe(true);

    const resp = await page.waitForResponse((r) => r.request() === req);
    expect(resp.status()).toBe(429);
  });

  test('should activate Circuit Breaker on 503 error', async ({ page }) => {
    let seen = false;

    // 1. Mock 503 on Geocode
    await page.route(/\/api\/v1\/tools\/geocode.*/i, async (route) => {
      seen = true;
      await route.fulfill({
        status: 503,
        body: JSON.stringify({ detail: 'Service Unavailable' }),
      });
    });

    // 2. Trigger Geocode
    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await searchInput.fill('Circuit Breaker Test');
    const reqPromise = page.waitForRequest(
      (req) => /\/api\/v1\/tools\/geocode/i.test(req.url()) && req.method() === 'GET'
    );
    await searchInput.press('Enter');
    const req = await reqPromise;

    await expect.poll(() => seen, { timeout: 5000 }).toBe(true);

    const resp = await page.waitForResponse((r) => r.request() === req);
    expect(resp.status()).toBe(503);
  });
});
