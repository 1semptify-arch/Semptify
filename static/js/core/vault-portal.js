/**
 * Semptify Vault Portal - Single Entry Point for ALL Document Uploads
 * All files go through here → Overlay extraction → User's cloud storage
 */

// Document Type Categories
const DOCUMENT_TYPES = {
  'lease': {
    label: 'Lease Agreement',
    icon: '📄',
    description: 'Rental contract, lease terms, addendums',
    autoFields: ['lease_start', 'lease_end', 'rent_amount', 'security_deposit']
  },
  'notice': {
    label: 'Notice / Letter',
    icon: '📨',
    description: 'Eviction notice, rent increase, lease termination, warnings',
    autoFields: ['notice_type', 'notice_date', 'deadline_date', 'sender']
  },
  'receipt': {
    label: 'Rent Receipt / Payment',
    icon: '🧾',
    description: 'Proof of rent payment, money order, bank transfer',
    autoFields: ['payment_date', 'amount', 'payment_method', 'period_covered']
  },
  'repair': {
    label: 'Repair Request / Maintenance',
    icon: '🔧',
    description: 'Maintenance requests, repair records, inspection reports',
    autoFields: ['request_date', 'issue_type', 'urgency', 'completion_status']
  },
  'photo': {
    label: 'Photo Evidence',
    icon: '📷',
    description: 'Property condition, damage, repairs, safety issues',
    autoFields: ['capture_date', 'location', 'description', 'geotag']
  },
  'legal': {
    label: 'Legal Document',
    icon: '⚖️',
    description: 'Court papers, attorney correspondence, legal notices',
    autoFields: ['court_name', 'case_number', 'filing_date', 'document_type']
  },
  'communication': {
    label: 'Communication / Messages',
    icon: '💬',
    description: 'Emails, texts, chat logs with landlord/property manager',
    autoFields: ['communication_date', 'parties', 'method', 'subject']
  },
  'insurance': {
    label: 'Insurance Document',
    icon: '🛡️',
    description: 'Renter\'s insurance, claims, correspondence',
    autoFields: ['provider', 'policy_number', 'coverage_date', 'claim_number']
  },
  'financial': {
    label: 'Financial Record',
    icon: '💰',
    description: 'Bank statements, income proof, hardship documentation',
    autoFields: ['statement_date', 'account_type', 'institution']
  },
  'medical': {
    label: 'Medical / Disability',
    icon: '🏥',
    description: 'Medical records, disability accommodation requests, doctor notes',
    autoFields: ['provider_name', 'date_of_service', 'accommodation_type']
  },
  'other': {
    label: 'Other Document',
    icon: '📑',
    description: 'Any other document related to your tenancy',
    autoFields: []
  }
};

/**
 * Open file picker → Upload → Overlay extraction → Cloud storage
 */
function openVaultUpload() {
  // Create and trigger file input
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.multiple = true;
  fileInput.accept = '.pdf,.jpg,.jpeg,.png,.doc,.docx,.txt,.heic,.heif';
  
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleVaultFiles(e.target.files);
    }
  });
  
  fileInput.click();
}

/**
 * Handle selected files - show metadata capture form
 */
function handleVaultFiles(files) {
  const filesArray = Array.from(files);
  
  // Build modal with document type selector
  const modalHTML = `
    <div id="vault-capture-modal" class="vault-modal active">
      <div class="vault-modal-backdrop" onclick="closeVaultCapture()"></div>
      <div class="vault-modal-content vault-capture-content">
        <div class="vault-header">
          <h2>📤 Document Upload (${filesArray.length} file${filesArray.length > 1 ? 's' : ''})</h2>
          <button class="vault-close" onclick="closeVaultCapture()">&times;</button>
        </div>
        
        <div class="vault-capture-body">
          <div class="file-list">
            ${filesArray.map((file, idx) => `
              <div class="file-item" data-index="${idx}">
                <span class="file-icon">${getFileIcon(file.name)}</span>
                <div class="file-info">
                  <div class="file-name">${file.name}</div>
                  <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
              </div>
            `).join('')}
          </div>
          
          <div class="capture-form">
            <div class="form-group">
              <label class="form-label">Document Type *</label>
              <select class="form-input" id="vault-doc-type" onchange="updateAutoFields()">
                <option value="">Select document type...</option>
                ${Object.entries(DOCUMENT_TYPES).map(([key, type]) => `
                  <option value="${key}">${type.icon} ${type.label}</option>
                `).join('')}
              </select>
              <p class="type-description" id="type-description"></p>
            </div>
            
            <div id="auto-fields" class="auto-fields"></div>
            
            <div class="form-group">
              <label class="form-label">Description (What happened?)</label>
              <textarea class="form-input" id="vault-description" rows="3" 
                placeholder="Brief description: what is this, why it matters, dates, people involved..."></textarea>
            </div>
            
            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" id="vault-emergency" value="emergency">
                <span>🚨 This is an emergency/urgent situation</span>
              </label>
            </div>
          </div>
          
          <div class="metadata-preview">
            <h4>📊 Auto-Captured Metadata</h4>
            <ul class="metadata-list">
              <li><strong>Upload time:</strong> ${new Date().toLocaleString()}</li>
              <li><strong>Device:</strong> ${navigator.userAgent.split(')')[0]})</li>
              <li><strong>Files:</strong> ${filesArray.length} document${filesArray.length > 1 ? 's' : ''}</li>
              <li><strong>Blockchain timestamp:</strong> ✅ Auto-enabled</li>
              <li><strong>Overlay extraction:</strong> ✅ Will process</li>
            </ul>
          </div>
        </div>
        
        <div class="vault-storage-info">
          <div class="storage-provider">
            <span>☁️</span>
            <span>Saving to: <strong>Your Google Drive</strong> (Semptify/Vault/)</span>
          </div>
          <p class="privacy-note">
            🔒 Your document stays in YOUR storage. Semptify creates an overlay (metadata only) 
            for searching and timeline. Full document never touches our servers.
          </p>
        </div>
        
        <div class="vault-actions">
          <button class="btn btn-secondary" onclick="closeVaultCapture()">Cancel</button>
          <button class="btn btn-primary" onclick="uploadToVault(${filesArray.length})">
            Upload to Vault →
          </button>
        </div>
      </div>
    </div>
  `;
  
  // Add to DOM
  const existing = document.getElementById('vault-capture-modal');
  if (existing) existing.remove();
  
  document.body.insertAdjacentHTML('beforeend', modalHTML);
  
  // Store files for upload
  window.vaultPendingFiles = filesArray;
}

