// Service worker for the caregiver app: keeps the report pages and their data available
// offline. Reports themselves wait in IndexedDB (see src/lib/offline/outbox.ts).
const CACHE = "irerero-v1";
const SHELL = [
  "/caregiver",
  "/caregiver/report",
  "/caregiver/sms",
  "/manifest.webmanifest",
  "/icon.svg",
];
const CACHED_API = [
  /^\/api\/session$/,
  /^\/api\/calendar$/,
  /^\/api\/centres\/[\w-]+$/,
  /^\/api\/sms\/format$/,
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request, { ignoreSearch: request.mode === "navigate" });
    if (cached) return cached;
    throw new Error("offline and not cached");
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/__nextjs_font") ||
    url.pathname.endsWith(".woff2")
  ) {
    event.respondWith(cacheFirst(request));
  } else if (request.mode === "navigate" && url.pathname.startsWith("/caregiver")) {
    event.respondWith(networkFirst(request));
  } else if (CACHED_API.some((pattern) => pattern.test(url.pathname))) {
    event.respondWith(networkFirst(request));
  }
});
