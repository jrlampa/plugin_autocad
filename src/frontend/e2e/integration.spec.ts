import { test, expect } from '@playwright/test';

/**
 * E2E Integration Tests for sisRUA Frontend
 * These tests validate cross-component interactions.
 */

test.describe('sisRUA Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for app to load
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should load the main application', async ({ page }) => {
    // Check that main UI elements are present
    await expect(page.locator('text=sisRUA')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Localização do Projeto/i)).toBeVisible();
  });

  test('should have a functional search input', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await expect(searchInput).toBeVisible();

    // Type a location and verify input works
    await searchInput.fill('-23.55, -46.63');
    await expect(searchInput).toHaveValue('-23.55, -46.63');
  });

  test('should have a radius slider', async ({ page }) => {
    // Check for radius control
    await expect(page.getByText(/Raio de Abrangência/i)).toBeVisible();

    // Check slider exists
    const slider = page.locator('input[type="range"]').first();
    await expect(slider).toBeVisible();
  });

  test('should have OSM generate button', async ({ page }) => {
    // Check for generate button
    const generateBtn = page.getByTestId('btn-generate-osm');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeEnabled();
  });

  test('should display map container', async ({ page }) => {
    // The map container should be present
    const mapContainer = page.locator('.leaflet-container');
    await expect(mapContainer).toBeVisible({ timeout: 5000 });
  });
});

test.describe('API Health Check', () => {
  test('should respond to health endpoint', async ({ request }) => {
    const response = await request.get('/api/v1/health');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('ok');
  });
});
