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
    },

    // ==================== CRISIS INTAKE PAGE ====================
    'crisis_intake': {
        cards: {
            '.intake-card': '<strong>Tell Us What\'s Happening:</strong> Answer simple questions about your situation. We\'ll guide you to the right tools and resources based on your answers.',
            '.crisis-alert': '<strong>⚠️ Crisis Alert:</strong> If you\'re facing immediate housing loss, we\'ll connect you with emergency resources right away.'
        },
        tooltips: {
            '.btn-primary': {
                title: '➡️ Continue',
                content: 'Move to the next question in the intake process.',
                when: 'Click after selecting your answer.',
                position: 'tooltip-bottom'
            },
            '.btn-outline': {
                title: '⬅️ Go Back',
                content: 'Return to the previous question to change your answer.',
                when: 'Use if you selected the wrong option.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== LETTER BUILDER PAGE ====================
    'letter_builder': {
        cards: {
            '.letter-card': '<strong>Letter Templates:</strong> Choose from professionally-drafted letter templates for common landlord-tenant situations.',
            '.editor-container': '<strong>Letter Editor:</strong> Customize your letter with your specific details. The AI will help ensure proper legal language.'
        },
        tooltips: {
            '.btn-generate': {
                title: '✨ Generate Letter',
                content: 'Create a customized letter based on your selections and input.',
                when: 'Click after selecting a template and filling in your details.',
                position: 'tooltip-bottom'
            },
            '.btn-copy': {
                title: '📋 Copy to Clipboard',
                content: 'Copy the generated letter text to paste elsewhere.',
                when: 'Use to paste into email or word processor.',
                position: 'tooltip-bottom'
            },
            '.btn-download': {
                title: '⬇️ Download Letter',
                content: 'Save the letter as a PDF or Word document.',
                when: 'Use to create a formal document for mailing.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== MY TENANCY TIMELINE PAGE ====================
    'my_tenancy': {
        cards: {
            '.timeline-container': '<strong>Your Tenancy Timeline:</strong> Complete history of your rental relationship - move-in, payments, issues, notices, and events.',
            '.upload-section': '<strong>Add Documents:</strong> Upload receipts, communications, photos, and other evidence to your timeline.',
            '.milestone-card': '<strong>Key Milestones:</strong> Important events that may affect your legal rights and defenses.'
        },
        tooltips: {
            '.btn-add-event': {
                title: '➕ Add Event',
                content: 'Record a new event in your tenancy timeline.',
                when: 'Use to document maintenance requests, conversations, payments, etc.',
                position: 'tooltip-bottom'
            },
            '.btn-upload': {
                title: '📤 Upload Evidence',
                content: 'Add photos, receipts, emails, or other documentation to support your timeline.',
                when: 'Upload anything that proves what happened and when.',
                position: 'tooltip-bottom'
            },
            '.btn-export': {
                title: '📄 Export Timeline',
                content: 'Generate a printable timeline document for court or your records.',
                when: 'Use when preparing for court hearings.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== LAW LIBRARY PAGE ====================
    'law_library': {
        cards: {
            '.law-card': '<strong>Legal Resource:</strong> Click to expand and read more about this law or tenant right.',
            '.search-container': '<strong>Search Laws:</strong> Find specific statutes, rights, or topics in Minnesota landlord-tenant law.'
        },
        tooltips: {
            '.btn-bookmark': {
                title: '🔖 Bookmark',
                content: 'Save this law for quick reference later.',
                when: 'Use to build a collection of laws relevant to your case.',
                position: 'tooltip-bottom'
            },
            '.btn-cite': {
                title: '📝 Get Citation',
                content: 'Copy the official legal citation for use in documents.',
                when: 'Use when writing formal legal responses.',
                position: 'tooltip-bottom'
            },
            '.btn-explain': {
                title: '💡 Explain Simply',
                content: 'Get a plain-English explanation of what this law means.',
                when: 'Use if legal language is confusing.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== EVICTION ANSWER PAGE ====================
    'eviction_answer': {
        cards: {
            '.answer-form': '<strong>Answer Form:</strong> Fill out your official response to the eviction complaint. Each field corresponds to the court form.',
            '.defenses-section': '<strong>Available Defenses:</strong> Legal defenses that may apply based on Minnesota law and your situation.',
            '.preview-section': '<strong>Document Preview:</strong> See how your completed Answer will look before filing.'
        },
        tooltips: {
            '.btn-submit': {
                title: '📤 Generate Answer',
                content: 'Create your official Answer document based on your inputs.',
                when: 'Click after completing all required fields.',
                position: 'tooltip-bottom'
            },
            '.btn-save-draft': {
                title: '💾 Save Progress',
                content: 'Save your work to continue later.',
                when: 'Use if you need to gather more information.',
                position: 'tooltip-bottom'
            },
            '.defense-checkbox': {
                title: '✅ Select Defense',
                content: 'Check this box if this defense applies to your situation.',
                when: 'Review each defense carefully - multiple may apply.',
                position: 'tooltip-right'
            }
        }
    },

    // ==================== HEARING PREP PAGE ====================
    'hearing_prep': {
        cards: {
            '.prep-checklist': '<strong>Preparation Checklist:</strong> Everything you need to do before your court date.',
            '.documents-needed': '<strong>Documents to Bring:</strong> Papers and evidence you should have ready for the hearing.',
            '.what-to-expect': '<strong>What to Expect:</strong> Step-by-step guide to what will happen in court.'
        },
        tooltips: {
            '.btn-checklist': {
                title: '☑️ Mark Complete',
                content: 'Check off items as you complete them.',
                when: 'Track your progress preparing for court.',
                position: 'tooltip-right'
            },
            '.btn-practice': {
                title: '🎭 Practice Session',
                content: 'Run through a simulated hearing to practice what you\'ll say.',
                when: 'Use to build confidence before your hearing.',
                position: 'tooltip-bottom'
            },
            '.btn-print-checklist': {
                title: '🖨️ Print Checklist',
                content: 'Print the preparation checklist to use offline.',
                when: 'Great for checking off items as you go.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== CASES PAGE ====================
    'cases': {
        cards: {
            '.case-card': '<strong>Your Cases:</strong> Each card represents an active legal case. Click to view details, documents, and timeline.',
            '.case-summary': '<strong>Case Status:</strong> Overview of where your case stands and what needs attention.',
            '.case-actions': '<strong>Quick Actions:</strong> Common tasks for managing your case.'
        },
        tooltips: {
            '.btn-new-case': {
                title: '➕ New Case',
                content: 'Create a new case file to organize documents and track a legal matter.',
                when: 'Use when you receive a new legal notice or start a new dispute.',
                position: 'tooltip-bottom'
            },
            '.btn-view-case': {
                title: '👁️ View Details',
                content: 'Open the full case view with all documents, timeline, and actions.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== COURT PACKET PAGE ====================
    'court_packet': {
        cards: {
            '.packet-builder': '<strong>Court Packet Builder:</strong> Select which documents to include in your court submission.',
            '.export-options': '<strong>Export Options:</strong> Choose format and organization for your packet.'
        },
        tooltips: {
            '.btn-generate': {
                title: '📦 Generate Packet',
                content: 'Create a professionally organized PDF with all selected documents.',
                when: 'Click after selecting all documents you want to include.',
                position: 'tooltip-bottom'
            },
            '.export-option': {
                title: '📄 Document Option',
                content: 'Check to include this document in your court packet.',
                position: 'tooltip-right'
            }
        }
    },

    // ==================== ZOOM COURT PAGE ====================
    'zoom_court': {
        cards: {
            '.zoom-join-card': '<strong>Join Hearing:</strong> Enter your Zoom link and get ready for your virtual court appearance.',
            '.zoom-tips': '<strong>Courtroom Tips:</strong> Important guidelines for professional virtual court conduct.',
            '.zoom-checklist': '<strong>Pre-Hearing Checklist:</strong> Make sure you\'re fully prepared before your hearing.'
        },
        tooltips: {
            '.btn-join': {
                title: '🎥 Join Hearing',
                content: 'Open Zoom and join your court hearing.',
                when: 'Click when it\'s time for your scheduled hearing.',
                position: 'tooltip-bottom'
            },
            '.btn-test': {
                title: '🔧 Test Setup',
                content: 'Check your camera, microphone, and internet connection.',
                when: 'Test at least 15 minutes before your hearing.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== DAKOTA DEFENSE PAGE ====================
    'dakota_defense': {
        cards: {
            '.defense-hub': '<strong>Defense Hub:</strong> Central command for your Dakota County eviction defense strategy.',
            '.court-forms': '<strong>Court Forms:</strong> Official forms you may need to file with Dakota County Court.',
            '.local-resources': '<strong>Local Resources:</strong> Dakota County specific legal aid and tenant assistance.'
        },
        tooltips: {
            '.btn-file-answer': {
                title: '📝 File Answer',
                content: 'Create and file your official response to the eviction complaint.',
                when: 'Use immediately after being served - you have limited time!',
                position: 'tooltip-bottom'
            },
            '.btn-download-form': {
                title: '⬇️ Download Form',
                content: 'Get the official court form for this filing.',
                when: 'Download, fill out, and file with the court.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== COUNTERCLAIM PAGE ====================
    'counterclaim': {
        cards: {
            '.counterclaim-form': '<strong>Counterclaim Form:</strong> File claims against your landlord for violations that caused you harm.',
            '.claim-types': '<strong>Types of Claims:</strong> Common counterclaims in Minnesota eviction cases.',
            '.damages-calculator': '<strong>Damages:</strong> Calculate potential compensation for landlord violations.'
        },
        tooltips: {
            '.btn-submit': {
                title: '📤 Generate Counterclaim',
                content: 'Create your counterclaim document based on selected violations.',
                when: 'Click after selecting all applicable claims.',
                position: 'tooltip-bottom'
            },
            '.claim-checkbox': {
                title: '✅ Select Claim',
                content: 'Check if this violation applies to your situation.',
                when: 'You can select multiple claims.',
                position: 'tooltip-right'
            }
        }
    },

    // ==================== MOTIONS PAGE ====================
    'motions': {
        cards: {
            '.motion-types': '<strong>Motion Types:</strong> Different motions you can file based on your case situation.',
            '.motion-form': '<strong>Motion Builder:</strong> Fill in details to generate your motion document.',
            '.filing-instructions': '<strong>How to File:</strong> Step-by-step instructions for filing with the court.'
        },
        tooltips: {
            '.btn-generate-motion': {
                title: '📄 Generate Motion',
                content: 'Create your motion document ready for filing.',
                when: 'Click after completing all required fields.',
                position: 'tooltip-bottom'
            },
            '.motion-type-card': {
                title: '📋 Motion Type',
                content: 'Click to select this type of motion.',
                when: 'Review which motion fits your situation.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== BRIEFCASE PAGE ====================
    'briefcase': {
        cards: {
            '.folder-view': '<strong>Document Folders:</strong> Organize your documents into folders like a digital filing cabinet.',
            '.document-list': '<strong>Your Documents:</strong> All uploaded documents with AI analysis and extractions.',
            '.starred-section': '<strong>Starred Items:</strong> Important documents you\'ve marked for quick access.'
        },
        tooltips: {
            '.btn-upload': {
                title: '📤 Upload Document',
                content: 'Add a new document to your briefcase.',
                when: 'Upload leases, notices, receipts, photos, etc.',
                position: 'tooltip-bottom'
            },
            '.btn-new-folder': {
                title: '📁 New Folder',
                content: 'Create a folder to organize your documents.',
                when: 'Use folders like "Court", "Evidence", "Rent Receipts".',
                position: 'tooltip-bottom'
            },
            '.btn-star': {
                title: '⭐ Star Document',
                content: 'Mark this document as important for quick access.',
                position: 'tooltip-right'
            }
        }
    },

    // ==================== TIMELINE BUILDER PAGE ====================
    'timeline_builder': {
        cards: {
            '.timeline-view': '<strong>Event Timeline:</strong> Visual chronological record of your tenancy events.',
            '.event-form': '<strong>Add Event:</strong> Record important dates and events in your case.'
        },
        tooltips: {
            '.btn-add-event': {
                title: '➕ Add Event',
                content: 'Create a new timeline event manually.',
                when: 'Use for events not in your documents.',
                position: 'tooltip-bottom'
            },
            '.btn-export': {
                title: '📄 Export Timeline',
                content: 'Generate a printable PDF of your timeline.',
                when: 'Perfect for court preparation.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== TIMELINE AUTO-BUILD PAGE ====================
    'timeline_auto_build': {
        cards: {
            '.upload-zone': '<strong>Upload Documents:</strong> Drag and drop documents to extract dates automatically using AI.',
            '.extracted-events': '<strong>Extracted Events:</strong> AI-detected dates and events from your documents.'
        },
        tooltips: {
            '.btn-analyze': {
                title: '🔍 Analyze',
                content: 'Have AI scan documents and extract important dates.',
                when: 'Works best with court papers, notices, and leases.',
                position: 'tooltip-bottom'
            },
            '.btn-confirm': {
                title: '✅ Confirm Events',
                content: 'Add the extracted events to your timeline.',
                when: 'Review extracted dates before confirming.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== INTERACTIVE TIMELINE PAGE ====================
    'interactive_timeline': {
        cards: {
            '.timeline-view': '<strong>Interactive Timeline:</strong> Zoomable view of your case from days to months to years.',
            '.zoom-controls': '<strong>Zoom Controls:</strong> Adjust the view to see more or less detail.'
        },
        tooltips: {
            '.btn-zoom-in': {
                title: '🔍+ Zoom In',
                content: 'See more detail - down to individual days.',
                position: 'tooltip-bottom'
            },
            '.btn-zoom-out': {
                title: '🔍- Zoom Out',
                content: 'See the bigger picture - months or years.',
                position: 'tooltip-bottom'
            },
            '.btn-today': {
                title: '📍 Today',
                content: 'Jump to today\'s date on the timeline.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== JOURNEY PAGE ====================
    'journey': {
        cards: {
            '.journey-progress': '<strong>Your Journey:</strong> Track your progress through the eviction defense process.',
            '.stage-card': '<strong>Current Stage:</strong> What you should focus on right now.'
        },
        tooltips: {
            '.btn-next-step': {
                title: '➡️ Next Step',
                content: 'Move to the next stage in your journey.',
                when: 'Click when you\'ve completed the current stage.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== COURT LEARNING PAGE ====================
    'court_learning': {
        cards: {
            '.learning-modules': '<strong>Learning Modules:</strong> Educational content about court procedures and tenant rights.',
            '.stats-section': '<strong>Court Statistics:</strong> Historical data on eviction cases in your area.'
        },
        tooltips: {
            '.btn-start-lesson': {
                title: '📚 Start Lesson',
                content: 'Begin this learning module.',
                when: 'Take lessons to prepare for court.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== CONTACTS PAGE ====================
    'contacts': {
        cards: {
            '.contacts-list': '<strong>Your Contacts:</strong> People involved in your case - landlord, witnesses, lawyers, etc.',
            '.add-contact': '<strong>Add Contact:</strong> Record contact information for anyone relevant to your case.'
        },
        tooltips: {
            '.btn-add-contact': {
                title: '👤 Add Contact',
                content: 'Add a new person to your contacts.',
                when: 'Record landlords, witnesses, lawyers, inspectors, etc.',
                position: 'tooltip-bottom'
            },
            '.btn-star': {
                title: '⭐ Important',
                content: 'Mark this contact as important.',
                position: 'tooltip-right'
            }
        }
    },

    // ==================== LEGAL TRAILS PAGE ====================
    'legal_trails': {
        cards: {
            '.stats-section': '<strong>Research Statistics:</strong> Overview of your legal research activity and saved resources.',
            '.attorneys-section': '<strong>Attorney Directory:</strong> Find legal aid attorneys in your area who help with tenant cases.'
        },
        tooltips: {
            '.btn-search': {
                title: '🔍 Search',
                content: 'Search for legal resources and case law.',
                position: 'tooltip-bottom'
            },
            '.btn-save': {
                title: '💾 Save Resource',
                content: 'Save this legal resource to your trails for reference.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== FUNDING SEARCH PAGE ====================
    'funding_search': {
        cards: {
            '.search-section': '<strong>Search Funding:</strong> Find rental assistance programs, tax credits, and financial resources.',
            '.results-section': '<strong>Available Programs:</strong> Funding sources that match your criteria.'
        },
        tooltips: {
            '.btn-search': {
                title: '🔍 Search Programs',
                content: 'Find funding programs based on your location and situation.',
                position: 'tooltip-bottom'
            },
            '.btn-export': {
                title: '📥 Export Results',
                content: 'Download search results as a CSV file.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== INTAKE PAGE ====================
    'intake': {
        cards: {
            '.intake-form': '<strong>Complaint Intake:</strong> Enter information about your housing issue to create a case file.',
            '.category-section': '<strong>Issue Categories:</strong> Select all the problems you\'re experiencing.'
        },
        tooltips: {
            '.btn-submit': {
                title: '🚀 Create Case',
                content: 'Submit your information to start a new case.',
                when: 'Click after filling out all required fields.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== FOCUS PAGE ====================
    'focus': {
        cards: {
            '.focus-section': '<strong>Today\'s Focus:</strong> The most important task you should complete today.',
            '.progress-section': '<strong>Your Progress:</strong> How far you\'ve come in defending your rights.',
            '.next-steps': '<strong>Up Next:</strong> What to do after your current focus task.'
        },
        tooltips: {
            '.btn-done': {
                title: '✅ Mark Complete',
                content: 'Mark your focus task as done.',
                position: 'tooltip-bottom'
            },
            '.btn-skip': {
                title: '⏭️ Skip',
                content: 'Skip this task for now and see what else needs attention.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== DOCUMENT INTAKE PAGE (already has some) ====================
    // Note: 'document-intake' is defined at the top of this file

    // ==================== HOME PAGE ====================
    'home': {
        cards: {
            '.hero': '<strong>Welcome Home:</strong> Your personalized dashboard showing case status, upcoming deadlines, and quick access to all your tools.',
            '.quick-actions': '<strong>Quick Actions:</strong> One-click access to the most common tasks - upload documents, check deadlines, or get help.',
            '.deadlines-widget': '<strong>Upcoming Deadlines:</strong> Critical dates you need to act on. Red items are urgent!',
            '.case-status': '<strong>Case Status:</strong> Current status of your eviction case and what stage you\'re in.'
        },
        tooltips: {
            '.btn-upload': {
                title: '📤 Upload Document',
                content: 'Quickly add a new document to your case. Supports PDFs, images, and Word docs.',
                when: 'Click when you receive new legal papers from your landlord or the court.',
                position: 'tooltip-bottom'
            },
            '.btn-timeline': {
                title: '📅 Timeline',
                content: 'View all events in your case chronologically - from move-in to today.',
                when: 'Use to understand the full history and prepare for court.',
                position: 'tooltip-bottom'
            },
            '.btn-help': {
                title: '❓ Get Help',
                content: 'Access legal resources, templates, and step-by-step guides.',
                when: 'Click when you\'re unsure what to do next.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== WELCOME PAGE ====================
    'welcome': {
        cards: {
            '.header': '<strong>Welcome to Semptify:</strong> Your tenant\'s journal - a private, secure way to document your tenancy and protect your rights.',
            '.feature-section': '<strong>Key Features:</strong> Everything Semptify offers to help you organize documents, track communications, and build your case.',
            '.cta': '<strong>Get Started:</strong> Begin your journey to better tenant documentation.'
        },
        tooltips: {
            '.cta-button': {
                title: '🚀 Start Your Journal',
                content: 'Begin setting up your secure tenant documentation system. You control your data.',
                when: 'Click to create your account and connect your storage.',
                position: 'tooltip-top'
            }
        }
    },

    // ==================== RESEARCH MODULE PAGE ====================
    'research_module': {
        cards: {
            '.search-section': '<strong>Property Lookup:</strong> Search for any landlord or property to find violations, complaints, and history.',
            '.results-section': '<strong>Research Results:</strong> Violations, complaints, ownership history, and public records for the searched property.',
            '.risk-score': '<strong>Risk Score:</strong> An overall assessment of the landlord/property based on violation history and tenant complaints.'
        },
        tooltips: {
            '.btn-search': {
                title: '🔍 Search Property',
                content: 'Look up public records, violations, and complaints for any rental property.',
                when: 'Enter an address or landlord name and click to search.',
                position: 'tooltip-bottom'
            },
            '.btn-save': {
                title: '💾 Save to Case',
                content: 'Add this research to your case file as evidence.',
                when: 'Click after finding relevant violations or complaints.',
                position: 'tooltip-bottom'
            },
            '.btn-download': {
                title: '⬇️ Download Report',
                content: 'Export a PDF of the research findings for court or records.',
                when: 'Use when you need a printable copy of the research.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== COMPLETE JOURNEY PAGE ====================
    'complete_journey': {
        cards: {
            '.welcome-screen': '<strong>Welcome:</strong> Start your legal journey here - we\'ll guide you through every step.',
            '.onboarding-container': '<strong>Tell Us About Your Situation:</strong> Answer a few questions so we can personalize your experience.',
            '.main-app': '<strong>Your Journey:</strong> Follow the guided steps to build your case and protect your rights.'
        },
        tooltips: {
            '.start-btn': {
                title: '▶️ Begin Journey',
                content: 'Start the guided process to understand your situation and build your defense.',
                when: 'Click when you\'re ready to begin.',
                position: 'tooltip-bottom'
            },
            '.next-btn': {
                title: '➡️ Next Step',
                content: 'Continue to the next part of the journey.',
                when: 'Click after completing the current step.',
                position: 'tooltip-bottom'
            },
            '.save-btn': {
                title: '💾 Save Progress',
                content: 'Save your current progress. You can return later to continue.',
                when: 'Click before leaving if you want to pick up where you left off.',
                position: 'tooltip-bottom'
            }
        }
    },

    // ==================== PDF TOOLS PAGE ====================
    'pdf_tools': {
        cards: {
            '.sidebar': '<strong>Document List:</strong> All PDFs you\'ve uploaded. Click to view any document.',
            '.viewer-container': '<strong>Document Viewer:</strong> Read and annotate your documents. Navigate pages with arrow keys.',
            '.tools-panel': '<strong>PDF Tools:</strong> Extract pages, add notes, highlight text, and save evidence.'
        },
        tooltips: {
            '#addToListBtn': {
                title: '📋 Add to Evidence',
                content: 'Mark this page as evidence for your case. It will be saved and organized.',
                when: 'Click when you find an important page.',
                position: 'tooltip-left'
            },
            '#deletePageBtn': {
                title: '🗑️ Remove Page',
                content: 'Remove this page from your extracted evidence list.',
                when: 'Use to remove accidentally added pages.',
                position: 'tooltip-left'
            },
            '.zoom-in': {
                title: '🔍 Zoom In',
                content: 'Make the document larger to read small text.',
                position: 'tooltip-bottom'
            },
            '.zoom-out': {
                title: '🔍 Zoom Out',
                content: 'Make the document smaller to see more at once.',
                position: 'tooltip-bottom'
            },
            '#noteModal': {
                title: '📝 Add Note',
                content: 'Add your own notes to this page. Useful for remembering why this page matters.',
                when: 'Use to annotate important sections.',
                position: 'tooltip-left'
            }
        }
    }
};

console.log('✅ Semptify Help Content loaded');
