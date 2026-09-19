/**
 * Path activity line — live "what Semptify is doing" indicator.
 *
 * Listens for 'semptify:narration' and 'semptify:notification' CustomEvents
 * dispatched by core/websocket-client.js (the shared /ws/events client the
 * shell already loads), plus the client's connected/disconnected signals.
 * The line only moves on real backend events — no fabricated progress.
 *
 * Elements: #path-activity-text (the line), #path-activity-dot (the pulse).
 * Both optional — the driver exits quietly if the path zone isn't present.
 */
(function () {
  'use strict';

  var textEl = null;
  var dotEl = null;
  var liveTimer = null;

  var IDLE_TEXT = 'Semptify is listening — updates appear here as they happen.';
  var PAUSED_TEXT = 'Updates paused — reconnecting quietly in the background.';

  function setText(t) {
    if (textEl) textEl.textContent = t;
  }

  function pulse() {
    if (!dotEl) return;
    dotEl.classList.remove('is-live');
    void dotEl.offsetWidth; // restart the pulse so each event lands visibly
    dotEl.classList.add('is-live');
    clearTimeout(liveTimer);
    liveTimer = setTimeout(function () {
      dotEl.classList.remove('is-live');
    }, 4000);
  }

  function onNarration(e) {
    if (e.detail && e.detail.text) {
      setText(e.detail.text);
      pulse();
    }
  }

  function onNotification(e) {
    var d = e.detail || {};
    var msg = d.title && d.message ? d.title + ' — ' + d.message : (d.message || d.title || '');
    if (msg) {
      setText(msg);
      pulse();
    }
  }

  function init() {
    textEl = document.getElementById('path-activity-text');
    dotEl = document.getElementById('path-activity-dot');
    if (!textEl) return;

    window.addEventListener('semptify:narration', onNarration);
    window.addEventListener('semptify:notification', onNotification);

    if (window.SemptifyWebSocket) {
      window.SemptifyWebSocket.on('disconnected', function () {
        setText(PAUSED_TEXT);
        if (dotEl) dotEl.classList.remove('is-live');
      });
      window.SemptifyWebSocket.on('connected', function () {
        setText(IDLE_TEXT);
      });
      window.SemptifyWebSocket.on('max_reconnects_reached', function () {
        setText('Updates are offline — everything you save is still kept. They will resume next visit.');
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
