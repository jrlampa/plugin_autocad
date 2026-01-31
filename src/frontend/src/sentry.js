import * as Sentry from '@sentry/react';

/**
 * Initialize Sentry for error monitoring.
 * Set VITE_SENTRY_DSN environment variable to enable.
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;

  if (dsn) {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
      release: 'sisrua-frontend@0.5.0',
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],
      tracesSampleRate: 0.1, // 10% of transactions
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0, // Always capture replays on error
    });
    console.log('[Sentry] Initialized');
  } else {
    console.log('[Sentry] Disabled (no DSN configured)');
  }
}

export { Sentry };
