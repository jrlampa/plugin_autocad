import { test, expect } from './fixtures';

test.describe('File Handling (Drag & Drop)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
  });

  test('should handle valid GeoJSON file drop', async ({ page }) => {
    const geoJsonContent = JSON.stringify({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { name: 'Test Point' },
          geometry: { type: 'Point', coordinates: [-46.63, -23.55] },
        },
      ],
    });

    await page.evaluate((content) => {
      const blob = new Blob([content], { type: 'application/geo+json' });
      const file = new File([blob], 'test.geojson', { type: 'application/geo+json' });

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      dataTransfer.types; // Accessing types property to ensure initialization in some browsers

      const dropZone = document.querySelector('[data-testid="app-root"]');
      if (!dropZone) throw new Error('Drop zone not found');

      // Dispatch Drag Enter
      dropZone.dispatchEvent(
        new DragEvent('dragenter', {
          bubbles: true,
          cancelable: true,
          dataTransfer,
        })
      );

      // Dispatch Drag Over
      dropZone.dispatchEvent(
        new DragEvent('dragover', {
          bubbles: true,
          cancelable: true,
          dataTransfer,
        })
      );

      // Dispatch Drop
      dropZone.dispatchEvent(
        new DragEvent('drop', {
          bubbles: true,
          cancelable: true,
          dataTransfer,
        })
      );
    }, geoJsonContent);

    // Verify Success indicator: Preview panel appears
    await expect(page.locator('text=GeoJSON carregado no mapa.')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('btn-import-geojson')).toBeVisible();
  });

  test('should handle invalid file drop', async ({ page }) => {
    await page.evaluate(() => {
      const blob = new Blob(['invalid data'], { type: 'text/plain' });
      const file = new File([blob], 'test.txt', { type: 'text/plain' });

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);

      const dropZone = document.querySelector('[data-testid="app-root"]');
      if (!dropZone) throw new Error('Drop zone not found');

      dropZone.dispatchEvent(
        new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer })
      );
      dropZone.dispatchEvent(
        new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer })
      );
      dropZone.dispatchEvent(
        new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer })
      );
    });

    // Verify Error Toast mapping the actual string in useFileProcessing.js
    await expect(page.locator('text=Erro ao ler arquivo')).toBeVisible({ timeout: 10000 });
  });
});
