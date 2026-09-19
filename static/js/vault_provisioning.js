/* Post-FINALE vault provisioning driver.
 * Runs on role homes only — never during onboarding. Chunked: one
 * provisioning step per request, resumable across visits. Non-blocking:
 * the home stays usable while this works; failure narrates calmly and
 * offers a retry instead of alarming.
 */
(function () {
  "use strict";

  var STATUS_URL = "/api/vault/provision/status";
  var RUN_URL = "/api/vault/provision/run/";

  var STEP_NARRATION = {
    folders: "Semptify is preparing your folders…",
    vault_db: "Semptify is setting up your workspace records…",
    configs: "Semptify is finishing your workspace setup…",
  };

  function el(id) {
    return document.getElementById(id);
  }

  function narrate(text) {
    var t = el("prov-status-text");
    if (t) t.textContent = text;
  }

  function showRetry(show) {
    var n = el("prov-retry-note");
    if (n) n.hidden = !show;
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
    narrate(STEP_NARRATION[step] || "Semptify is setting up your workspace…");
    var r = await fetch(RUN_URL + step, {
      method: "POST",
      credentials: "same-origin",
    });
    if (!r.ok) return { success: false };
    return r.json();
  }

  async function drive() {
    showRetry(false);
    var status;
    try {
      status = await fetchStatus();
    } catch (e) {
      return; // network hiccup — try again next visit
    }
    if (!status || !status.applicable || !status.next_step) {
      hide();
      return;
    }
    // Walk runnable steps in order; pending (not-yet-built) steps never
    // appear in next_step, so the narrative always describes real work.
    // Bounded: never loop more steps than exist plus one re-check.
    var failed = false;
    var guard = 4;
    while (status.next_step && guard-- > 0) {
      var result;
      try {
        result = await runStep(status.next_step);
      } catch (e) {
        result = null;
      }
      if (!result || result.success === false) {
        failed = true;
        break;
      }
      try {
        status = await fetchStatus();
      } catch (e) {
        status = null;
        failed = true;
        break;
      }
      if (!status) {
        failed = true;
        break;
      }
    }
    if (failed || (status && status.next_step)) {
      narrate("Semptify is still setting up your workspace.");
      showRetry(true);
      return;
    }
    narrate("Your workspace is ready.");
    setTimeout(hide, 2500);
  }

  var retryBtn = el("prov-retry-btn");
  if (retryBtn) retryBtn.addEventListener("click", drive);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", drive);
  } else {
    drive();
  }
})();
