const CACHE_NAME = 'medley';
const PRECACHEABLES = [
    '/redirect',
    '/startpage/',
    '/favicon.ico'
];

self.addEventListener('message', (event) => {
    if (event.data.command === 'delete') {
        console.info(`Removing ${event.data.key} from the cache`);
        const removal = caches.open(CACHE_NAME)
              .then(cache => cache.delete(event.data.key))
              .catch(err => console.error(err));

        event.waitUntil(removal);
    }
});

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

    // Don't cache alternate views.
    if (req.url.match(/action=/)) {
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

    const fetchToCache = caches.open(CACHE_NAME).then(cache => {
        cache.delete(req, {ignoreSearch: true});
        return cache;
    }).then(cache => {
        return cache.add(req);
    }).catch(err => console.error(err));


    event.waitUntil(fetchToCache);
});
