// FactureKiller V3 - Service Worker Simplifié
// Cache offline pour Scanner Pro Mobile

const CACHE_NAME = 'facturekiller-v1.3';

// Installation du Service Worker - version simplifiée
self.addEventListener('install', (event) => {
    console.log('🔧 Service Worker installing...');
    // Forcer l'activation immédiate
    self.skipWaiting();
});

// Activation du Service Worker
self.addEventListener('activate', (event) => {
    console.log('✅ Service Worker activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Prendre le contrôle immédiatement
            return self.clients.claim();
        })
    );
});

// Interception des requêtes - version simplifiée
self.addEventListener('fetch', (event) => {
    // Ignorer les requêtes non-GET et les APIs
    if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
        return;
    }
    
    event.respondWith(
        fetch(event.request).catch(() => {
            // En cas d'échec réseau, essayer le cache
            return caches.match(event.request);
        })
    );
});

// Gestion des messages du client
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('📱 FactureKiller Service Worker Loaded'); 