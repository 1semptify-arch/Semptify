/**
 * ============================================================================
 * SEMPTIFY WEBSOCKET MANAGER
 * ============================================================================
 * 
 * Robust WebSocket manager with:
 * - Automatic reconnection with exponential backoff
 * - Event-based pub/sub system
 * - Connection state management
 * - Heartbeat/ping-pong
 * - Message queuing during disconnection
 * - Multiple channel support
 */

const WS_BASE_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

// Connection states
const ConnectionState = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting',
  FAILED: 'failed'
};

/**
 * WebSocket connection manager
 */
class WebSocketManager {
  constructor(options = {}) {
    this.options = {
      reconnect: true,
      maxReconnectAttempts: 10,
      reconnectDelay: 1000,
      maxReconnectDelay: 30000,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      ...options
    };

    this.connections = new Map();
    this.eventListeners = new Map();
    this.globalListeners = [];
  }

  /**
   * Connect to a WebSocket endpoint
   */
  connect(channel, endpoint, options = {}) {
    // Close existing connection if any
    if (this.connections.has(channel)) {
      this.disconnect(channel);
    }

    const connection = {
      channel,
      endpoint,
      options: { ...this.options, ...options },
      socket: null,
      state: ConnectionState.CONNECTING,
      reconnectAttempts: 0,
      messageQueue: [],
      heartbeatTimer: null,
      reconnectTimer: null,
      listeners: new Map()
    };

    this.connections.set(channel, connection);
    this._createSocket(connection);

    return {
      on: (event, callback) => this.on(channel, event, callback),
      off: (event, callback) => this.off(channel, event, callback),
      send: (data) => this.send(channel, data),
      disconnect: () => this.disconnect(channel),
      getState: () => this.getState(channel)
    };
  }

