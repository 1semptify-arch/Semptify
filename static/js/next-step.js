/**
 * Semptify Next Step Navigation
 * Adds contextual "Next Step" buttons to guide users through workflows
 * 
 * Features:
 * - Auto-detects current page and suggests next step
 * - Shows progress indicator
 * - Persists progress in localStorage
 * 
 * Usage: Include on workflow pages:
 *   <script src="/static/js/next-step.js"></script>
 *   <div id="next-step-container"></div>
 */

const NextStepNav = {
    // Define the main workflow sequence
    workflow: [
        {
            id: 'intake',
            name: 'Upload Documents',
            description: 'Submit your notices and evidence',
            page: '/static/document_intake.html',
            icon: '📄',
            checkComplete: () => parseInt(localStorage.getItem('semptify_doc_count') || '0') > 0
        },
        {
            id: 'timeline',
            name: 'Build Timeline',
            description: 'Document what happened and when',
            page: '/static/timeline.html',
            icon: '📅',
            checkComplete: () => parseInt(localStorage.getItem('semptify_timeline_count') || '0') >= 3
        },
        {
            id: 'answer',
            name: 'Prepare Answer',
            description: 'Draft your legal response',
            page: '/static/eviction_answer.html',
            icon: '⚖️',
            checkComplete: () => localStorage.getItem('semptify_has_answer') === 'true'
        },
        {
            id: 'court',
            name: 'Court Packet',
            description: 'Assemble documents for court',
            page: '/static/court_packet.html',
            icon: '📋',
            checkComplete: () => localStorage.getItem('semptify_has_court_packet') === 'true'
        },
        {
            id: 'complete',
            name: 'Ready for Court',
            description: 'Review and finalize everything',
            page: '/static/briefcase.html',
            icon: '✅',
            checkComplete: () => localStorage.getItem('semptify_court_ready') === 'true'
        }
    ],

    /**
     * Get current workflow step based on page
     */
    getCurrentStepIndex() {
        const path = window.location.pathname;
        return this.workflow.findIndex(step => path.includes(step.page.split('/').pop()));
    },

    /**
     * Get next incomplete step
     */
    getNextIncompleteStep() {
        return this.workflow.find(step => !step.checkComplete());
    },

    /**
     * Get all completed steps
     */
    getCompletedSteps() {
        return this.workflow.filter(step => step.checkComplete());
    },

    /**
     * Calculate progress percentage
     */
    getProgressPercentage() {
        const completed = this.getCompletedSteps().length;
        return Math.round((completed / this.workflow.length) * 100);
    },

    /**
     * Render the Next Step button
     */
    renderNextStepButton(container) {
        const currentIndex = this.getCurrentStepIndex();
        const nextStep = currentIndex >= 0 && currentIndex < this.workflow.length - 1
            ? this.workflow[currentIndex + 1]
            : this.getNextIncompleteStep();

        if (!nextStep || nextStep.checkComplete()) {
            // All done! Show celebration message
            container.innerHTML = this.renderCompletionMessage();
            return;
        }

        container.innerHTML = `
            <div class="next-step-card">
                <div class="next-step-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${this.getProgressPercentage()}%"></div>
                    </div>
                    <span class="progress-text">${this.getProgressPercentage()}% Complete</span>
                </div>
                <div class="next-step-content">
                    <span class="next-step-icon">${nextStep.icon}</span>
                    <div class="next-step-info">
                        <div class="next-step-label">Next Step</div>
                        <div class="next-step-name">${nextStep.name}</div>
                        <div class="next-step-desc">${nextStep.description}</div>
                    </div>
                    <a href="${nextStep.page}" class="next-step-btn">
                        Continue →
                    </a>
                </div>
            </div>
        `;

        this.injectStyles();
    },

    /**
     * Render completion message
     */
    renderCompletionMessage() {
        return `
            <div class="next-step-card next-step-complete">
                <div class="next-step-content">
                    <span class="next-step-icon">🎉</span>
                    <div class="next-step-info">
                        <div class="next-step-name">You're Ready!</div>
                        <div class="next-step-desc">All steps complete. Review your case in Briefcase.</div>
                    </div>
                    <a href="/static/briefcase.html" class="next-step-btn next-step-btn-success">
                        View Case →
                    </a>
                </div>
            </div>
        `;
    },

    /**
     * Render progress stepper (horizontal workflow view)
     */
    renderStepper(container) {
        const currentIndex = this.getCurrentStepIndex();
        
        let html = '<div class="workflow-stepper">';
        
        this.workflow.forEach((step, index) => {
            const isComplete = step.checkComplete();
            const isCurrent = index === currentIndex;
            const isAccessible = index <= currentIndex || isComplete || 
                (index > 0 && this.workflow[index - 1].checkComplete());

            let statusClass = '';
            if (isComplete) statusClass = 'complete';
            else if (isCurrent) statusClass = 'current';
            else if (!isAccessible) statusClass = 'locked';

            html += `
                <div class="stepper-step ${statusClass}">
                    <a href="${isAccessible ? step.page : '#'}" 
                       class="stepper-link ${!isAccessible ? 'disabled' : ''}"
                       ${!isAccessible ? 'onclick="return false;"' : ''}>
                        <span class="stepper-icon">${isComplete ? '✓' : step.icon}</span>
                        <span class="stepper-name">${step.name}</span>
                    </a>
                    ${index < this.workflow.length - 1 ? '<span class="stepper-connector"></span>' : ''}
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
        this.injectStepperStyles();
    },

    /**
     * Mark current step as complete
     */
    markStepComplete(stepId) {
        const step = this.workflow.find(s => s.id === stepId);
        if (step) {
            // Set the appropriate localStorage flag based on step
            switch(stepId) {
                case 'intake':
                    localStorage.setItem('semptify_doc_count', '1');
                    break;
                case 'timeline':
                    localStorage.setItem('semptify_timeline_count', '3');
                    break;
                case 'answer':
                    localStorage.setItem('semptify_has_answer', 'true');
                    break;
                case 'court':
                    localStorage.setItem('semptify_has_court_packet', 'true');
                    break;
                case 'complete':
                    localStorage.setItem('semptify_court_ready', 'true');
                    break;
            }
        }
    },

    /**
     * Inject styles for next step card
     */
    injectStyles() {
        if (document.getElementById('next-step-styles')) return;

        const style = document.createElement('style');
        style.id = 'next-step-styles';
        style.textContent = `
            .next-step-card {
                background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
                box-shadow: 0 4px 15px rgba(26, 35, 126, 0.3);
            }

            .next-step-progress {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 1rem;
            }

            .progress-bar {
                flex: 1;
                height: 6px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                background: #4caf50;
                border-radius: 3px;
                transition: width 0.5s ease;
            }

            .progress-text {
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.75rem;
                white-space: nowrap;
            }

            .next-step-content {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .next-step-icon {
                font-size: 2rem;
                flex-shrink: 0;
            }

            .next-step-info {
                flex: 1;
            }

            .next-step-label {
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .next-step-name {
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
                margin: 0.25rem 0;
            }

            .next-step-desc {
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.85rem;
            }

            .next-step-btn {
                background: white;
                color: #1a237e;
                padding: 0.75rem 1.25rem;
                border-radius: 8px;
                font-weight: 600;
                text-decoration: none;
                white-space: nowrap;
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .next-step-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }

            .next-step-btn-success {
                background: #4caf50;
                color: white;
            }

            .next-step-complete {
                background: linear-gradient(135deg, #2e7d32 0%, #4caf50 100%);
            }

            @media (max-width: 480px) {
                .next-step-content {
                    flex-wrap: wrap;
                }
                
                .next-step-btn {
                    width: 100%;
                    text-align: center;
                    margin-top: 0.5rem;
                }
            }
        `;

        document.head.appendChild(style);
    },

    /**
     * Inject styles for stepper
     */
    injectStepperStyles() {
        if (document.getElementById('stepper-styles')) return;

        const style = document.createElement('style');
        style.id = 'stepper-styles';
        style.textContent = `
            .workflow-stepper {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 1rem;
                background: var(--surface-color, #1e1e1e);
                border-radius: 12px;
                margin: 1rem 0;
                overflow-x: auto;
            }

            .stepper-step {
                display: flex;
                align-items: center;
                flex-shrink: 0;
            }

            .stepper-link {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-decoration: none;
                padding: 0.5rem;
                border-radius: 8px;
                transition: background 0.2s;
            }

            .stepper-link:hover:not(.disabled) {
                background: rgba(255, 255, 255, 0.1);
            }

            .stepper-link.disabled {
                cursor: not-allowed;
                opacity: 0.5;
            }

            .stepper-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--surface-variant, #2a2a2a);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
                margin-bottom: 0.5rem;
                border: 2px solid transparent;
            }

            .stepper-step.complete .stepper-icon {
                background: #4caf50;
                color: white;
            }

            .stepper-step.current .stepper-icon {
                border-color: #3949ab;
                background: #3949ab;
            }

            .stepper-step.locked .stepper-icon {
                opacity: 0.5;
            }

            .stepper-name {
                font-size: 0.75rem;
                color: var(--text-secondary, #aaa);
                text-align: center;
                max-width: 80px;
            }

            .stepper-step.current .stepper-name {
                color: var(--primary, #3949ab);
                font-weight: 600;
            }

            .stepper-connector {
                width: 30px;
                height: 2px;
                background: var(--surface-variant, #2a2a2a);
                margin: 0 0.5rem;
            }

            .stepper-step.complete + .stepper-step .stepper-connector,
            .stepper-step.complete .stepper-connector {
                background: #4caf50;
            }

            @media (max-width: 600px) {
                .workflow-stepper {
                    padding: 0.75rem;
                }

                .stepper-name {
                    display: none;
                }

                .stepper-icon {
                    width: 32px;
                    height: 32px;
                    font-size: 1rem;
                }

                .stepper-connector {
                    width: 20px;
                }
            }
        `;

        document.head.appendChild(style);
    },

    /**
     * Initialize - finds containers and renders components
     */
    init() {
        // Render next step button if container exists
        const nextStepContainer = document.getElementById('next-step-container');
        if (nextStepContainer) {
            this.renderNextStepButton(nextStepContainer);
        }

        // Render stepper if container exists
        const stepperContainer = document.getElementById('workflow-stepper');
        if (stepperContainer) {
            this.renderStepper(stepperContainer);
        }
    }
};

// Expose globally
window.NextStepNav = NextStepNav;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    NextStepNav.init();
});
