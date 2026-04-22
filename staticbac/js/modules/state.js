/**
 * ============================================================================
 * SEMPTIFY STATE MANAGER
 * ============================================================================
 * 
 * Centralized application state management with:
 * - Observable state changes
 * - Persistence to localStorage
 * - Computed values
 * - State history (undo/redo)
 * - DevTools integration
 */

// ============================================================================
// STATE STORE
// ============================================================================

class Store {
  constructor(initialState = {}, options = {}) {
    this._state = { ...initialState };
    this._subscribers = new Map();
    this._computedCache = new Map();
    this._history = [];
    this._historyIndex = -1;
    this._maxHistory = options.maxHistory || 50;
    this._persistKey = options.persistKey || null;
    this._debounceTimeout = null;

    // Load persisted state
    if (this._persistKey) {
      this._loadPersistedState();
    }

    // DevTools integration
    if (typeof window !== 'undefined' && window.__SEMPTIFY_DEVTOOLS__) {
      this._initDevTools();
    }
  }

  /**
   * Get current state (returns a copy)
   */
  getState() {
    return { ...this._state };
  }

  /**
   * Get a specific value from state
   */
  get(path, defaultValue = undefined) {
    return this._getByPath(this._state, path, defaultValue);
  }

  /**
   * Set state value(s)
   */
  set(pathOrObject, value) {
    const oldState = { ...this._state };

    if (typeof pathOrObject === 'string') {
      this._setByPath(this._state, pathOrObject, value);
    } else if (typeof pathOrObject === 'object') {
      this._state = { ...this._state, ...pathOrObject };
    }

    // Add to history
    this._addToHistory(oldState);

    // Clear computed cache
    this._computedCache.clear();

    // Notify subscribers
    this._notify(pathOrObject, value);

    // Persist
    if (this._persistKey) {
      this._debouncePersist();
    }
  }

  /**
   * Update state using a function
   */
  update(path, updater) {
    const currentValue = this.get(path);
    const newValue = updater(currentValue);
    this.set(path, newValue);
    return newValue;
  }

  /**
   * Subscribe to state changes
   */
  subscribe(pathOrCallback, callback) {
    // Allow subscribing to all changes
    if (typeof pathOrCallback === 'function') {
      callback = pathOrCallback;
      pathOrCallback = '*';
    }

    if (!this._subscribers.has(pathOrCallback)) {
      this._subscribers.set(pathOrCallback, new Set());
    }

    this._subscribers.get(pathOrCallback).add(callback);

    // Return unsubscribe function
    return () => {
      const subs = this._subscribers.get(pathOrCallback);
      if (subs) {
        subs.delete(callback);
      }
    };
  }

  /**
   * Subscribe to a computed value
   */
  computed(name, dependencies, computeFn) {
    // Store computation info
    if (!this._computedCache.has(name)) {
      this._computedCache.set(name, {
        dependencies,
        computeFn,
        value: undefined,
        dirty: true
      });
    }

    // Subscribe to dependencies
    dependencies.forEach(dep => {
      this.subscribe(dep, () => {
        const cached = this._computedCache.get(name);
        if (cached) {
          cached.dirty = true;
        }
      });
    });

    // Return getter
    return () => {
      const cached = this._computedCache.get(name);
      if (cached.dirty) {
        cached.value = computeFn(this._state);
        cached.dirty = false;
      }
      return cached.value;
    };
  }

  /**
   * Undo last state change
   */
  undo() {
    if (this._historyIndex > 0) {
      this._historyIndex--;
      this._state = { ...this._history[this._historyIndex] };
      this._notify('*', this._state);
      return true;
    }
    return false;
  }

  /**
   * Redo state change
   */
  redo() {
    if (this._historyIndex < this._history.length - 1) {
      this._historyIndex++;
      this._state = { ...this._history[this._historyIndex] };
      this._notify('*', this._state);
      return true;
    }
    return false;
  }

  /**
   * Check if undo is available
   */
  canUndo() {
    return this._historyIndex > 0;
  }

  /**
   * Check if redo is available
   */
  canRedo() {
    return this._historyIndex < this._history.length - 1;
  }

  /**
   * Reset to initial state
   */
  reset(initialState = {}) {
    this._state = { ...initialState };
    this._history = [];
    this._historyIndex = -1;
    this._computedCache.clear();
    this._notify('*', this._state);
  }

  // Private methods

  _getByPath(obj, path, defaultValue) {
    const keys = path.split('.');
    let result = obj;

    for (const key of keys) {
      if (result === null || result === undefined) {
        return defaultValue;
      }
      result = result[key];
    }

    return result !== undefined ? result : defaultValue;
  }

  _setByPath(obj, path, value) {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    current[keys[keys.length - 1]] = value;
  }

  _addToHistory(state) {
    // Remove any future states if we're not at the end
    if (this._historyIndex < this._history.length - 1) {
      this._history = this._history.slice(0, this._historyIndex + 1);
    }

    // Add state to history
    this._history.push(state);
    this._historyIndex = this._history.length - 1;

    // Limit history size
    if (this._history.length > this._maxHistory) {
      this._history.shift();
      this._historyIndex--;
    }
  }

  _notify(path, value) {
    // Notify path-specific subscribers
    if (typeof path === 'string') {
      const subs = this._subscribers.get(path);
      if (subs) {
        subs.forEach(callback => callback(value, this._state));
      }
    }

    // Notify wildcard subscribers
    const wildcardSubs = this._subscribers.get('*');
    if (wildcardSubs) {
      wildcardSubs.forEach(callback => callback(this._state));
    }
  }

