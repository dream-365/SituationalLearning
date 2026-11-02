const VERSION = "v1";
const SHELL_CACHE = `situlearn-shell-${VERSION}`;
const RUNTIME_CACHE = `situlearn-runtime-${VERSION}`;
const SHELL = [
  "/offline",
  "/static/styles.css",
  "/static/player.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];
const MAX_RUNTIME_ENTRIES = 200;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== SHELL_CACHE && key !== RUNTIME_CACHE)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

async function trimRuntimeCache(cache) {
  const keys = await cache.keys();
  if (keys.length <= MAX_RUNTIME_ENTRIES) return;
  await Promise.all(
    keys
      .slice(0, keys.length - MAX_RUNTIME_ENTRIES)
      .map((key) => cache.delete(key))
  );
}

async function cacheResponse(request, response, cacheName) {
  if (!response || !response.ok) return response;
  const cache = await caches.open(cacheName);
  await cache.put(request, response.clone());
  if (cacheName === RUNTIME_CACHE) await trimRuntimeCache(cache);
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => cacheResponse(request, response, SHELL_CACHE))
        .catch(async () => {
          const cached = await caches.match(request);
          return cached || (await caches.match("/offline"));
        })
    );
    return;
  }

  if (url.pathname.startsWith("/r/") || url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) =>
          cacheResponse(request, response, RUNTIME_CACHE)
        );
      })
    );
  }
});
