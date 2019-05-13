const CACHE_NAME = 'medley';
const PRECACHEABLES = [
    '/redirect',
    '/favicon.ico'
];

/**
 * Precache selected paths at install time.
 */
self.addEventListener('install', (event) => {
    console.info('Service worker installed');

    const precache = caches.open(CACHE_NAME)
          .then(cache => cache.addAll(PRECACHEABLES))
          .catch(err => console.error(err));

    event.waitUntil(precache);
});

/**
 * Serve requests from the cache.
 */
self.addEventListener('fetch', (event) => {
    const req = event.request;

    // Only consider GET requests.
    if (req.method !== 'GET') {
        return;
    }

    // Try to serve the request from the cache.
    const cacheMatch = caches.open(CACHE_NAME)
          .then(cache => cache.match(req, {ignoreSearch: true}))
          .then(match => match || fetch(req));
    event.respondWith(cacheMatch);

    // Update the cache for next time.
    const isPrecacheable = PRECACHEABLES.some(path => req.url.indexOf(path) > -1);
    if (req.url.indexOf('/static/') === -1 && isPrecacheable === false) {
        console.log(`Skipping cache update for ${req.url}`);
        return;
    }

    const fetchToCache = fetch(req).then(response => {
        if (response.status !== 200) {
            return;
        }

        if (response.headers.get('content-type').startsWith('text/html')) {
            return;
        }

        caches.open(CACHE_NAME).then(cache => {
            return cache.put(req, response.clone())
                .then(() => response);
        });
    });

    event.waitUntil(fetchToCache);
});
