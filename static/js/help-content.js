/**
 * Semptify Help Content Database
 * 
 * This file contains all help content for every page.
 * Content is loaded on-demand when help mode is enabled.
 * 
 * Structure:
 * - cards: Help banners that appear at the top of card sections
 * - tooltips: Hover tooltips for buttons and interactive elements
 */

window.SEMPTIFY_HELP_CONTENT = {
    
    // ==================== DOCUMENT INTAKE PAGE ====================
    'document-intake': {
        cards: {
            '.card:has(#uploadZone)': '<strong>Upload Card:</strong> This is where you add new documents to the system. Upload legal documents like eviction notices, leases, or court papers to have them analyzed and securely registered.',
            '.card:has(#documentQueue)': '<strong>Document Queue:</strong> Shows documents you\'ve uploaded that are waiting to be processed or registered. Click any document to select it and see its analysis results on the right.',
            '.card:has(#registeredDocsList)': '<strong>Registered Documents:</strong> Shows ALL documents that have been officially registered. Click any document to view its details, verify integrity, or see chain of custody.',
            '.card:has(.tabs)': '<strong>Analysis Results:</strong> View extracted data from your documents. Use the tabs to see different types of information: Overview, Extracted Data, Issues, Registry details, and Chain of Custody.'
        },
        tooltips: {
            '#processAllBtn': {
                title: '⚙️ Process All Documents',
                content: '<strong>What:</strong> Analyzes all uploaded documents using AI to extract dates, parties, deadlines, and legal issues.<br><br><strong>Why:</strong> Processing identifies key information and potential problems in your documents automatically.',
                when: 'Click after uploading documents. Button is disabled until you have unprocessed documents.',
                position: 'tooltip-bottom'
            },
            '#registerAllBtn': {
                title: '✓ Register All Documents',
                content: '<strong>What:</strong> Creates a tamper-proof record of each document with cryptographic hash verification.<br><br><strong>Why:</strong> Registration proves the document existed at this time and hasn\'t been altered - critical for court evidence.',
                when: 'Click after processing to permanently register documents. Cannot be undone.',
                position: 'tooltip-bottom'
            },
            '#clearQueueBtn': {
                title: '🗑️ Clear Upload Queue',
                content: '<strong>What:</strong> Removes all documents from the current upload queue (NOT registered documents).<br><br><strong>Why:</strong> Start fresh if you uploaded wrong files or want to begin a new batch.',
                when: 'Click to clear the queue. Already registered documents are NOT affected.',
                position: 'tooltip-bottom'
            },
            '#caseNumber': {
                title: '📋 Case Number',
                content: 'Link documents to a specific legal case. This helps organize all related documents together and makes them easy to find later.',
                when: 'Enter this if you have a court case number or want to group documents.',
                position: 'tooltip-right'
            },
            '#uploadZone': {
                title: '📤 Upload Zone',
                content: 'Drag and drop files here OR click to browse your computer. You can upload multiple files at once.<br><br>Supported formats: PDF, DOCX, DOC, JPG, PNG, TIFF',
                when: 'Use this to add any legal document you\'ve received (eviction notice, lease, court summons, etc.)',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== DASHBOARD PAGE ====================
    'dashboard': {
        cards: {
            '.card:has(.case-summary)': '<strong>Case Summary:</strong> Overview of your current legal situation including key dates, deadlines, and action items.',
            '.card:has(.recent-activity)': '<strong>Recent Activity:</strong> Shows your latest actions - document uploads, case updates, and important notifications.',
            '.card:has(.quick-actions)': '<strong>Quick Actions:</strong> Common tasks you can do with one click - upload documents, check deadlines, get legal help.'
        },
        tooltips: {
            '.btn-upload': {
                title: '📤 Upload Document',
                content: 'Quickly upload a new document to your case.',
                when: 'Use when you receive new legal papers.',
                position: 'tooltip-bottom'
            },
            '.btn-timeline': {
                title: '📅 View Timeline',
                content: 'See all events and deadlines in chronological order.',
                when: 'Use to understand what happened and what\'s coming up.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== DOCUMENTS PAGE ====================
    'documents': {
        cards: {
            '.card:has(.document-list)': '<strong>Your Documents:</strong> All documents you\'ve uploaded organized by type and date. Click any document to view, download, or manage it.',
            '.card:has(.document-filters)': '<strong>Filters:</strong> Narrow down your documents by type, date, status, or search terms.'
        },
        tooltips: {
            '.btn-view': {
                title: '👁️ View Document',
                content: 'Open and read the document in the viewer.',
                position: 'tooltip-bottom'
            },
            '.btn-download': {
                title: '⬇️ Download',
                content: 'Save a copy of this document to your computer.',
                position: 'tooltip-bottom'
            },
            '.btn-verify': {
                title: '✅ Verify Integrity',
                content: 'Check if the document has been tampered with since registration.',
                when: 'Use if you need to prove document authenticity.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== TIMELINE PAGE ====================
    'timeline': {
        cards: {
            '.card:has(.timeline-view)': '<strong>Case Timeline:</strong> Visual history of all events in your case - when documents were received, court dates, deadlines, and actions taken.',
            '.card:has(.upcoming-deadlines)': '<strong>Upcoming Deadlines:</strong> Important dates you need to prepare for. Missing these could hurt your case!'
        },
        tooltips: {
            '.btn-add-event': {
                title: '➕ Add Event',
                content: 'Manually add an event to your timeline.',
                when: 'Use for events that weren\'t automatically detected.',
                position: 'tooltip-bottom'
            },
            '.btn-export': {
                title: '📤 Export Timeline',
                content: 'Download your timeline as a PDF or printable document.',
                when: 'Use when preparing for court or sharing with your lawyer.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== CALENDAR PAGE ====================
    'calendar': {
        cards: {
            '.card:has(.calendar-view)': '<strong>Calendar:</strong> See all your court dates, deadlines, and scheduled events. Click any date to see details or add new events.',
            '.card:has(.event-list)': '<strong>Upcoming Events:</strong> List of your next appointments and deadlines sorted by date.'
        },
        tooltips: {
            '.btn-add-event': {
                title: '➕ Add Event',
                content: 'Schedule a new court date, meeting, or deadline.',
                when: 'Use when you have a new date to track.',
                position: 'tooltip-bottom'
            },
            '.btn-sync': {
                title: '🔄 Sync Calendar',
                content: 'Connect to Google Calendar or Outlook to see events in your other calendars.',
                when: 'Use to keep all your calendars in sync.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== EVICTION DEFENSE PAGE ====================
    'eviction': {
        cards: {
            '.card:has(.case-status)': '<strong>Case Status:</strong> Where your eviction case currently stands and what stage you\'re in.',
            '.card:has(.defense-options)': '<strong>Defense Options:</strong> Legal defenses that may apply to your situation based on Minnesota tenant rights law.',
            '.card:has(.action-items)': '<strong>Action Items:</strong> Things you need to do right now to protect your rights. Prioritized by urgency.'
        },
        tooltips: {
            '.btn-analyze': {
                title: '🔍 Analyze Notice',
                content: 'Have AI review your eviction notice for legal defects and violations.',
                when: 'Use immediately after receiving any eviction-related document.',
                position: 'tooltip-bottom'
            },
            '.btn-generate-response': {
                title: '📝 Generate Response',
                content: 'Create a legal response document based on your situation.',
                when: 'Use when you need to formally respond to landlord or court.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== COMPLAINTS PAGE ====================
    'complaints': {
        cards: {
            '.card:has(.complaint-form)': '<strong>File Complaint:</strong> Report landlord violations to Minnesota regulatory agencies. We help you fill out the correct forms.',
            '.card:has(.complaint-history)': '<strong>Your Complaints:</strong> Track complaints you\'ve filed and their current status.'
        },
        tooltips: {
            '.btn-submit': {
                title: '📤 Submit Complaint',
                content: 'Send your completed complaint to the appropriate agency.',
                when: 'Use after filling out all required fields. Review before submitting!',
                position: 'tooltip-bottom'
            },
            '.btn-save-draft': {
                title: '💾 Save Draft',
                content: 'Save your progress without submitting.',
                when: 'Use if you need to gather more information before submitting.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== BRAIN/COPILOT PAGE ====================
    'brain': {
        cards: {
            '.card:has(.chat-interface)': '<strong>AI Legal Assistant:</strong> Ask questions about your situation, get explanations of legal terms, or request help with documents.',
            '.card:has(.suggested-questions)': '<strong>Suggested Questions:</strong> Common questions others in similar situations have asked.'
        },
        tooltips: {
            '#sendMessage': {
                title: '📤 Send Message',
                content: 'Ask the AI assistant your question.',
                when: 'Type your question first, then click to send.',
                position: 'tooltip-bottom'
            },
            '.btn-clear-chat': {
                title: '🗑️ Clear Chat',
                content: 'Start a fresh conversation.',
                when: 'Use when you want to change topics or start over.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== SETTINGS PAGE ====================
    'settings': {
        cards: {
            '.card:has(.profile-settings)': '<strong>Profile:</strong> Your personal information and contact details.',
            '.card:has(.notification-settings)': '<strong>Notifications:</strong> Control how and when you receive alerts about deadlines and case updates.',
            '.card:has(.storage-settings)': '<strong>Storage:</strong> Where your documents are saved - local device or cloud backup.'
        },
        tooltips: {
            '.btn-save': {
                title: '💾 Save Changes',
                content: 'Save all changes you\'ve made on this page.',
                when: 'Click after making any changes to your settings.',
                position: 'tooltip-bottom'
            },
            '.btn-export-data': {
                title: '📦 Export All Data',
                content: 'Download all your documents and case data as a backup.',
                when: 'Use regularly to keep a backup of your important data.',
                position: 'tooltip-bottom'
            }
        }
    },
    
    // ==================== WELCOME PAGE ====================
    'welcome': {
        cards: {
            '.card:has(.getting-started)': '<strong>Getting Started:</strong> Quick steps to set up Semptify and start protecting your tenant rights.',
            '.card:has(.features)': '<strong>Features:</strong> What Semptify can do to help you with your legal situation.'
        },
        tooltips: {
            '.btn-start': {
                title: '🚀 Get Started',
                content: 'Begin the setup process to configure Semptify for your situation.',
                when: 'Click this if you\'re new to Semptify.',
                position: 'tooltip-bottom'
            }
        }
    }
};

console.log('✅ Semptify Help Content loaded');
