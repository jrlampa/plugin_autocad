import { test, expect } from './fixtures';

test.describe('Map Interaction & Drawing', () => {
  test.beforeEach(async ({ page }) => {
    console.log('Navigating to root...');
    await page.goto('/');
    console.log('Waiting for map container...');
    // Wait for map to be visible (implies Backend is Ready)
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
    console.log('Map container found.');
  });

  test('should enter drawing mode when requested via Sidebar', async ({ page }) => {
    // 1. Click "Desenhar Rua" button using testId
    const drawBtn = page.getByTestId('btn-toggle-drawing');

    await expect(drawBtn).toBeAttached();
    console.log('Clicking Draw Button...');
    await drawBtn.click();
    console.log('Clicked Draw Button.');

    // 2. Verify Drawing UI state
    // Verify button class changed to red (bg-red-500)
    console.log('Waiting for red class...');
    await expect(drawBtn).toHaveClass(/bg-red-500/, { timeout: 5000 });
    console.log('Button has red class.');
  });

  test('should draw a polygon and finish drawing', async ({ page }) => {
    // 1. Start Drawing
    const drawBtn = page.getByTestId('btn-toggle-drawing');
    await drawBtn.click();

    // 2. Simulate clicks on the map
    const map = page.locator('.leaflet-container');

    // Leaflet map needs some time to process
    await page.waitForTimeout(1000);

    // Click points with some delay
    const box = await map.boundingBox();
    if (!box) throw new Error('Map container not found');

    console.log(`Map Box: ${JSON.stringify(box)}`);

    await map.click({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForTimeout(300);
    await map.click({ position: { x: box.width / 2 + 50, y: box.height / 2 } });
    await page.waitForTimeout(300);
    await map.click({ position: { x: box.width / 2 + 50, y: box.height / 2 + 50 } });
    await page.waitForTimeout(300);

    // 3. Verify "Finalizar Rua" button appears
    const finishBtn = page.getByTestId('btn-finish-drawing');
    console.log('Waiting for Finish Button...');
    await expect(finishBtn).toBeVisible();

    // 4. Click Finalizar
    console.log('Clicking Finish Button...');
    await finishBtn.click();

    // 5. Verify UI resets
    await expect(drawBtn).not.toHaveClass(/bg-red-500/);
    await expect(finishBtn).not.toBeVisible();
  });

  test('should handle geocoding search', async ({ page }) => {
    // Mock Geocoding API
    await page.route('**/api/v1/tools/geocode*', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          latitude: -23.55,
          longitude: -46.63,
          display_name: 'São Paulo, Brasil',
        }),
      });
    });

    const searchInput = page.getByPlaceholder(/Buscar endereço/i);
    await searchInput.fill('São Paulo');
    await searchInput.press('Enter');

    // Verify input updates with coordinates (app logic usually does this on success)
    await expect(searchInput).toHaveValue(/-23\.55.*-46\.63/, { timeout: 5000 });
  });
});
