/* Post-FINALE vault provisioning driver.
 * Runs on role homes only — never during onboarding. Chunked: one
 * provisioning step per request, resumable across visits. Non-blocking:
 * the home stays usable while this works; failure just defers to the
 * next visit.
 */
(function () {
  "use strict";

  var STATUS_URL = "/api/vault/provision/status";
  var RUN_URL = "/api/vault/provision/run/";

  var STEP_LABELS = {
    folders: "Preparing your folders",
    vault_db: "Preparing your workspace records",
    configs: "Finishing your workspace setup",
  };

  function el(id) {
    return document.getElementById(id);
  }

  function setText(text) {
    var t = el("prov-status-text");
    if (t) t.textContent = text;
  }

  function hide() {
    var banner = el("prov-banner");
    if (banner) banner.hidden = true;
  }

  async function fetchStatus() {
    var r = await fetch(STATUS_URL, { credentials: "same-origin" });
    if (!r.ok) return null;
    return r.json();
  }

  async function runStep(step) {
    setText(STEP_LABELS[step] || "Setting up your workspace");
    var r = await fetch(RUN_URL + step, {
      method: "POST",
      credentials: "same-origin",
    });
    if (!r.ok) return { success: false };
    return r.json();
  }

  async function drive() {
    var status;
    try {
      status = await fetchStatus();
    } catch (e) {
      return; // network hiccup — try again next visit
    }
    if (!status || !status.applicable) {
      hide();
      return;
    }
    if (status.provisioned) {
      hide();
      return;
    }
    // Walk todo steps in order. Pending steps (not yet built) don't block.
    while (status.next_step) {
      var result;
      try {
        result = await runStep(status.next_step);
      } catch (e) {
        break;
      }
      if (!result || result.success === false) break;
      try {
        status = await fetchStatus();
      } catch (e) {
        break;
      }
      if (!status) break;
    }
    var fresh;
    try {
      fresh = await fetchStatus();
    } catch (e) {
      fresh = null;
    }
    if (fresh && fresh.provisioned) {
      setText("Your workspace is ready.");
      setTimeout(hide, 2500);
    } else {
      setText("We'll finish setting up next time you're here.");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", drive);
  } else {
    drive();
  }
})();
