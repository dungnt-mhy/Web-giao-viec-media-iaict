/* Giao Việc IAICT — service worker: cache the app shell only.
   API calls are never cached (they carry live, permission-checked
   business data). GĐ3 adds Web Push display + click-through. */
const CACHE = "giao-viec-iaict-v3";
const SHELL = [
  "/", "/index.html", "/app.js", "/styles.css",
  "/manifest.webmanifest", "/icon.svg", "/icon-192.png", "/icon-512.png",
];

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
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match("/")))
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
