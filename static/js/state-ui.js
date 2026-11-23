/**
 * state-ui.js — State-driven UI runtime
 * ============================================================================
 * Deterministic mode-map driver for smart toolbars and adaptive navigation.
 *
 * The whole pattern in one sentence: the UI is a pure function of state.
 *
 *   - MODES maps a mode name to the actions/items that exist in that mode.
 *   - Actions never touch the DOM — dispatch() mutates state, then render()
 *     rebuilds the surface from the map. There is no hidden per-button logic.
 *   - The mode key comes from passive signals (what is selected, whether the
 *     form is valid, which stage/role/capability is active) — never from
 *     click history or tracking.
 *
 * Zero dependencies, ES5-safe, ~60 lines. Load with a plain <script> tag.
 * ============================================================================
 */
(function (global) {
  "use strict";

  /**
   * Render a mode's action buttons into a container.
   * Each entry: { id, label, cls?, title?, disabled?(state), hidden?(state) }
   * `label` may be a string or a function of state.
   */
  function renderActions(container, buttons, state, dispatch) {
    container.innerHTML = "";
    (buttons || []).forEach(function (b) {
      if (b.hidden && b.hidden(state)) return;
      var el = document.createElement("button");
      el.type = "button";
      el.className = "btn " + (b.cls || "btn-secondary");
      el.textContent = typeof b.label === "function" ? b.label(state) : b.label;
      if (b.disabled && b.disabled(state)) el.disabled = true;
      if (b.title) el.title = b.title;
      el.addEventListener("click", function () { dispatch(b.id); });
      container.appendChild(el);
    });
  }

  /**
   * Render a nav set into a container (adaptive navigation half).
   * Each entry: { id, label, cls? } — the active item gets .active.
   */
  function renderNav(container, items, activeId, onSelect) {
    container.innerHTML = "";
    (items || []).forEach(function (item) {
      var el = document.createElement("button");
      el.type = "button";
      el.className = "mode-nav-item" + (item.id === activeId ? " active" : "");
      el.textContent = item.label;
      el.addEventListener("click", function () {
        if (onSelect) onSelect(item.id);
      });
      container.appendChild(el);
    });
  }

  /**
   * mount(options) — wire a state machine to the DOM.
   *
   * options:
   *   state    — initial state object (must hold `mode` when `modes` is used)
   *   modes    — { modeName: [button entries] } rendered into `el`
   *   el       — toolbar container (optional when `render` is given)
   *   render   — custom render fn (state, dispatch); replaces el+modes rendering
   *   dispatch — host reducer: fn(actionId, state, render)
   *
   * Returns { state, dispatch, render }.
   */
  function mount(options) {
    var state = options.state || {};

    function render() {
      if (options.render) {
        options.render(state, dispatch);
      } else if (options.el && options.modes) {
        renderActions(options.el, options.modes[state.mode] || [], state, dispatch);
      }
    }

    function dispatch(actionId) {
      if (options.dispatch) options.dispatch(actionId, state, render);
      else render();
    }

    render();
    return { state: state, dispatch: dispatch, render: render };
  }

  global.StateUI = { mount: mount, renderActions: renderActions, renderNav: renderNav };
})(window);
