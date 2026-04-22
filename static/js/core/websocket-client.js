/**
 * WebSocket Client - Real-time Notifications
 * Connects to /ws/events for live updates
 */

(function() {
  'use strict';

  const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/events`;
  const RECONNECT_DELAY = 3000;
  const MAX_RECONNECT_ATTEMPTS = 5;

  let ws = null;
  let reconnectAttempts = 0;
  let reconnectTimer = null;
  let isManualClose = false;

  // Event handlers registry
  const handlers = new Map();

  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return;

    try {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        reconnectAttempts = 0;
        emit('connected', { timestamp: new Date().toISOString() });
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log('[WebSocket] Message:', msg.type);
          handleMessage(msg);
        } catch (e) {
          console.error('[WebSocket] Parse error:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Closed', event.code);
        emit('disconnected', { code: event.code, wasClean: event.wasClean });
        if (!isManualClose) scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        emit('error', { error: 'WebSocket error occurred' });
      };

    } catch (e) {
      console.error('[WebSocket] Connection failed:', e);
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.warn('[WebSocket] Max reconnection attempts reached');
      emit('max_reconnects_reached', {});
      return;
    }
    reconnectAttempts++;
    console.log(`[WebSocket] Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttempts})`);
    reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
  }

  function disconnect() {
    isManualClose = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws) {
      ws.close(1000, 'Manual disconnect');
      ws = null;
    }
  }

  function handleMessage(msg) {
    // System messages
    if (msg.type === 'connected') {
      console.log('[WebSocket] Server welcome:', msg.message);
      return;
    }

    // Job notifications
    if (msg.type === 'job_status') {
      showNotification('Job Update', msg.data.message || 'Job status changed', msg.data.status);
    }

    // Document upload notifications
    if (msg.type === 'document_upload') {
      showNotification('Document', msg.data.message || 'Document processed', 'success');
    }

    // System alerts
    if (msg.type === 'system_alert') {
      showNotification('System', msg.data.message || 'System alert', msg.data.level || 'info');
    }

    // Emit to registered handlers
    emit(msg.type, msg.data);
  }

  function showNotification(title, message, level = 'info') {
    // Use native notifications if permitted, otherwise console
    if (typeof window.showNotification === 'function') {
      window.showNotification(title, message, level);
    } else {
      console.log(`[Notification] ${title}: ${message} (${level})`);
    }

    // Dispatch custom event for UI components
    window.dispatchEvent(new CustomEvent('semptify:notification', {
      detail: { title, message, level, timestamp: new Date().toISOString() }
    }));
  }

  function on(event, handler) {
    if (!handlers.has(event)) handlers.set(event, []);
    handlers.get(event).push(handler);
  }

  function off(event, handler) {
    if (!handlers.has(event)) return;
    const idx = handlers.get(event).indexOf(handler);
    if (idx > -1) handlers.get(event).splice(idx, 1);
  }

  function emit(event, data) {
    if (!handlers.has(event)) return;
    handlers.get(event).forEach(h => {
      try { h(data); } catch (e) { console.error(e); }
    });
  }

  function send(data) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Not connected, cannot send');
    }
  }

  // Auto-connect when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connect);
  } else {
    connect();
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', disconnect);

  // Expose API
  window.SemptifyWebSocket = {
    connect,
    disconnect,
    send,
    on,
    off,
    isConnected: () => ws?.readyState === WebSocket.OPEN,
    getReconnectAttempts: () => reconnectAttempts
  };

  console.log('[WebSocket] Client loaded, auto-connecting...');
})();
