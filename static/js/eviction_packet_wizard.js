/*
 * Eviction packet wizard — drives the guided defense-packet flow on
 * /eviction-defense/wizard. Calls existing APIs only:
 *
 *   POST /api/eviction-defense/calculate-deadlines
 *   GET  /api/forms/defenses
 *   GET  /api/eviction-defense/counterclaims
 *   POST /api/forms/generate
 *   GET  /api/eviction-defense/case-checklist/pretrial
 *   POST /api/forms/library/packet
 *
 * Steps unlock in order; every error keeps its retry button live so the
 * tenant can never dead-end.
 */
(function () {
  "use strict";

  var STEP_ORDER = ["basics", "deadlines", "answer", "counterclaim", "motions", "hearing", "packet"];

  var state = {
    caseData: {},
    answerDefenses: [],
    counterclaims: [],
    motions: [],
    docs: [] // { label, filename, b64 }
  };

  // ---------- DOM helpers ----------

  function el(sel) { return document.querySelector(sel); }
  function els(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function busy(text) {
    var n = el("[data-pw-busy]");
    if (n) n.textContent = text || "";
  }

  function showError(text) {
    var n = el("[data-pw-error]");
    if (!n) return;
    if (text) { n.textContent = text; n.hidden = false; }
    else { n.textContent = ""; n.hidden = true; }
  }

  function setState(step, label) {
    var row = document.querySelector('[data-pw-step="' + step + '"] [data-pw-state]');
    if (row) row.textContent = label;
  }

  function unlock(zone) {
    var body = document.querySelector("[data-pw-" + zone + "-body]");
    var waiting = document.querySelector("[data-pw-" + zone + "-waiting]");
    if (body) body.hidden = false;
    if (waiting) waiting.hidden = true;
  }

  function field(name) {
    var input = document.querySelector('[data-pw-field="' + name + '"]');
    return input ? input.value.trim() : "";
  }

  // ---------- API ----------

  function api(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (opts.body && typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
    return fetch(path, opts).then(function (res) {
      if (res.status === 401 || res.status === 403) {
        var err = new Error("storage-auth");
        err.code = "auth";
        throw err;
      }
      if (!res.ok) {
        return res.text().then(function (t) {
          throw new Error("Request failed (" + res.status + "): " + t.slice(0, 200));
        });
      }
      return res.json();
    });
  }

  function fail(step, e) {
    busy("");
    if (e && e.code === "auth") {
      showError("Your storage connection is needed to build documents. Reconnect your storage from your home page, then come back — your answers here are still on this page.");
      setState(step, "Needs storage connection");
    } else {
      showError("That step did not finish: " + (e && e.message ? e.message : "unknown problem") + " — you can try it again.");
      setState(step, "Needs attention");
    }
  }

  function b64Download(label, filename, b64) {
    try {
      var bin = atob(b64);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      var url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
      var a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.textContent = label;
      return a;
    } catch (e) {
      return null;
    }
  }

  function addDoc(label, filename, b64) {
    state.docs.push({ label: label, filename: filename, b64: b64 });
    var list = el("[data-pw-doc-list]");
    if (!list) return;
    var li = document.createElement("li");
    var a = b64Download(label, filename, b64);
    if (a) { li.appendChild(a); list.appendChild(li); }
  }

  // ---------- Step handlers ----------

  function stepBasics() {
    showError("");
    var d = {
      tenant_name: field("tenant_name"),
      landlord_name: field("landlord_name"),
      county: field("county"),
      case_number: field("case_number"),
      defendant_address: field("address"),
      service_date: field("service_date"),
      hearing_date: field("hearing_date")
    };
    if (!d.tenant_name || !d.landlord_name || !d.service_date) {
      showError("Fill in your name, the landlord's name, and the date you were served — those three are required.");
      return;
    }
    if (d.county) d.court_name = d.county + " County District Court";

    state.caseData = d;
    setState("basics", "Done");
    busy("Checking your deadlines…");

    api("/api/eviction-defense/calculate-deadlines", {
      method: "POST",
      body: { service_date: d.service_date, case_type: "nonpayment" }
    }).then(function (res) {
      busy("");
      var list = el("[data-pw-deadline-list]");
      var warn = el("[data-pw-deadline-warn]");
      if (list) {
        list.innerHTML = "";
        var rows = [
          ["Answer due", res.answer_due],
          ["Jury demand due", res.jury_demand_due],
          ["Estimated hearing", res.estimated_hearing],
          ["Estimated jury trial", res.estimated_jury_trial]
        ];
        rows.forEach(function (r) {
          if (!r[1]) return;
          var li = document.createElement("li");
          li.textContent = r[0] + ": " + r[1];
          list.appendChild(li);
        });
      }
      if (warn && res.warnings && res.warnings.length) {
        warn.textContent = res.warnings.join(" ");
        warn.hidden = false;
      }
      el("[data-pw-deadlines]").hidden = false;
      el("[data-pw-deadlines-waiting]").hidden = true;
      setState("deadlines", "Ready");
    }).catch(function (e) { fail("deadlines", e); });
  }

  function stepDeadlinesDone() {
    setState("deadlines", "Done");
    loadDefenses();
  }

  function loadDefenses() {
    busy("Loading defenses…");
    api("/api/forms/defenses").then(function (list) {
      busy("");
      var box = el("[data-pw-defense-list]");
      if (box) {
        box.innerHTML = "";
        (list || []).forEach(function (d) {
          var id = d.type || d.id;
          var label = d.title || d.label || id;
          if (d.statute) label += " (" + d.statute + ")";
          var l = document.createElement("label");
          l.className = "shell-check";
          var c = document.createElement("input");
          c.type = "checkbox";
          c.value = id;
          var s = document.createElement("span");
          s.textContent = " " + label;
          l.appendChild(c);
          l.appendChild(s);
          box.appendChild(l);
        });
      }
      unlock("answer");
    }).catch(function (e) { fail("answer", e); });
  }

  function stepAnswer() {
    showError("");
    var chosen = els("[data-pw-defense-list] input:checked").map(function (c) { return c.value; });
    if (!chosen.length) {
      showError("Pick at least one defense — if none look right, choose the closest and explain below.");
      return;
    }
    state.answerDefenses = chosen;
    setState("answer", "In progress");
    busy("Putting together your Answer…");

    var data = Object.assign({}, state.caseData, {
      defenses: chosen,
      defense_details: field("defense_details")
    });

    api("/api/forms/generate", {
      method: "POST",
      body: { form_type: "answer_to_complaint", case_data: data, defenses: chosen, output_format: "pdf" }
    }).then(function (res) {
      busy("");
      var fname = "Answer_to_Eviction_" + state.caseData.tenant_name.replace(/\s+/g, "_") + ".pdf";
      addDoc("Answer to Eviction Complaint", fname, res.content);
      var note = el("[data-pw-answer-result]");
      if (note) { note.textContent = "Your Answer is ready — it is listed under step 7 for download."; note.hidden = false; }
      setState("answer", "Done");
      loadCounterclaims();
    }).catch(function (e) { fail("answer", e); });
  }

  function loadCounterclaims() {
    unlock("counterclaim");
    busy("Loading claims…");
    api("/api/eviction-defense/counterclaims").then(function (list) {
      busy("");
      var box = el("[data-pw-claim-list]");
      if (box) {
        box.innerHTML = "";
        (list || []).forEach(function (c) {
          var id = c.id || c.claim_id || (c.name || c.title || "").toLowerCase().replace(/[^a-z0-9]+/g, "_");
          var label = c.name || c.title || id;
          var l = document.createElement("label");
          l.className = "shell-check";
          var cb = document.createElement("input");
          cb.type = "checkbox";
          cb.value = id;
          var s = document.createElement("span");
          s.textContent = " " + label;
          l.appendChild(cb);
          l.appendChild(s);
          box.appendChild(l);
        });
      }
    }).catch(function () {
      // Claims list is optional — leave the box empty, the details box still works.
      busy("");
    });
  }

  function stepCounterclaim() {
    showError("");
    var chosen = els("[data-pw-claim-list] input:checked").map(function (c) { return c.value; });
    var details = field("claim_details");
    if (!chosen.length && !details) {
      showError("Pick a claim or describe what happened — or use Skip if there is nothing to claim.");
      return;
    }
    state.counterclaims = chosen;
    setState("counterclaim", "In progress");
    busy("Putting together your counterclaim…");

    var data = Object.assign({}, state.caseData, {
      claims: chosen,
      claim_details: details
    });

    api("/api/forms/generate", {
      method: "POST",
      body: { form_type: "counterclaim", case_data: data, output_format: "pdf" }
    }).then(function (res) {
      busy("");
      var fname = "Counterclaim_" + state.caseData.tenant_name.replace(/\s+/g, "_") + ".pdf";
      addDoc("Counterclaim", fname, res.content);
      var note = el("[data-pw-cc-result]");
      if (note) { note.textContent = "Your counterclaim is ready — listed under step 7."; note.hidden = false; }
      setState("counterclaim", "Done");
      unlock("motions");
    }).catch(function (e) { fail("counterclaim", e); });
  }

  function stepCounterclaimSkip() {
    setState("counterclaim", "Skipped");
    unlock("motions");
  }

  function stepMotions() {
    showError("");
    var chosen = els("[data-pw-motion-list] input:checked").map(function (c) { return c.value; });
    if (!chosen.length) {
      showError("Pick a motion — or use Skip if you do not need one.");
      return;
    }
    state.motions = chosen;
    setState("motions", "In progress");
    busy("Putting together your motions…");

    var names = {
      motion_to_dismiss: "Motion_to_Dismiss",
      motion_for_continuance: "Motion_for_Continuance",
      request_for_hearing: "Request_for_Hearing"
    };
    var grounds = field("motion_grounds");

    var seq = Promise.resolve();
    chosen.forEach(function (ft) {
      seq = seq.then(function () {
        var data = Object.assign({}, state.caseData, { grounds: grounds });
        return api("/api/forms/generate", {
          method: "POST",
          body: { form_type: ft, case_data: data, output_format: "pdf" }
        }).then(function (res) {
          var label = (names[ft] || ft).replace(/_/g, " ");
          addDoc(label, names[ft] + "_" + state.caseData.tenant_name.replace(/\s+/g, "_") + ".pdf", res.content);
        });
      });
    });

    seq.then(function () {
      busy("");
      var note = el("[data-pw-motions-result]");
      if (note) { note.textContent = "Your motions are ready — listed under step 7."; note.hidden = false; }
      setState("motions", "Done");
      loadHearingPrep();
    }).catch(function (e) { fail("motions", e); });
  }

  function stepMotionsSkip() {
    setState("motions", "Skipped");
    loadHearingPrep();
  }

  function loadHearingPrep() {
    unlock("hearing");
    busy("Loading your checklist…");
    api("/api/eviction-defense/case-checklist/pretrial").then(function (res) {
      busy("");
      var list = el("[data-pw-checklist]");
      if (!list) return;
      list.innerHTML = "";
      var items = [];
      if (Array.isArray(res)) items = res;
      else if (res && Array.isArray(res.checklist)) items = res.checklist;
      else if (res && Array.isArray(res.items)) items = res.items;
      else if (res && Array.isArray(res.tasks)) items = res.tasks;
      items.forEach(function (it) {
        var li = document.createElement("li");
        li.textContent = typeof it === "string" ? it : (it.task || it.title || it.label || it.text || JSON.stringify(it));
        list.appendChild(li);
      });
      if (!items.length) {
        var li2 = document.createElement("li");
        li2.textContent = "Bring your lease, every paper you were served, rent receipts, photos of the home, and anything in writing between you and the landlord.";
        list.appendChild(li2);
      }
    }).catch(function () {
      busy("");
      var list = el("[data-pw-checklist]");
      if (list) {
        var li = document.createElement("li");
        li.textContent = "Bring your lease, every paper you were served, rent receipts, photos of the home, and anything in writing between you and the landlord.";
        list.appendChild(li);
      }
    });
  }

  function stepHearingDone() {
    setState("hearing", "Done");
    unlock("packet");
  }

  function stepPacket() {
    showError("");
    if (!state.docs.length) {
      showError("Nothing to bundle yet — build at least your Answer above first.");
      return;
    }
    setState("packet", "In progress");
    busy("Merging your documents into one packet…");

    var items = [{ form_id: "answer_to_complaint", field_values: Object.assign({}, state.caseData, { defenses: state.answerDefenses, defense_details: field("defense_details") }) }];
    if (state.counterclaims.length || field("claim_details")) {
      items.push({ form_id: "counterclaim", field_values: Object.assign({}, state.caseData, { claims: state.counterclaims, claim_details: field("claim_details") }) });
    }
    state.motions.forEach(function (ft) {
      items.push({ form_id: ft, field_values: Object.assign({}, state.caseData, { grounds: field("motion_grounds") }) });
    });

    api("/api/forms/library/packet", {
      method: "POST",
      body: { items: items, filename: "Defense_Packet_" + state.caseData.tenant_name.replace(/\s+/g, "_") + ".pdf" }
    }).then(function (res) {
      busy("");
      var a = b64Download("Complete defense packet (all documents in one PDF)", res.filename || "Defense_Packet.pdf", res.content);
      var note = el("[data-pw-packet-result]");
      if (a) {
        a.click();
        if (note) { note.textContent = "Your complete packet downloaded. Individual documents are listed above and saved in your storage."; note.hidden = false; }
        setState("packet", "Done");
      } else {
        throw new Error("packet decode failed");
      }
    }).catch(function (e) { fail("packet", e); });
  }

  // ---------- Wire-up ----------

  var actions = {
    "basics": stepBasics,
    "deadlines-done": stepDeadlinesDone,
    "answer": stepAnswer,
    "counterclaim": stepCounterclaim,
    "counterclaim-skip": stepCounterclaimSkip,
    "motions": stepMotions,
    "motions-skip": stepMotionsSkip,
    "hearing-done": stepHearingDone,
    "packet": stepPacket
  };

  els("[data-pw-action]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var fn = actions[btn.getAttribute("data-pw-action")];
      if (fn) fn();
    });
  });
})();
