import { test as base } from '@playwright/test';

// Define custom test fixtures
type AutoCadFixtures = {
  mockAutoCAD: void;
  sendToWebView: (action: string, data?: any) => Promise<void>;
  getLastMessage: () => Promise<any>;
  clearMessages: () => Promise<void>;
  mockBackend: void;
};

export const test = base.extend<AutoCadFixtures>({
  // Fixture to inject mock window.chrome.webview
  mockAutoCAD: [
    async ({ page }, use) => {
      await page.addInitScript(() => {
        // Mock storage for sent messages
        (window as any).__outgoingMessages = [];

        // Mock event listeners
        const listeners = new Map<string, Function[]>();

        (window as any).chrome = {
          webview: {
            postMessage: (message: any) => {
              console.log('[MockAutoCAD] Sent:', message);
              (window as any).__outgoingMessages.push(message);
            },
            addEventListener: (type: string, listener: Function) => {
              console.log(`[MockAutoCAD] addEventListener: ${type}`);
              if (!listeners.has(type)) listeners.set(type, []);
              listeners.get(type)?.push(listener);
            },
            removeEventListener: (type: string, listener: Function) => {
              console.log(`[MockAutoCAD] removeEventListener: ${type}`);
              const list = listeners.get(type) || [];
              const index = list.indexOf(listener);
              if (index > -1) list.splice(index, 1);
            },
            // Helper to trigger events from "Host"
            __triggerEvent: (event: any) => {
              console.log(`[MockAutoCAD] __triggerEvent: ${event?.type}`, event);
              const list = listeners.get('message') || [];
              console.log(`[MockAutoCAD] Found ${list.length} message listeners`);
              list.forEach((l) => {
                try {
                  l(event);
                } catch (err) {
                  console.error('[MockAutoCAD] Listener Error:', err);
                }
              });
            },
          },
        };
      });

      await use();
    },
    { auto: true },
  ], // Auto-start for all tests using this custom test

  // Helper to simulate C# -> JS messages
  sendToWebView: async ({ page }, use) => {
    await use(async (action: string, data: any = {}) => {
      await page.evaluate(
        ({ action, data }) => {
          const event = new MessageEvent('message', {
            data: JSON.stringify({ action, data }),
          });
          (window as any).chrome.webview.__triggerEvent(event);
        },
        { action, data }
      );
    });
  },

  // Helper to verify JS -> C# messages
  getLastMessage: async ({ page }, use) => {
    await use(async () => {
      return await page.evaluate(() => {
        const msgs = (window as any).__outgoingMessages;
        return msgs.length > 0 ? msgs[msgs.length - 1] : null;
      });
    });
  },

  clearMessages: async ({ page }, use) => {
    await use(async () => {
      await page.evaluate(() => {
        (window as any).__outgoingMessages = [];
      });
    });
  },

  // Helper to intercept API calls
  mockBackend: [
    async ({ page }, use) => {
      // Mock Health Check
      await page.route('**/api/v1/health', async (route) => {
        await route.fulfill({ status: 200, body: JSON.stringify({ status: 'ok' }) });
      });

      // Mock Auth Check
      await page.route('**/api/v1/auth/check', async (route) => {
        await route.fulfill({ status: 200, body: JSON.stringify({ authenticated: true }) });
      });

      await use();
    },
    { auto: true },
  ],
});

export { expect } from '@playwright/test';
