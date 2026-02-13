import { test, expect } from './fixtures';

test.describe('Host Bridge (IPC) & Job Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 });
  });

  test('should send GENERATE_OSM command when user generates project', async ({
    page,
    getLastMessage,
  }) => {
    const generateBtn = page.getByTestId('btn-generate-osm');
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    await expect
      .poll(
        async () => {
          const msg = await getLastMessage();
          return msg?.action;
        },
        { timeout: 5000 }
      )
      .toBe('GENERATE_OSM');

    const msg = await getLastMessage();
    expect(msg.data).toBeDefined();
    // Default radius is 500
    expect(msg.data.radius).toBe(500);
  });

  test('should display Job Overlay when receiving JOB_PROGRESS', async ({
    page,
    sendToWebView,
  }) => {
    const jobData = {
      id: 'job-123',
      status: 'processing',
      message: 'Analisando topologia...',
      progress: 0.45,
    };

    // 2. Simulate Incoming Message
    // Add artificial delay to ensure listener is bound
    await page.waitForTimeout(1000);

    await sendToWebView('JOB_PROGRESS', jobData);

    // 3. Verify Overlay Appears
    const overlay = page.getByTestId('job-overlay');

    await expect(overlay).toBeVisible({ timeout: 5000 });
    await expect(overlay).toContainText('Processando');
    await expect(overlay).toContainText('Analisando topologia...');
    await expect(overlay).toContainText('45%');

    // 4. Update to Completed
    await sendToWebView('JOB_PROGRESS', {
      ...jobData,
      status: 'completed',
      progress: 1.0,
      message: 'Sucesso!',
    });
    await expect(overlay).toContainText('Concluído');
  });
});
