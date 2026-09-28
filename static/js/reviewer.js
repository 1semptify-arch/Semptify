/* Reviewer share page (/r/{token}) — anonymous, token-gated.
   Loads the shared bundle, renders documents → reader → ask → Q&A in that
   order. Read-only: this file never writes to a document. */
(function () {
    "use strict";

    var shell = document.getElementById("rsShell");
    if (!shell) return;
    var token = shell.getAttribute("data-token");
    var API = "/api/legal-share/r/" + encodeURIComponent(token);

    var state = {
        currentDoc: null,
        bundle: null,
    };

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    function fmtDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
        } catch (e) {
            return "";
        }
    }

    function api(url, opts) {
        var o = opts || {};
        o.headers = Object.assign({ "Content-Type": "application/json" }, o.headers || {});
        return fetch(url, o).then(function (r) {
            if (r.status === 404 || r.status === 410) {
                // Token died mid-session — reload so the page route renders
                // the calm "not available" state instead of an error blob.
                window.location.reload();
                return null;
            }
            if (!r.ok) throw new Error("request_failed_" + r.status);
            return r.json();
        });
    }

    /* --- documents ----------------------------------------------------------- */

    function renderDocs(docs) {
        var list = document.getElementById("rsDocList");
        list.innerHTML = "";
        docs.forEach(function (d) {
            var li = document.createElement("li");
            var btn = document.createElement("button");
            btn.type = "button";
            btn.innerHTML = esc(d.name || "Untitled document");
            btn.addEventListener("click", function () { openDoc(d); });
            li.appendChild(btn);
            list.appendChild(li);
        });
    }

    function openDoc(d) {
        state.currentDoc = d;
        document.getElementById("rsDocTitle").textContent = d.name || "Document";
        var frame = document.getElementById("rsViewer");
        frame.hidden = false;
        frame.src = API + "/document/" + encodeURIComponent(d.id) + "/content";
        var full = document.getElementById("rsOpenFull");
        full.hidden = false;
        full.href = API + "/document/" + encodeURIComponent(d.id) + "/content";
        document.getElementById("rsViewerEmpty").hidden = true;
        document.getElementById("rsAskForm").hidden = false;
        document.getElementById("rsAskMsg").textContent = "";
        document.getElementById("rsAskBody").value = "";
        document.getElementById("rsAskSubject").value = "";
        Array.prototype.forEach.call(
            document.querySelectorAll("#rsDocList button"),
            function (b) { b.removeAttribute("aria-current"); }
        );
        // mark the active document
        Array.prototype.forEach.call(
            document.querySelectorAll("#rsDocList li"),
            function (li) {
                if (li.textContent === (d.name || "")) {
                    li.querySelector("button").setAttribute("aria-current", "true");
                }
            }
        );
    }

    /* --- notes / deadlines ---------------------------------------------------- */

    function renderNotes(notes) {
        if (!notes || !notes.length) return;
        document.getElementById("rsNotes").hidden = false;
        var list = document.getElementById("rsNoteList");
        notes.forEach(function (n) {
            var li = document.createElement("li");
            li.textContent = n.text;
            list.appendChild(li);
        });
    }

    function renderDeadlines(deadlines) {
        if (!deadlines || !deadlines.length) return;
        document.getElementById("rsDeadlines").hidden = false;
        var list = document.getElementById("rsDeadlineList");
        deadlines.forEach(function (d) {
            var li = document.createElement("li");
            li.textContent = (fmtDate(d.start_datetime) ? fmtDate(d.start_datetime) + " — " : "") + (d.title || "Date");
            list.appendChild(li);
        });
    }

    /* --- threads --------------------------------------------------------------- */

    function renderThreads(threads) {
        var host = document.getElementById("rsThreadList");
        var empty = document.getElementById("rsThreadsEmpty");
        host.innerHTML = "";
        if (!threads || !threads.length) {
            empty.hidden = false;
            return;
        }
        empty.hidden = true;
        threads.forEach(function (t) {
            var box = document.createElement("div");
            box.className = "rs-thread";
            var status = t.status === "answered" ? "answered" : "waiting";
            var head = '<span class="rs-thread-doc">' + esc(t.document_name || t.document_id) + "</span>" +
                '<span class="rs-thread-status' + (t.status === "answered" ? " is-answered" : "") + '">' + status + "</span>";
            if (t.subject) head += '<div><strong>' + esc(t.subject) + "</strong></div>";
            box.innerHTML = head;
            (t.messages || []).forEach(function (m) {
                var msg = document.createElement("div");
                msg.className = "rs-msg";
                var who = m.side === "reviewer" ? "You" : "Tenant";
                msg.innerHTML = '<span class="rs-msg-side">' + who + '</span><span class="rs-msg-time">' +
                    esc(fmtDate(m.created_at)) + "</span><div>" + esc(m.body) + "</div>";
                box.appendChild(msg);
            });
            // Follow-up box on every thread
            var reply = document.createElement("form");
            reply.className = "rs-reply";
            reply.innerHTML =
                '<textarea class="rs-textarea" rows="2" placeholder="Add a follow-up…" aria-label="Follow-up message"></textarea>' +
                '<button type="submit" class="rs-btn">Send</button>';
            reply.addEventListener("submit", function (ev) {
                ev.preventDefault();
                var body = reply.querySelector("textarea").value.trim();
                if (!body) return;
                api(API + "/threads/" + encodeURIComponent(t.thread_id) + "/messages", {
                    method: "POST",
                    body: JSON.stringify({ body: body }),
                }).then(function (t2) {
                    if (t2) loadThreads();
                }).catch(function () {});
            });
            box.appendChild(reply);
            host.appendChild(box);
        });
    }

    function loadThreads() {
        api(API + "/threads").then(function (data) {
            if (data) renderThreads(data.threads);
        }).catch(function () {});
    }

    /* --- ask ------------------------------------------------------------------- */

    document.getElementById("rsAskForm").addEventListener("submit", function (ev) {
        ev.preventDefault();
        if (!state.currentDoc) return;
        var body = document.getElementById("rsAskBody").value.trim();
        var subject = document.getElementById("rsAskSubject").value.trim();
        var msg = document.getElementById("rsAskMsg");
        if (!body) return;
        msg.textContent = "Sending…";
        api(API + "/questions", {
            method: "POST",
            body: JSON.stringify({ document_id: state.currentDoc.id, body: body, subject: subject || null }),
        }).then(function (t) {
            if (!t) return;
            msg.textContent = "Sent — it appears below under Questions & answers.";
            document.getElementById("rsAskBody").value = "";
            document.getElementById("rsAskSubject").value = "";
            loadThreads();
        }).catch(function () {
            msg.textContent = "Couldn't send — try again.";
        });
    });

    /* --- boot ------------------------------------------------------------------ */

    api(API).then(function (bundle) {
        if (!bundle) return;
        state.bundle = bundle;
        document.getElementById("rsLoading").hidden = true;
        shell.hidden = false;

        document.getElementById("rsCaseTitle").textContent =
            (bundle.summary && bundle.summary.title) || "Shared case file";
        var meta = [];
        if (bundle.reviewer_label) meta.push("Prepared for " + bundle.reviewer_label);
        if (bundle.expires_at) meta.push("Link works until " + fmtDate(bundle.expires_at));
        document.getElementById("rsMeta").textContent = meta.join(" · ");

        renderDocs(bundle.documents || []);
        renderNotes(bundle.notes);
        renderDeadlines(bundle.deadlines);
        renderThreads(bundle.threads);
    }).catch(function () {
        document.getElementById("rsLoading").textContent =
            "This file couldn't be opened right now. Try the link again in a few minutes.";
    });
})();
