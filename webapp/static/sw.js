/* Giao Việc IAICT — service worker.
   API calls are never cached (they carry live, permission-checked
   business data). GĐ3 adds Web Push display + click-through.
   TD-0009 (v4): the app shell (index.html, app.js, styles.css) is
   NETWORK-FIRST so a new deploy reaches installed PWAs immediately —
   a cache-first shell once kept a phone stuck on the previous UI.
   Other static assets (icons, manifest) stay cache-first.
   skipWaiting + clients.claim make a new worker take over at once;
   app.js reloads the page once when control changes hands. */
const CACHE = "giao-viec-iaict-v9";
/* index.html references the shell assets with a ?v=<release> query:
   Cloudflare's edge once kept serving a stale /app.js under its
   plain URL (default TTL) even after the origin had the new file. */
const SHELL = [
  "/", "/index.html", "/app.js?v=0.5.1", "/styles.css?v=0.5.1",
  "/manifest.webmanifest", "/icon.svg", "/icon-192.png", "/icon-512.png",
];
const SHELL_PATHS = new Set(["/", "/index.html", "/app.js", "/styles.css"]);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") {
    return; // network only for API and writes
  }
  const cacheCopy = (response) => {
    if (response && response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(event.request, copy));
    }
    return response;
  };
  if (SHELL_PATHS.has(url.pathname) || event.request.mode === "navigate") {
    // App shell: network-first, cache only as the offline fallback.
    event.respondWith(
      fetch(event.request)
        .then(cacheCopy)
        .catch(() => caches.match(event.request).then((hit) => hit || caches.match("/")))
    );
    return;
  }
  // Other static assets: cache-first, refreshed from network on a miss.
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request).then(cacheCopy))
  );
});

/* ------------------------- Web Push (GĐ3) ------------------------- */

self.addEventListener("push", (event) => {
  let data = { title: "Giao Việc IAICT", body: "", url: "/" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch { /* keep defaults; some services send text-only payloads */ }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  const url = new URL(target, self.location.origin).href;
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({
      type: "window", includeUncontrolled: true,
    });
    for (const client of windows) {
      if (client.url.startsWith(self.location.origin) && "focus" in client) {
        await client.focus();
        if ("navigate" in client) {
          try { await client.navigate(url); } catch { /* already there */ }
        }
        return;
      }
    }
    await self.clients.openWindow(url);
  })());
});
