const CACHE_NAME = "packsense-shell-v1";

const APP_SHELL = [
    "/",
    "/static/manifest.json"
];

self.addEventListener("install", function (event) {

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function (cache) {
                return cache.addAll(APP_SHELL);
            })
    );

    self.skipWaiting();
});


self.addEventListener("activate", function (event) {

    event.waitUntil(
        caches.keys().then(function (cacheNames) {

            return Promise.all(
                cacheNames
                    .filter(function (name) {
                        return name !== CACHE_NAME;
                    })
                    .map(function (name) {
                        return caches.delete(name);
                    })
            );

        })
    );

    self.clients.claim();
});


self.addEventListener("fetch", function (event) {

    const request = event.request;

    /*
     * NEVER cache API requests.
     *
     * This is important because your AI,
     * database, login, history and other
     * Flask APIs must continue working
     * normally.
     */

    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
        return;
    }


    event.respondWith(

        fetch(request)

            .then(function (response) {

                const responseCopy = response.clone();

                caches.open(CACHE_NAME)
                    .then(function (cache) {
                        cache.put(request, responseCopy);
                    });

                return response;
            })

            .catch(function () {

                return caches.match(request)
                    .then(function (cachedResponse) {

                        if (cachedResponse) {
                            return cachedResponse;
                        }

                        return caches.match("/");
                    });

            })
    );
});