/*
 * Vault setup flow — shared first-run component on every role home.
 *
 * Drives the existing /onboarding/api/vault/* endpoints:
 *   GET status → POST init → POST security → POST verify (upload)
 * Server-side vault_checks rows are the resume point — a user can leave
 * mid-setup and continue on any device; on load we pick up where the
 * server says they stopped. Every failure shows a retry, never a dead end.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-vault-setup]");
  if (!root) return;

  var API = "/onboarding/api/vault";
  var VERIFY_RETRIES = 10;
  var VERIFY_DELAY_MS = 4000;

  var stepEls = {};
  root.querySelectorAll("[data-vs-step]").forEach(function (el) {
    stepEls[el.getAttribute("data-vs-step")] = el;
  });
  var uploadBox = root.querySelector("[data-vs-upload]");
  var fileInput = root.querySelector("[data-vs-file]");
  var drop = root.querySelector("[data-vs-drop]");
  var dropLabel = root.querySelector("[data-vs-drop-label]");
  var submitBtn = root.querySelector("[data-vs-submit]");
  var busyText = root.querySelector("[data-vs-busy-text]");
  var errorBox = root.querySelector("[data-vs-error]");
  var errorText = root.querySelector("[data-vs-error-text]");
  var retryBtn = root.querySelector("[data-vs-retry]");

  var pickedFile = null;
  var retryAction = null;

  function setStep(name, text, warn) {
    var row = stepEls[name];
    if (!row) return;
    var state = row.querySelector("[data-vs-state]");
    if (state) {
      state.textContent = text;
      state.classList.toggle("shell-status-value--warn", !!warn);
    }
  }

  function busy(msg) {
    if (busyText) busyText.textContent = msg || "";
  }

  function showError(msg, retry) {
    errorText.textContent = msg;
    errorBox.hidden = false;
    retryAction = retry || null;
  }

  function clearError() {
    errorBox.hidden = true;
    retryAction = null;
  }

  function reconnect() {
    window.location.href =
      "/storage/reconnect?return_to=" + encodeURIComponent(window.location.pathname);
  }

  /* One fetch wrapper: POST by default, 401 → reconnect, redirect action
   * honored. Returns parsed JSON or null when the page navigated away. */
  async function call(path, opts) {
    var res = await fetch(
      API + path,
      Object.assign({ credentials: "include", method: "POST" }, opts || {})
    );
    if (res.status === 401) {
      reconnect();
      return null;
    }
    var data = {};
    try {
      data = await res.json();
    } catch (e) {
      /* non-JSON body — treat as failure handled by caller */
    }
    if (data && data.action === "redirect" && data.redirect_url) {
      window.location.href = data.redirect_url;
      return null;
    }
    return data;
  }

  function finish() {
    setStep("upload", "Done", false);
    busy("Vault verified — opening your home.");
    setTimeout(function () {
      window.location.reload();
    }, 900);
  }

  /* Step 3 — upload + full verification. file may be null on retries:
   * the backend's detect-first path verifies the document already in the
   * vault instead of forcing a duplicate upload. */
  async function doVerify(file, attempt) {
    attempt = attempt || 0;
    clearError();
    setStep("upload", "Working…", false);
    busy(attempt > 0 ? "Verifying your vault — still working…" : "Verifying your vault…");

    var fd = new FormData();
    if (file) fd.append("file", file, file.name);

    var d;
    try {
      d = await call("/verify", { body: fd });
    } catch (e) {
      busy("");
      showError("Could not reach the service — check your connection and try again.", function () {
        doVerify(file, 0);
      });
      return;
    }
    if (!d) return; // navigated to reconnect

    if (d.ok) {
      finish();
      return;
    }
    if (d.verifying && attempt < VERIFY_RETRIES) {
      setTimeout(function () {
        doVerify(null, attempt + 1);
      }, VERIFY_DELAY_MS);
      return;
    }

    busy("");
    var msg = d.error || "Verification did not finish.";
    if (d.failed_check) msg += " (" + d.failed_check + ")";
    setStep("upload", "Needs attention", true);
    showError(msg, function () {
      doVerify(pickedFile, 0);
    });
  }

  /* Steps 1–2 — folders, then token backup + live probe. Automatic; the
   * only user action in the whole flow is the document upload. */
  async function runInstall() {
    clearError();
    setStep("folders", "Working…", false);
    busy("Building your vault folders…");
    try {
      var init = await call("/init");
      if (!init) return;
      if (!init.success) throw new Error(init.error || "Your vault folders could not be created.");
    } catch (e) {
      busy("");
      setStep("folders", "Needs attention", true);
      showError(e.message || "Your vault folders could not be created.", runInstall);
      return;
    }
    setStep("folders", "Done", false);

    setStep("secure", "Working…", false);
    busy("Securing the connection…");
    try {
      var sec = await call("/security");
      if (!sec) return;
      if (!sec.success) throw new Error(sec.error || "The connection could not be secured.");
    } catch (e) {
      busy("");
      setStep("secure", "Needs attention", true);
      showError(e.message || "The connection could not be secured.", runInstall);
      return;
    }
    setStep("secure", "Done", false);
    busy("");
    showUpload();
  }

  function showUpload() {
    uploadBox.hidden = false;
    setStep("upload", pickedFile ? "Ready" : "Waiting", false);
  }

  function showPicked() {
    dropLabel.textContent = pickedFile.name;
    submitBtn.disabled = false;
    setStep("upload", "Ready", false);
  }

  fileInput.addEventListener("change", function () {
    if (fileInput.files.length) {
      pickedFile = fileInput.files[0];
      showPicked();
    }
  });
  drop.addEventListener("dragover", function (e) {
    e.preventDefault();
  });
  drop.addEventListener("drop", function (e) {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      pickedFile = e.dataTransfer.files[0];
      showPicked();
    }
  });
  submitBtn.addEventListener("click", function () {
    if (pickedFile) doVerify(pickedFile, 0);
  });
  retryBtn.addEventListener("click", function () {
    if (retryAction) retryAction();
  });

  /* Resume point: the server's vault_checks state decides where we start,
   * not anything in the browser — works across devices and sessions. */
  async function boot() {
    busy("Checking your vault…");
    var s;
    try {
      s = await call("/status", { method: "GET" });
    } catch (e) {
      busy("");
      showError("Could not check your vault status — check your connection and try again.", boot);
      return;
    }
    if (!s) return;
    busy("");

    if (s.document_uploaded) {
      // FINALE already set — reload so the home renders in normal mode.
      window.location.reload();
      return;
    }

    if (s.vault_initialized) {
      setStep("folders", "Done", false);
      setStep("secure", "Done", false);
      showUpload();
      if (s.document_count > 0) {
        // A document is already in the vault from a prior attempt —
        // verify it directly instead of asking for another upload.
        doVerify(null, 0);
      }
      return;
    }

    if (s.vault_status === "test_pending" || s.vault_status === "failed") {
      // Folders exist server-side; re-run install (idempotent) to heal.
      runInstall();
      return;
    }

    runInstall();
  }

  boot();
})();
