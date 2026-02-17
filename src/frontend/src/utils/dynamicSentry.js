/**
 * Lazy-load Sentry to keep the initial bundle small.
 */
export async function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;

  if (dsn) {
    try {
      // Dynamic import to keep Sentry out of the critical path
      const Sentry = await import('@sentry/react');

      Sentry.init({
        dsn,
        environment: import.meta.env.MODE,
        release: 'sisrua-frontend@0.8.0',
        integrations: [
          Sentry.browserTracingIntegration(),
          Sentry.replayIntegration({
            maskAllText: false,
            blockAllMedia: false,
          }),
        ],
        tracesSampleRate: 0.1,
        replaysSessionSampleRate: 0.1,
        replaysOnErrorSampleRate: 1.0,
      });
      console.log('[Sentry] Initialized dynamically');
      return Sentry;
    } catch (error) {
      console.error('[Sentry] Failed to initialize:', error);
    }
  } else {
    // Return a dummy object if DSN is missing to avoid breaks
    return null;
  }
}