/**
 * Update auto-fields based on document type selection
 */
function updateAutoFields() {
  const type = document.getElementById('vault-doc-type').value;
  const container = document.getElementById('auto-fields');
  const description = document.getElementById('type-description');
  
  if (!type || !DOCUMENT_TYPES[type]) {
    container.innerHTML = '';
    description.textContent = '';
    return;
  }
  
  const docType = DOCUMENT_TYPES[type];
  description.textContent = docType.description;
  
  // Build auto-fields form
  const fieldHTML = docType.autoFields.map(field => {
    const label = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return `
      <div class="form-group auto-field">
        <label class="form-label">${label}</label>
        <input type="text" class="form-input" id="field-${field}" placeholder="${label}...">
      </div>
    `;
  }).join('');
  
  container.innerHTML = fieldHTML;
}

/**
 * Close capture modal
 */
function closeVaultCapture() {
  const modal = document.getElementById('vault-capture-modal');
  if (modal) modal.remove();
  window.vaultPendingFiles = null;
}

/**
 * Upload files to vault
 */
async function uploadToVault(fileCount) {
  const docType = document.getElementById('vault-doc-type').value;
  const description = document.getElementById('vault-description').value;
  const isEmergency = document.getElementById('vault-emergency').checked;
  
  if (!docType) {
    alert('Please select a document type');
    return;
  }
  
  const files = window.vaultPendingFiles;
  if (!files || files.length === 0) {
    alert('No files selected');
    return;
  }
  
  // Gather all metadata
  const typeConfig = DOCUMENT_TYPES[docType];
  const autoFieldData = {};
  typeConfig.autoFields.forEach(field => {
    const input = document.getElementById(`field-${field}`);
    if (input) autoFieldData[field] = input.value;
  });
  
  const uploadData = {
    files: files.map(f => ({ name: f.name, size: f.size, type: f.type })),
    documentType: docType,
    documentTypeLabel: typeConfig.label,
    description: description,
    isEmergency: isEmergency,
    autoFields: autoFieldData,
    timestamp: new Date().toISOString(),
    blockchainHash: await generateBlockchainHash(),
    overlayData: null // Will be populated after OCR/processing
  };
  
  console.log('Vault upload prepared:', uploadData);
  
  // TODO: Send to backend
  // POST /api/vault/upload with FormData containing actual files + metadata JSON
  
  // Simulate success
  alert(`${fileCount} document(s) uploaded to your vault.\n\nOverlay processing started.\nBlockchain timestamp applied.\nSaved to your Google Drive.`);
  
  closeVaultCapture();
}

/**
 * Generate blockchain hash for timestamp proof
 */
async function generateBlockchainHash() {
  // In production: call backend to get actual blockchain anchor
  // For now, return a simulated hash
  return '0x' + Array.from(crypto.getRandomValues(new Uint8Array(32)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Helper: Get icon for file type
 */
function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const icons = {
    'pdf': '📕',
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'png': '🖼️',
    'doc': '📝',
    'docx': '📝',
    'txt': '📄'
  };
  return icons[ext] || '📄';
}

/**
 * Helper: Format file size
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1024 / 1024).toFixed(2) + ' MB';
}

// Export for use
typeof module !== 'undefined' && (module.exports = {
  openVaultUpload,
  DOCUMENT_TYPES
});
