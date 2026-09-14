/* Function-nav rail — gated stage navigation (progressive enhancement).
 *
 * Reads data-fnav-requires (comma-separated form field names) off the
 * forward button rendered by components/fnav.html. While any required
 * field is empty the action is visibly locked and the gate note says what
 * unlocks it. When all required fields are satisfied the action unlocks.
 *
 * Without JS the button submits normally — the gate is an enhancement,
 * never a dead end. Server-side validation remains authoritative.
 */
(function () {
  "use strict";

  function init() {
    var go = document.querySelector(".fnav [data-fnav-requires]");
    if (!go) return;

    var formId = go.getAttribute("form");
    var form = formId ? document.getElementById(formId) : go.form;
    if (!form) return;

    var gate = document.querySelector(".fnav .fnav__gate");
    var required = (go.getAttribute("data-fnav-requires") || "")
      .split(",")
      .map(function (s) { return s.trim(); })
      .filter(Boolean);

    function fieldValue(name) {
      var el = form.elements[name];
      if (!el) return "";
      // RadioNodeList / checkbox handling: a checked box counts as filled.
      if (el instanceof RadioNodeList) return el.value || "";
      if (el.type === "checkbox") return el.checked ? el.value || "on" : "";
      return (el.value || "").trim();
    }

    function fieldLabel(name) {
      var el = form.elements[name];
      var node = el instanceof RadioNodeList ? el[0] : el;
      if (node && node.id) {
        var label = form.querySelector('label[for="' + node.id + '"]');
        if (label) return label.textContent.replace(/[*]/g, "").trim();
      }
      return name.replace(/_/g, " ");
    }

    function missing() {
      return required.filter(function (name) { return !fieldValue(name); });
    }

    function update() {
      var miss = missing();
      var locked = miss.length > 0;
      go.classList.toggle("fnav__btn--locked", locked);
      go.disabled = locked;
      if (locked) {
        go.setAttribute("aria-disabled", "true");
        if (gate) gate.textContent = "Needs " + miss.map(fieldLabel).join(", ") + " first";
      } else {
        go.removeAttribute("aria-disabled");
        if (gate) gate.textContent = "";
      }
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("reset", function () {
      setTimeout(update, 0);
    });
    update();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
