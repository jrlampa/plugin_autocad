/**
 * sw.js — Service Worker sisRUA (Fase 4: App Campo Offline)
 *
 * Estratégia:
 *   - Cache-First para assets estáticos (js, css, fonts, svg)
 *   - Network-First com fallback para rotas de API
 *   - Stale-While-Revalidate para tiles de mapa (OpenStreetMap)
 *
 * Conformidade: PWA Manifest + Offline-First conforme Roadmap Fase 4.
 * Custo zero: sem dependência de serviços pagos.
 */

const CACHE_VERSION = 'sisrua-v1';
const STATIC_ASSETS = ['/', '/index.html', '/manifest.json', '/vite.svg'];

const TILE_CACHE = 'sisrua-tiles-v1';
const API_CACHE = 'sisrua-api-v1';

// ─────────────────────────────────────────────
// Install: pré-cache de assets críticos
// ─────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Em dev, nem todos os assets existem — ignora silenciosamente
      });
    })
  );
  self.skipWaiting();
});

// ─────────────────────────────────────────────
// Activate: limpa caches antigos
// ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE_VERSION && k !== TILE_CACHE && k !== API_CACHE)
            .map((k) => caches.delete(k))
        )
      )
  );
  self.clients.claim();
});

// ─────────────────────────────────────────────
// Fetch: roteamento de estratégias de cache
// ─────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignora requisições não-GET e Chrome extensions — passa para o browser
  if (request.method !== 'GET' || url.protocol === 'chrome-extension:') {
    return;
  }

  // Tiles OSM → Stale-While-Revalidate
  const OSM_TILE_HOSTS = [
    'tile.openstreetmap.org',
    'a.tile.openstreetmap.org',
    'b.tile.openstreetmap.org',
    'c.tile.openstreetmap.org',
  ];
  if (OSM_TILE_HOSTS.includes(url.hostname)) {
    event.respondWith(staleWhileRevalidate(request, TILE_CACHE));
    return;
  }

  // API do backend → Network-First (dados dinâmicos)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Assets estáticos e navegação → Cache-First
  event.respondWith(cacheFirst(request, CACHE_VERSION));
});

// ─────────────────────────────────────────────
// Estratégias de cache
// ─────────────────────────────────────────────

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Sem conexão. Recurso indisponível offline.', {
      status: 503,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return (
      cached ||
      new Response(JSON.stringify({ error: 'offline', message: 'Backend indisponível.' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  return cached || fetchPromise;
}
