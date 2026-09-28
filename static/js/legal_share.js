/* Legal Share tenant page (/legal-share).
   Chronological flow: case → items → reviewer → contact → expiry → create.
   Below the form: the created link, existing shares (revoke at bottom of
   each), then the reviewer-questions panel. */
(function () {
    "use strict";

    var API = "/api/legal-share";
    var caseSelect = document.getElementById("lsCase");
    if (!caseSelect) return;

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    function fmtDate(iso) {
        if (!iso) return "—";
        try {
            return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
        } catch (e) {
            return "—";
        }
    }

    function api(url, opts) {
        var o = opts || {};
        o.headers = Object.assign({ "Content-Type": "application/json" }, o.headers || {});
        return fetchWithCSRF(url, o).then(function (r) {
            if (!r.ok) {
                return r.json().catch(function () { return {}; }).then(function (body) {
                    var err = new Error(body.detail && body.detail.error ? body.detail.error : (body.error || "request_failed"));
                    err.status = r.status;
                    err.body = body;
                    throw err;
                });
            }
            return r.json();
        });
    }

    /* --- step 1: cases ------------------------------------------------------- */

    api(API + "/cases").then(function (data) {
        (data.cases || []).forEach(function (c) {
            var opt = document.createElement("option");
            opt.value = c.incident_id;
            opt.textContent = c.title || ("Case " + c.incident_id);
            caseSelect.appendChild(opt);
        });
    }).catch(function () {});

    /* --- step 2: items -------------------------------------------------------- */

    var currentItems = null;

    caseSelect.addEventListener("change", function () {
        var id = caseSelect.value;
        ["lsItemsStep", "lsReviewerStep", "lsContactStep", "lsExpiryStep", "lsCreateStep"].forEach(function (elId) {
            document.getElementById(elId).hidden = !id;
        });
        if (!id) return;
        api(API + "/cases/" + encodeURIComponent(id) + "/items").then(function (data) {
            currentItems = data;
            renderItems(data);
        }).catch(function () {});
    });

    function renderItems(data) {
        var host = document.getElementById("lsItems");
        host.innerHTML = "";
        var docs = data.documents || [];
        if (!docs.length) {
            host.innerHTML = '<p class="rs-hint">No documents in your vault for this case yet. Upload them in Document Center first.</p>';
        }
        docs.forEach(function (d) {
            var row = document.createElement("label");
            row.className = "ls-doc-row";
            var meta = [];
            if (d.category) meta.push(d.category);
            if (d.document_type) meta.push(d.document_type);
            row.innerHTML =
                '<input type="checkbox" data-doc-id="' + esc(d.id) + '"' + (d.suggested ? " checked" : "") + ">" +
                '<span class="ls-doc-name">' + esc(d.name) +
                '<span class="ls-doc-meta">' + esc(meta.join(" · ")) + "</span></span>";
            host.appendChild(row);
        });

        var dl = document.getElementById("lsDeadlines");
        dl.innerHTML = "";
        var deadlines = data.deadlines || [];
        document.getElementById("lsDeadlinePick").hidden = !deadlines.length;
        deadlines.forEach(function (d) {
            var row = document.createElement("label");
            row.className = "ls-doc-row";
            row.innerHTML =
                '<input type="checkbox" data-deadline-id="' + esc(d.id) + '">' +
                '<span class="ls-doc-name">' + esc(d.title || "Date") +
                '<span class="ls-doc-meta">' + esc(fmtDate(d.start_datetime)) + "</span></span>";
            dl.appendChild(row);
        });
    }

    /* --- step 6: create -------------------------------------------------------- */

    document.getElementById("lsCreateBtn").addEventListener("click", function () {
        var caseId = caseSelect.value;
        var label = document.getElementById("lsReviewer").value.trim();
        var msg = document.getElementById("lsCreateMsg");
        if (!caseId || !label) {
            msg.textContent = "Pick a case and name the reviewer first.";
            return;
        }
        var docIds = Array.prototype.map.call(
            document.querySelectorAll("#lsItems input[data-doc-id]:checked"),
            function (el) { return el.getAttribute("data-doc-id"); }
        );
        if (!docIds.length) {
            msg.textContent = "Check at least one document to share.";
            return;
        }
        var deadlineIds = Array.prototype.map.call(
            document.querySelectorAll("#lsDeadlines input[data-deadline-id]:checked"),
            function (el) { return el.getAttribute("data-deadline-id"); }
        );
        var expiry = document.querySelector('input[name="lsExpiry"]:checked');
        msg.textContent = "Creating…";
        api(API + "/shares", {
            method: "POST",
            body: JSON.stringify({
                case_id: parseInt(caseId, 10),
                reviewer_label: label,
                reviewer_contact: document.getElementById("lsContact").value.trim() || null,
                document_ids: docIds,
                include_notes: document.getElementById("lsIncludeNotes").checked,
                deadline_ids: deadlineIds,
                include_summary: document.getElementById("lsIncludeSummary").checked,
                expires_days: expiry ? parseInt(expiry.value, 10) : 30,
            }),
        }).then(function (data) {
            msg.textContent = "";
            var share = data.share;
            var link = location.origin + share.share_url;
            document.getElementById("lsLink").value = link;
            var mailto = document.getElementById("lsMailto");
            var subject = "Shared case file: " + (share.case_title || "my case");
            var bodyText = "I'm sharing part of my case file with you. Open this link to read the documents and ask questions:\n\n" + link +
                "\n\nThe link works until " + fmtDate(share.expires_at) + ".";
            mailto.href = "mailto:" + encodeURIComponent(share.reviewer_contact || "") +
                "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(bodyText);
            document.getElementById("lsLinkZone").hidden = false;
            document.getElementById("lsLinkZone").scrollIntoView({ behavior: "smooth", block: "nearest" });
            loadShares();
        }).catch(function (e) {
            msg.textContent = e.status === 404 ? "That case couldn't be found." :
                e.status === 400 ? (e.body && e.body.detail ? String(e.body.detail) : "Check the selections above.") :
                "Couldn't create the link — try again in a moment.";
        });
    });

    document.getElementById("lsCopyBtn").addEventListener("click", function () {
        var input = document.getElementById("lsLink");
        input.select();
        try {
            navigator.clipboard.writeText(input.value);
            showFlash("Link copied.", "success");
        } catch (e) {
            document.execCommand("copy");
        }
    });

    /* --- step 8/9: existing shares ---------------------------------------------- */

    function renderShares(shares) {
        var host = document.getElementById("lsShareList");
        host.innerHTML = "";
        document.getElementById("lsSharesEmpty").hidden = shares.length > 0;
        shares.forEach(function (s) {
            var box = document.createElement("div");
            box.className = "ls-share" + (s.status === "active" ? "" : " is-closed");
            var statusLabel = s.status === "active" ? "active" : (s.status === "expired" ? "expired" : "turned off");
            var unread = s.unread_questions ? " · " + s.unread_questions + " new question" + (s.unread_questions === 1 ? "" : "s") : "";
            box.innerHTML =
                '<div class="ls-share-head"><h3 class="rs-section-head">' + esc(s.reviewer_label || "Reviewer") +
                ' <span class="ls-status is-' + esc(s.status) + '">' + statusLabel + "</span></h3>" +
                '<span class="ls-share-meta">' + esc(s.case_title || "") + "</span></div>" +
                '<p class="ls-share-meta">Opened ' + s.access_count + " time" + (s.access_count === 1 ? "" : "s") +
                (s.accessed_at ? " · last opened " + esc(fmtDate(s.accessed_at)) : "") +
                " · works until " + esc(fmtDate(s.expires_at)) + esc(unread) + "</p>";
            var actions = document.createElement("div");
            actions.className = "ls-share-actions";
            if (s.status === "active") {
                var copy = document.createElement("button");
                copy.type = "button";
                copy.className = "rs-btn";
                copy.textContent = "Copy link";
                copy.addEventListener("click", function () {
                    navigator.clipboard.writeText(location.origin + s.share_url).then(function () {
                        showFlash("Link copied.", "success");
                    });
                });
                actions.appendChild(copy);
            }
            box.appendChild(actions);
            if (s.status === "active") {
                var danger = document.createElement("div");
                danger.className = "ls-share-danger";
                var revoke = document.createElement("button");
                revoke.type = "button";
                revoke.className = "rs-btn rs-btn--danger";
                revoke.textContent = "Turn off this link";
                revoke.addEventListener("click", function () {
                    if (!window.confirm("Turn off this link? " + (s.reviewer_label || "Your reviewer") + " won't be able to open it anymore.")) return;
                    api(API + "/shares/" + encodeURIComponent(s.share_id) + "/revoke", { method: "POST" })
                        .then(function () { loadShares(); loadQuestions(); })
                        .catch(function () { showFlash("Couldn't turn off the link — try again.", "error"); });
                });
                danger.appendChild(revoke);
                box.appendChild(danger);
            }
            host.appendChild(box);
        });
    }

    function loadShares() {
        api(API + "/shares").then(function (data) {
            renderShares(data.shares || []);
        }).catch(function () {});
    }

    /* --- step 10: questions ------------------------------------------------------ */

    function renderQuestions(questions) {
        var host = document.getElementById("lsQuestionList");
        host.innerHTML = "";
        document.getElementById("lsQuestionsEmpty").hidden = questions.length > 0;
        questions.forEach(function (t) {
            var box = document.createElement("div");
            box.className = "ls-question is-unread";
            box.innerHTML =
                '<div><span class="rs-thread-doc">' + esc(t.document_name || t.document_id) + "</span>" +
                '<span class="rs-thread-status">from ' + esc(t.reviewer_label || "reviewer") + " · " + esc(t.case_title || "") + "</span></div>" +
                (t.subject ? "<div><strong>" + esc(t.subject) + "</strong></div>" : "");
            (t.messages || []).forEach(function (m) {
                var msg = document.createElement("div");
                msg.className = "rs-msg";
                var who = m.side === "reviewer" ? (t.reviewer_label || "Reviewer") : "You";
                msg.innerHTML = '<span class="rs-msg-side">' + esc(who) + '</span><span class="rs-msg-time">' +
                    esc(fmtDate(m.created_at)) + "</span><div>" + esc(m.body) + "</div>";
                box.appendChild(msg);
            });
            var reply = document.createElement("form");
            reply.className = "rs-reply";
            reply.innerHTML =
                '<textarea class="rs-textarea" rows="2" required placeholder="Write your answer in your own words…" aria-label="Your answer"></textarea>' +
                '<button type="submit" class="rs-btn rs-btn--primary">Send answer</button>';
            reply.addEventListener("submit", function (ev) {
                ev.preventDefault();
                var body = reply.querySelector("textarea").value.trim();
                if (!body) return;
                api(API + "/shares/" + encodeURIComponent(t.share_id) + "/threads/" + encodeURIComponent(t.thread_id) + "/reply", {
                    method: "POST",
                    body: JSON.stringify({ body: body }),
                }).then(function () {
                    showFlash("Answer sent.", "success");
                    loadQuestions();
                    loadShares();
                }).catch(function () {
                    showFlash("Couldn't send — try again.", "error");
                });
            });
            box.appendChild(reply);
            host.appendChild(box);
        });
    }

    function loadQuestions() {
        api(API + "/questions").then(function (data) {
            renderQuestions(data.questions || []);
        }).catch(function () {});
    }

    loadShares();
    loadQuestions();
})();