  /**
   * Create WebSocket connection
   */
  _createSocket(connection) {
    const { channel, endpoint, options } = connection;
    const url = endpoint.startsWith('ws') ? endpoint : `${WS_BASE_URL}${endpoint}`;

    try {
      connection.socket = new WebSocket(url);
      connection.state = ConnectionState.CONNECTING;
      this._emitState(channel);

      connection.socket.onopen = () => {
        connection.state = ConnectionState.CONNECTED;
        connection.reconnectAttempts = 0;
        this._emitState(channel);
        this._emit(channel, 'open', { channel });
        this._startHeartbeat(connection);
        this._flushMessageQueue(connection);
      };

      connection.socket.onclose = (event) => {
        this._stopHeartbeat(connection);
        connection.state = ConnectionState.DISCONNECTED;
        this._emitState(channel);
        this._emit(channel, 'close', { channel, code: event.code, reason: event.reason });

        // Attempt reconnection if enabled
        if (options.reconnect && connection.reconnectAttempts < options.maxReconnectAttempts) {
          this._scheduleReconnect(connection);
        } else if (connection.reconnectAttempts >= options.maxReconnectAttempts) {
          connection.state = ConnectionState.FAILED;
          this._emitState(channel);
          this._emit(channel, 'failed', { channel, attempts: connection.reconnectAttempts });
        }
      };

      connection.socket.onerror = (error) => {
        this._emit(channel, 'error', { channel, error });
      };

      connection.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle pong messages
          if (data.type === 'pong') {
            return;
          }

          // Emit to specific event type listeners
          if (data.type) {
            this._emit(channel, data.type, data);
          }

          // Emit generic message event
          this._emit(channel, 'message', data);

        } catch {
          // Not JSON, emit as raw message
          this._emit(channel, 'message', { raw: event.data });
        }
      };

    } catch (error) {
      connection.state = ConnectionState.FAILED;
      this._emitState(channel);
      this._emit(channel, 'error', { channel, error });
    }
  }

  /**
   * Schedule reconnection with exponential backoff
   */
  _scheduleReconnect(connection) {
    const { channel, options } = connection;
    
    connection.state = ConnectionState.RECONNECTING;
    this._emitState(channel);

    const delay = Math.min(
      options.reconnectDelay * Math.pow(2, connection.reconnectAttempts),
      options.maxReconnectDelay
    );

    connection.reconnectTimer = setTimeout(() => {
      connection.reconnectAttempts++;
      this._emit(channel, 'reconnecting', { 
        channel, 
        attempt: connection.reconnectAttempts,
        maxAttempts: options.maxReconnectAttempts 
      });
      this._createSocket(connection);
    }, delay);
  }

  /**
   * Start heartbeat to keep connection alive
   */
  _startHeartbeat(connection) {
    const { options } = connection;

    if (!options.heartbeatInterval) return;

    connection.heartbeatTimer = setInterval(() => {
      if (connection.socket?.readyState === WebSocket.OPEN) {
        this.send(connection.channel, { type: 'ping' });
      }
    }, options.heartbeatInterval);
  }

  /**
   * Stop heartbeat
   */
  _stopHeartbeat(connection) {
    if (connection.heartbeatTimer) {
      clearInterval(connection.heartbeatTimer);
      connection.heartbeatTimer = null;
    }
  }

  /**
   * Flush queued messages after reconnection
   */
  _flushMessageQueue(connection) {
    while (connection.messageQueue.length > 0) {
      const message = connection.messageQueue.shift();
      this._sendDirect(connection, message);
    }
  }

  /**
   * Send message directly
   */
  _sendDirect(connection, data) {
    if (connection.socket?.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      connection.socket.send(message);
      return true;
    }
    return false;
  }

  /**
   * Send message to a channel
   */
  send(channel, data) {
    const connection = this.connections.get(channel);
    
    if (!connection) {
      console.warn(`WebSocket: No connection for channel "${channel}"`);
      return false;
    }

    // If connected, send immediately
    if (this._sendDirect(connection, data)) {
      return true;
    }

    // Queue message for later
    if (connection.messageQueue.length < connection.options.messageQueueSize) {
      connection.messageQueue.push(data);
      return true;
    }

    console.warn(`WebSocket: Message queue full for channel "${channel}"`);
    return false;
  }

  /**
   * Subscribe to events on a channel
   */
  on(channel, event, callback) {
    const connection = this.connections.get(channel);
    
    if (!connection) {
      console.warn(`WebSocket: No connection for channel "${channel}"`);
      return () => {};
    }

    if (!connection.listeners.has(event)) {
      connection.listeners.set(event, new Set());
    }

    connection.listeners.get(event).add(callback);

    // Return unsubscribe function
    return () => this.off(channel, event, callback);
  }

  /**
   * Unsubscribe from events
   */
  off(channel, event, callback) {
    const connection = this.connections.get(channel);
    
    if (!connection) return;

    const eventListeners = connection.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
    }
  }

  /**
   * Emit event to listeners
   */
  _emit(channel, event, data) {
    const connection = this.connections.get(channel);
    
    if (!connection) return;

    // Emit to channel-specific listeners
    const listeners = connection.listeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`WebSocket: Error in event handler for "${event}"`, error);
        }
      });
    }

    // Emit to global listeners
    this.globalListeners.forEach(callback => {
      try {
        callback(channel, event, data);
      } catch (error) {
        console.error('WebSocket: Error in global handler', error);
      }
    });
  }

  /**
   * Emit state change events
   */
  _emitState(channel) {
    const connection = this.connections.get(channel);
    if (connection) {
      this._emit(channel, 'stateChange', { 
        channel, 
        state: connection.state 
      });
    }
  }

  /**
   * Subscribe to all events across all channels
   */
  onAny(callback) {
    this.globalListeners.push(callback);
    return () => {
      const index = this.globalListeners.indexOf(callback);
      if (index > -1) {
        this.globalListeners.splice(index, 1);
      }
    };
  }

  /**
   * Get connection state
   */
  getState(channel) {
    const connection = this.connections.get(channel);
    return connection?.state || ConnectionState.DISCONNECTED;
  }

  /**
   * Check if connected
   */
  isConnected(channel) {
    return this.getState(channel) === ConnectionState.CONNECTED;
  }

  /**
   * Disconnect from a channel
   */
  disconnect(channel) {
    const connection = this.connections.get(channel);
    
    if (!connection) return;

    // Clear timers
    this._stopHeartbeat(connection);
    if (connection.reconnectTimer) {
      clearTimeout(connection.reconnectTimer);
      connection.reconnectTimer = null;
    }

    // Disable auto-reconnect
    connection.options.reconnect = false;

    // Close socket
    if (connection.socket) {
      connection.socket.close(1000, 'Client disconnect');
      connection.socket = null;
    }

    // Clear listeners
    connection.listeners.clear();
    
    // Remove from connections
    this.connections.delete(channel);
  }

  /**
   * Disconnect all channels
   */
  disconnectAll() {
    for (const channel of this.connections.keys()) {
      this.disconnect(channel);
    }
    this.globalListeners = [];
  }

  /**
   * Get all active channels
   */
  getChannels() {
    return Array.from(this.connections.keys());
  }

  /**
   * Get all connection states
   */
  getConnectionStates() {
    const states = {};
    for (const [channel, connection] of this.connections) {
      states[channel] = connection.state;
    }
    return states;
  }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

const wsManager = new WebSocketManager();

// ============================================================================
// CONVENIENCE FUNCTIONS FOR COMMON CHANNELS
// ============================================================================

/**
 * Connect to the main events channel
 */
function connectEvents(options = {}) {
  return wsManager.connect('events', '/ws/events', {
    heartbeatInterval: 30000,
    ...options
  });
}

/**
 * Connect to the AI/Brain channel
 */
function connectBrain(options = {}) {
  return wsManager.connect('brain', '/api/brain/ws', {
    heartbeatInterval: 60000,
    ...options
  });
}

/**
 * Connect to the sync status channel
 */
function connectSyncStatus(options = {}) {
  return wsManager.connect('sync', '/ws/sync', {
    heartbeatInterval: 30000,
    ...options
  });
}

/**
 * Connect to document processing updates
 */
function connectDocuments(options = {}) {
  return wsManager.connect('documents', '/ws/documents', {
    heartbeatInterval: 30000,
    ...options
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

// Make available globally
window.WebSocketManager = WebSocketManager;
window.wsManager = wsManager;
window.ConnectionState = ConnectionState;
window.connectEvents = connectEvents;
window.connectBrain = connectBrain;
window.connectSyncStatus = connectSyncStatus;
window.connectDocuments = connectDocuments;

// ES Module exports
export {
  WebSocketManager,
  wsManager,
  ConnectionState,
  connectEvents,
  connectBrain,
  connectSyncStatus,
  connectDocuments
};
