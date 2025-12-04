/**
 * Semptify Service Worker
 * Version: 5.0.0
 * 
 * Provides:
 * - Offline support
 * - Asset caching
 * - Background sync
 * - Push notifications
 */

const CACHE_NAME = 'semptify-v5';
const STATIC_CACHE = 'semptify-static-v5';
const DYNAMIC_CACHE = 'semptify-dynamic-v5';

// Core assets to cache immediately
const STATIC_ASSETS = [
  '/static/css/design-system.css',
  '/static/css/layouts.css',
  '/static/css/accessibility.css',
  '/static/js/modules/api.js',
  '/static/js/modules/websocket.js',
  '/static/js/modules/ui.js',
  '/static/js/modules/state.js',
  '/static/js/modules/a11y.js',
  '/static/js/modules/performance.js',
  '/static/js/app.main.js',
  '/static/dashboard-v2.html',
  '/static/documents-v2.html',
  '/static/calendar-v2.html',
  '/static/timeline-v2.html',
  '/static/settings-v2.html'
];

// API routes that should always go to network
const NETWORK_ONLY = [
  '/api/auth',
  '/api/documents/upload',
  '/api/sync'
];

// API routes that can be cached
const CACHEABLE_API = [
  '/api/documents',
  '/api/calendar',
  '/api/timeline',
  '/api/settings'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // Network-only requests
  if (NETWORK_ONLY.some(route => url.pathname.startsWith(route))) {
    event.respondWith(fetch(request));
    return;
  }

  // API requests - network first, fall back to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets - cache first, fall back to network
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML pages - stale while revalidate
  if (request.headers.get('Accept')?.includes('text/html')) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Default - network first
  event.respondWith(networkFirst(request));
});

/**
 * Cache-first strategy
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] Cache-first fetch failed:', error);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network-first strategy
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok && isCacheableRequest(request)) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache');
    const cached = await caches.match(request);
    
    if (cached) {
      return cached;
    }
    
    // Return offline fallback for API requests
    if (request.url.includes('/api/')) {
      return new Response(
        JSON.stringify({ error: 'Offline', cached: true }),
        { 
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
    
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Stale-while-revalidate strategy
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cached = await cache.match(request);
  
  const networkPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);
  
  return cached || networkPromise;
}

/**
 * Check if URL is a static asset
 */
function isStaticAsset(pathname) {
  return /\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|ico)$/.test(pathname);
}

/**
 * Check if request should be cached
 */
function isCacheableRequest(request) {
  const url = new URL(request.url);
  return CACHEABLE_API.some(route => url.pathname.startsWith(route));
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-documents') {
    event.waitUntil(syncDocuments());
  }
  
  if (event.tag === 'sync-timeline') {
    event.waitUntil(syncTimeline());
  }
});

/**
 * Sync offline documents
 */
async function syncDocuments() {
  try {
    // Get pending uploads from IndexedDB
    const db = await openDatabase();
    const pendingUploads = await getPendingUploads(db);
    
    for (const upload of pendingUploads) {
      try {
        await fetch('/api/documents/upload', {
          method: 'POST',
          body: upload.data
        });
        await markUploadComplete(db, upload.id);
      } catch (error) {
        console.error('[SW] Failed to sync upload:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Sync documents failed:', error);
  }
}

/**
 * Sync offline timeline events
 */
async function syncTimeline() {
  try {
    // Implementation for syncing timeline events
    console.log('[SW] Syncing timeline events...');
  } catch (error) {
    console.error('[SW] Sync timeline failed:', error);
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  const options = {
    body: 'New notification from Semptify',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  
  if (event.data) {
    try {
      const data = event.data.json();
      options.body = data.body || options.body;
      options.data = data;
    } catch (e) {
      options.body = event.data.text();
    }
  }
  
  event.waitUntil(
    self.registration.showNotification('Semptify', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action);
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/static/dashboard-v2.html')
    );
  }
});

// IndexedDB helpers
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('semptify-offline', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      if (!db.objectStoreNames.contains('pending-uploads')) {
        db.createObjectStore('pending-uploads', { keyPath: 'id', autoIncrement: true });
      }
      
      if (!db.objectStoreNames.contains('pending-events')) {
        db.createObjectStore('pending-events', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function getPendingUploads(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-uploads', 'readonly');
    const store = tx.objectStore('pending-uploads');
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function markUploadComplete(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-uploads', 'readwrite');
    const store = tx.objectStore('pending-uploads');
    const request = store.delete(id);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// Message handler for client communication
self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
  
  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((names) => 
        Promise.all(names.map((name) => caches.delete(name)))
      ).then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});

console.log('[SW] Service worker loaded:', CACHE_NAME);
