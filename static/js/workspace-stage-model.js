/* Workspace Stage Model - Semptify 5.0
   Runtime stage management for workspace panels.

   Pulls canonical case state from /api/workflow/case-state and asks
   /api/workflow/next-step for the single best next action. Renders
   stage cards and alerts into the workspace panel container.

   Failure mode: if the workflow service is unavailable, we fall back
   to a safe "connect storage" next action so the tenant is never
   stuck on a blank screen.
*/

(function () {
    'use strict';

    var FALLBACK_NEXT_ACTION = 'connect_storage';
    var FALLBACK_NEXT_ROUTE = '/storage/providers';

    function buildNextStepRequest(caseState) {
        return {
            role: caseState.role || 'user',
            storage_state: caseState.storage_connected ? 'already_connected' : 'need_connect',
            documents_present: !!caseState.documents_present,
            has_active_case: !!caseState.has_active_case,
            timeline_events: caseState.timeline_events || 0,
            defense_started: !!caseState.defense_started,
            court_packet_ready: !!caseState.court_packet_ready,
            hearing_scheduled: !!caseState.hearing_scheduled,
        };
    }

    function renderStageCards(container, payload) {
        if (!container) return;
        var cards = Array.isArray(payload.stage_cards) ? payload.stage_cards : [];
        container.innerHTML = '';
        cards.forEach(function (card) {
            var el = document.createElement('div');
            el.className = 'workspace-stage__card';
            el.setAttribute('data-card-id', card.card_id || '');
            el.innerHTML =
                '<h4>' + (card.title || '') + '</h4>' +
                '<p>' + (card.description || '') + '</p>' +
                '<a class="btn btn--' + (card.button_variant || 'primary') + '" href="' + (card.route || '#') + '">' +
                (card.button_label || 'Open') + '</a>';
            container.appendChild(el);
        });
    }

    function renderAlerts(container, payload) {
        if (!container) return;
        var alerts = Array.isArray(payload.alerts) ? payload.alerts : [];
        if (alerts.length === 0) {
            container.innerHTML = '<p class="workspace-stage__alert-good">No urgent issues detected.</p>';
            return;
        }
        container.innerHTML = '';
        alerts.forEach(function (alert) {
            var el = document.createElement('div');
            el.className = 'workspace-stage__alert workspace-stage__alert--' + (alert.level || 'good');
            el.textContent = alert.message || '';
            container.appendChild(el);
        });
    }

    function applyNextStep(payload) {
        var next = payload || {};
        var banner = document.querySelector('[data-workflow-next-action]');
        if (banner) {
            banner.setAttribute('data-next-action', next.next_action || FALLBACK_NEXT_ACTION);
            banner.setAttribute('data-next-route', next.next_route || FALLBACK_NEXT_ROUTE);
            banner.textContent = next.deterministic_reason || 'Continue to your next step.';
        }
    }

    function applyFallback(message) {
        var banner = document.querySelector('[data-workflow-next-action]');
        if (banner) {
            banner.setAttribute('data-next-action', FALLBACK_NEXT_ACTION);
            banner.setAttribute('data-next-route', FALLBACK_NEXT_ROUTE);
            banner.textContent = message || 'Workflow service unavailable. Refresh to retry.';
        }
        // Expose fallback payload so callers can inspect the resolved next step
        // without querying the DOM. Shape mirrors NextStepResponse from the API.
        window.WorkspaceStageModel = window.WorkspaceStageModel || {};
        window.WorkspaceStageModel.lastNextStep = {
            next_process: 'A',
            next_route: '/storage/providers',
            next_action: 'connect_storage',
            deterministic_reason: message || 'Workflow service unavailable. Refresh to retry.',
            warnings: [],
        };
    }

    async function loadCaseState() {
        var response = await fetch('/api/workflow/case-state');
        if (!response.ok) {
            throw new Error('case-state HTTP ' + response.status);
        }
        return await response.json();
    }

    async function loadNextStep(caseState) {
        var response = await fetch('/api/workflow/next-step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(buildNextStepRequest(caseState)),
        });
        if (!response.ok) {
            throw new Error('next-step HTTP ' + response.status);
        }
        return await response.json();
    }

    async function refresh() {
        var cardsContainer = document.querySelector('[data-workflow-stage-cards]');
        var alertsContainer = document.querySelector('[data-workflow-alerts]');

        try {
            var caseState = await loadCaseState();
            renderStageCards(cardsContainer, caseState);
            renderAlerts(alertsContainer, caseState);

            try {
                var nextStep = await loadNextStep(caseState);
                applyNextStep(nextStep);
            } catch (_) {
                applyFallback('Workflow service unavailable. Refresh to retry.');
            }
        } catch (_) {
            if (cardsContainer) cardsContainer.innerHTML = '';
            if (alertsContainer) {
                alertsContainer.innerHTML = '<p class="workspace-stage__alert-bad">Workflow service unavailable. Refresh to retry.</p>';
            }
            applyFallback('Workflow service unavailable. Refresh to retry.');
        }
    }

    window.WorkspaceStageModel = {
        init: function () {
            var panels = document.querySelectorAll('.workspace-stage__panel');
            panels.forEach(function (panel) {
                panel.setAttribute('data-stage-ready', 'true');
            });
            refresh().catch(function () {
                applyFallback('Workflow service unavailable. Refresh to retry.');
            });
        },
        refresh: refresh,
        buildNextStepRequest: buildNextStepRequest,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.WorkspaceStageModel.init);
    } else {
        window.WorkspaceStageModel.init();
    }
})();