  _loadPersistedState() {
    try {
      const stored = localStorage.getItem(this._persistKey);
      if (stored) {
        this._state = { ...this._state, ...JSON.parse(stored) };
      }
    } catch (e) {
      console.warn('Failed to load persisted state:', e);
    }
  }

  _debouncePersist() {
    if (this._debounceTimeout) {
      clearTimeout(this._debounceTimeout);
    }

    this._debounceTimeout = setTimeout(() => {
      this._persist();
    }, 100);
  }

  _persist() {
    try {
      localStorage.setItem(this._persistKey, JSON.stringify(this._state));
    } catch (e) {
      console.warn('Failed to persist state:', e);
    }
  }

  _initDevTools() {
    // Simple DevTools integration
    window.__SEMPTIFY_DEVTOOLS__.register(this);
  }
}

// ============================================================================
// APPLICATION STATE
// ============================================================================

// Default application state
const defaultAppState = {
  // User
  user: null,
  isAuthenticated: false,

  // UI
  theme: 'light',
  sidebarCollapsed: false,
  currentPage: null,

  // Documents
  documents: [],
  selectedDocument: null,
  documentsLoading: false,

  // Timeline
  timelineEvents: [],
  timelineLoading: false,

  // Notifications
  notifications: [],
  unreadCount: 0,

  // Sync status
  syncStatus: {
    connected: false,
    lastSync: null,
    provider: null
  },

  // Connection status
  online: navigator.onLine,
  wsConnected: false
};

// Create app store
const appStore = new Store(defaultAppState, {
  persistKey: 'semptify_app_state',
  maxHistory: 30
});

// ============================================================================
// STATE ACTIONS (Pure functions that modify state)
// ============================================================================

const actions = {
  // User actions
  setUser(user) {
    appStore.set({
      user,
      isAuthenticated: !!user
    });
  },

  logout() {
    appStore.set({
      user: null,
      isAuthenticated: false
    });
  },

  // Theme actions
  setTheme(theme) {
    appStore.set('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  },

  toggleTheme() {
    const current = appStore.get('theme');
    actions.setTheme(current === 'dark' ? 'light' : 'dark');
  },

  // Sidebar actions
  toggleSidebar() {
    appStore.update('sidebarCollapsed', collapsed => !collapsed);
  },

  // Documents actions
  setDocuments(documents) {
    appStore.set('documents', documents);
  },

  addDocument(document) {
    appStore.update('documents', docs => [...docs, document]);
  },

  removeDocument(documentId) {
    appStore.update('documents', docs => docs.filter(d => d.id !== documentId));
  },

  selectDocument(document) {
    appStore.set('selectedDocument', document);
  },

  // Timeline actions
  setTimelineEvents(events) {
    appStore.set('timelineEvents', events);
  },

  addTimelineEvent(event) {
    appStore.update('timelineEvents', events => [...events, event].sort((a, b) => new Date(b.date) - new Date(a.date)));
  },

  // Notifications
  addNotification(notification) {
    const id = notification.id || Date.now();
    appStore.update('notifications', notifs => [{
      ...notification,
      id,
      timestamp: new Date().toISOString(),
      read: false
    }, ...notifs]);
    appStore.update('unreadCount', count => count + 1);
    return id;
  },

  markNotificationRead(id) {
    appStore.update('notifications', notifs => 
      notifs.map(n => n.id === id ? { ...n, read: true } : n)
    );
    appStore.update('unreadCount', count => Math.max(0, count - 1));
  },

  clearNotifications() {
    appStore.set({
      notifications: [],
      unreadCount: 0
    });
  },

  // Sync status
  setSyncStatus(status) {
    appStore.set('syncStatus', { ...appStore.get('syncStatus'), ...status });
  },

  // Connection status
  setOnlineStatus(online) {
    appStore.set('online', online);
  },

  setWebSocketConnected(connected) {
    appStore.set('wsConnected', connected);
  }
};

// ============================================================================
// SELECTORS (Computed values)
// ============================================================================

const selectors = {
  // Get sorted documents
  getSortedDocuments: appStore.computed(
    'sortedDocuments',
    ['documents'],
    (state) => [...state.documents].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  ),

  // Get unread notifications
  getUnreadNotifications: appStore.computed(
    'unreadNotifications',
    ['notifications'],
    (state) => state.notifications.filter(n => !n.read)
  ),

  // Check if fully connected
  isFullyConnected: appStore.computed(
    'fullyConnected',
    ['online', 'wsConnected', 'syncStatus'],
    (state) => state.online && state.wsConnected && state.syncStatus.connected
  )
};

// ============================================================================
// ONLINE/OFFLINE DETECTION
// ============================================================================

window.addEventListener('online', () => actions.setOnlineStatus(true));
window.addEventListener('offline', () => actions.setOnlineStatus(false));

// ============================================================================
// THEME INITIALIZATION
// ============================================================================

// Apply persisted theme on load
const savedTheme = appStore.get('theme');
if (savedTheme) {
  document.documentElement.setAttribute('data-theme', savedTheme);
}

// Listen for system theme changes
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!appStore.get('theme')) {
      actions.setTheme(e.matches ? 'dark' : 'light');
    }
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

// Global exports
window.Store = Store;
window.appStore = appStore;
window.actions = actions;
window.selectors = selectors;

// ES Module exports
export {
  Store,
  appStore,
  actions,
  selectors
};
