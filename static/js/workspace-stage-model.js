(function () {
    function byId(id) {
        return document.getElementById(id);
    }

    function applyCurrentStage(payload) {
        const stageEl = byId('workspaceCaseStageValue');
        if (!stageEl) return;
        stageEl.textContent = payload.current_stage_title || 'Loading...';
    }

    function applyUrgency(payload) {
        const urgencyEl = byId('workspaceUrgencyValue');
        if (!urgencyEl) return;
        urgencyEl.textContent = payload.urgency_level || 'Moderate';
        urgencyEl.title = payload.urgency_reason || '';
    }

    function applyCounts(payload) {
        const docEl = byId('workspaceDocumentCount');
        const timelineEl = byId('workspaceTimelineCount');
        if (docEl) docEl.textContent = String(payload.document_count || 0);
        if (timelineEl) timelineEl.textContent = String(payload.timeline_events || 0);
    }

    function applyNextStep(payload) {
        const titleEl = byId('workspaceNextStepTitle');
        const reasonEl = byId('workspaceNextStepReason');
        const linkEl = byId('workspaceNextStepLink');
        if (!titleEl || !reasonEl || !linkEl) return;

        const actionLabels = {
            connect_storage: 'Connect Storage',
            upload_documents: 'Upload Documents',
            review_timeline: 'Review Timeline',
            start_defense: 'Start Defense Filing',
            build_court_packet: 'Build Court Packet',
            hearing_prep: 'Open Hearing Prep',
            run_zoom_court_prep: 'Open Zoom Court Prep',
            open_case_queue: 'Open Case Workspace',
            collect_case_documents: 'Collect Case Documents',
            build_timeline: 'Build Timeline',
            prepare_court_packet: 'Prepare Court Packet',
        };

        const label = actionLabels[payload.next_action] || 'Continue Workflow';
        titleEl.textContent = label;
        reasonEl.textContent = payload.deterministic_reason || 'Continue with the recommended next workflow step.';
        linkEl.href = payload.next_route || '/';
        linkEl.textContent = label;
    }

    function applyStageCards(payload) {
        const container = byId('workspaceStageCards');
        if (!container) return;

        const cards = Array.isArray(payload.stage_cards) ? payload.stage_cards : [];
        if (!cards.length) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = cards.map((card) => {
            const state = String(card.state || 'Upcoming').toLowerCase();
            const buttonClass = card.button_variant === 'secondary' ? 'btn btn--secondary' : 'btn btn--primary';
            return `
                <article class="workspace-stage-card is-${state}">
                    <span class="workspace-stage-state">${card.state || 'Upcoming'}</span>
                    <h3>${card.title || 'Workflow Stage'}</h3>
                    <p>${card.description || ''}</p>
                    <a class="${buttonClass}" href="${card.route || '/'}">${card.button_label || 'Open'}</a>
                </article>
            `;
        }).join('');
    }

    function applyAlerts(payload) {
        const container = byId('workspaceAlerts');
        if (!container) return;

        const alerts = Array.isArray(payload.alerts) ? payload.alerts : [];
        if (!alerts.length) {
            container.innerHTML = '<div class="alert alert--info">No urgent issues detected.</div>';
            return;
        }

        const levelMap = {
            good: 'success',
            warning: 'warning',
            danger: 'error',
            info: 'info',
        };

        container.innerHTML = alerts.map((alert) => {
            const level = levelMap[alert.level] || 'info';
            return `<div class="alert alert--${level}">${alert.message || ''}</div>`;
        }).join('');
    }

    function buildNextStepRequest(caseState) {
        return {
            role: caseState.role || 'user',
            storage_state: caseState.storage_connected ? 'already_connected' : 'need_connect',
            documents_present: !!caseState.documents_present,
            has_active_case: !!caseState.documents_present || (caseState.timeline_events || 0) > 0,
            timeline_events: caseState.timeline_events || 0,
            defense_started: !!caseState.defense_started,
            court_packet_ready: !!caseState.court_packet_ready,
            hearing_scheduled: !!caseState.hearing_scheduled,
        };
    }

    async function loadWorkspaceStageModel() {
        if (!byId('workspaceStageModel')) return;

        try {
            const stateResp = await fetch('/api/workflow/case-state', { credentials: 'include' });
            if (!stateResp.ok) {
                throw new Error('case-state unavailable');
            }

            const caseState = await stateResp.json();
            applyCurrentStage(caseState);
            applyUrgency(caseState);
            applyCounts(caseState);
            applyStageCards(caseState);
            applyAlerts(caseState);

            const nextStepResp = await fetch('/api/workflow/next-step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(buildNextStepRequest(caseState)),
            });

            if (!nextStepResp.ok) {
                throw new Error('next-step unavailable');
            }

            const nextStep = await nextStepResp.json();
            applyNextStep(nextStep);
        } catch (_) {
            applyCurrentStage({ current_stage_title: 'Workflow Overview' });
            applyUrgency({ urgency_level: 'Moderate', urgency_reason: 'Workflow service unavailable.' });
            applyCounts({ document_count: 0, timeline_events: 0 });
            applyStageCards({ stage_cards: [] });
            applyAlerts({ alerts: [{ level: 'warning', message: 'Workflow service unavailable. Refresh to retry.' }] });
            applyNextStep({
                next_action: 'connect_storage',
                next_route: '/storage/providers',
                deterministic_reason: 'Fallback recommendation applied while workflow services are unavailable.',
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadWorkspaceStageModel);
    } else {
        loadWorkspaceStageModel();
    }
})();