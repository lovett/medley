const CACHE_NAME = 'startpage';

self.addEventListener('activate', (event) => {
    console.log('activated!');
});

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

    // Always refetch non-hashed assets.
    //
    // This ensures the cached copy stays current with edits made by
    // other clients, but means that the new version won't be visible
    // until the next page load.
    if (event.request.url.indexOf('?') === -1) {
        fetchAndCache(event.request);
    }
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
 *
 * Fetch errors while offline are suppressed to reduce console noise.
 */
function fetchAndCache(request) {
    return fetch(request).then(response => {
        return caches.open(CACHE_NAME).then(cache => {
            return cache.put(request, response.clone()).then(() => {
                return response;
            });
        });
    }).catch(error => {
        if (navigator.onLine === true) {
            console.error(error);
        }
    });
}
