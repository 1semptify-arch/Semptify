/**
 * Narration Strip — ADR-0008 / Build Contract Part 2 live narration.
 *
 * Listens for 'semptify:narration' CustomEvents (dispatched by
 * core/websocket-client.js when a WebSocket payload carries a narration
 * line) and writes the latest line into #narration-strip. The strip is a
 * polite ARIA live region, so assistive tech hears each line as it lands.
 *
 * Design: one calm status line — the current line replaces the previous
 * one (a short trail of recent lines would re-read as history; the strip
 * narrates now). Empty strip hides itself via :empty CSS.
 */
(function () {
  'use strict';

  function getStrip() {
    return document.getElementById('narration-strip');
  }

  function show(detail) {
    var strip = getStrip();
    if (!strip || !detail || !detail.text) return;
    strip.textContent = detail.text;
    strip.classList.remove('narration-strip--fresh');
    // Restart the fade so each new line lands visibly.
    void strip.offsetWidth;
    strip.classList.add('narration-strip--fresh');
  }

  window.addEventListener('semptify:narration', function (e) {
    show(e.detail);
  });
})();
