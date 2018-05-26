const CACHE_NAME = 'startpage';

self.addEventListener('fetch', (event) => {
    // Only consider GET requests.
    if (event.request.method !== 'GET') {
        return;
    }

    // Don't cache alternate views.
    if (event.request.url.match(/action=/)) {
        return;
    }

    event.respondWith(cacheCheck(event.request));
});

/**
 * See if a resource exists in the cache.
 *
 * If it doesn't, try to get it from the network.
 */
function cacheCheck(request) {
    return caches.open(CACHE_NAME)
        .then(cache => cache.match(request))
        .then(match => match || fetchAndCache(request));
}

/**
 * Fetch a resource from the network and cache it.
 */
function fetchAndCache(request) {
    return fetch(request).then(response => {
        return caches.open(CACHE_NAME).then(cache => {
            cache.put(request, response.clone()).then(() => {
                return response;
            });
        });
    });
}
