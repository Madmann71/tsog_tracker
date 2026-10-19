// Service Worker для автономной работы и установки PWA Мастерской ТСОГ (v2 с надежным кэшированием QR и CDN)
const CACHE_NAME = 'tsog-cache-v3';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js',
  'https://cdn.tailwindcss.com/3.4.17',
  'https://unpkg.com/lucide@0.469.0/dist/umd/lucide.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Кэшируем локальные файлы обязательно, а CDN-скрипты по возможности
      return Promise.allSettled(
        ASSETS_TO_CACHE.map((url) => cache.add(url).catch((err) => console.warn('Cache add warn:', url, err)))
      );
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Network-First стратегия с надежным фолбэком в кэш для статики и офлайн-режима
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Игнорируем внешние запросы к API баз данных (GitHub Gist API или локальный сервер), чтобы данные всегда были живыми
  if (url.origin.includes('api.github.com') || url.pathname.startsWith('/api/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Кэшируем успешные ответы (включая CORS и opaque для CDN библиотек)
        if (response && (response.status === 200 || response.type === 'opaque')) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // При отсутствии сети берем из кэша
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('./index.html');
          }
        });
      })
  );
});
