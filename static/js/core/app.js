/**
 * Semptify Core Application JavaScript
 * Shared functionality across all pages
 */

// ========================================
// VAULT PORTAL FUNCTIONS
// ========================================

function openVaultPortal() {
  const modal = document.getElementById('vault-portal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeVaultPortal() {
  const modal = document.getElementById('vault-portal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
    resetVaultForm();
  }
}

function resetVaultForm() {
  const fileList = document.getElementById('vault-file-list');
  const docType = document.getElementById('vault-doc-type');
  const description = document.getElementById('vault-description');
  const timestamp = document.getElementById('vault-timestamp');
  
  if (fileList) fileList.innerHTML = '';
  if (docType) docType.value = '';
  if (description) description.value = '';
  if (timestamp) timestamp.checked = false;
}

function uploadToVault() {
  const files = document.getElementById('vault-file-input')?.files;
  const docType = document.getElementById('vault-doc-type')?.value;
  const description = document.getElementById('vault-description')?.value;
  const addTimestamp = document.getElementById('vault-timestamp')?.checked;
  const portal = document.getElementById('vault-portal');

  let status = portal?.querySelector('.vault-upload-status');
  if (!status && portal) {
    status = document.createElement('div');
    status.className = 'vault-upload-status';
    status.style.cssText = 'padding:12px;margin:12px 0;border-radius:6px;font-size:0.9rem;display:none;';
    const content = portal.querySelector('.vault-portal-content, .modal-content, .modal-body');
    (content || portal).prepend(status);
  }
  const showStatus = (message, type) => {
    if (!status) return;
    status.textContent = message;
    status.style.display = 'block';
    status.style.background = type === 'error' ? '#fee2e2' : '#dcfce7';
    status.style.color = type === 'error' ? '#991b1b' : '#166534';
  };

  if (!files || files.length === 0) {
    showStatus('Please select files to upload.', 'error');
    return;
  }

  const userIdMatch = document.cookie.match(/(?:^|; )semptify_uid=([^;]+)/);
  const userId = userIdMatch ? decodeURIComponent(userIdMatch[1]) : null;

  const btn = document.querySelector('#vault-portal .btn--primary');
  const originalText = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Uploading...'; }

  const fetchFn = typeof window.fetchWithCSRF === 'function' ? window.fetchWithCSRF : fetch;
  const returnTo = encodeURIComponent(window.location.pathname);

  const runUpload = async () => {
    let uploadedCount = 0;
    const errors = [];
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_id', userId || '');
      formData.append('access_token', 'auto');
      if (docType) formData.append('document_type', docType);
      if (description) formData.append('description', description);
      if (addTimestamp) formData.append('tags', 'timestamped');

      try {
        const resp = await fetchFn('/api/intake/upload/auto', { method: 'POST', body: formData });
        const result = await resp.json().catch(() => ({}));

        if (resp.ok && result.status !== 'error' && result.vault_id) {
          uploadedCount++;
        } else if (
          resp.status === 401 ||
          result.error === 'token_expired' ||
          result.error === 'storage_required'
        ) {
          const redirect = result.redirect_url || `/storage/reconnect?return_to=${returnTo}`;
          if (confirm('Your storage connection expired. Reconnect now?')) {
            window.location.href = redirect;
          }
          return;
        } else {
          const msg = result.detail || result.message || result.error || `Upload failed (HTTP ${resp.status})`;
          errors.push(`${file.name}: ${msg}`);
        }
      } catch (e) {
        errors.push(`${file.name}: ${e.message}`);
      }
    }

    if (uploadedCount > 0) {
      window.dispatchEvent(new CustomEvent('vault:uploaded', {
        detail: { fileCount: uploadedCount, timestamp: new Date().toISOString() }
      }));
      showStatus(`${uploadedCount} file(s) uploaded successfully.`, 'success');
      setTimeout(() => {
        closeVaultPortal();
        if (typeof refreshVaultFileList === 'function') refreshVaultFileList();
        window.location.reload();
      }, 1500);
    }

    if (errors.length > 0) {
      showStatus('Upload failed: ' + errors.join('; '), 'error');
    }
  };

  runUpload().finally(() => {
    if (btn) { btn.disabled = false; btn.textContent = originalText; }
  });
}

// ========================================
// VAULT EVENT LISTENERS
// ========================================

document.addEventListener('DOMContentLoaded', function() {
  // Vault dropzone
  const dropzone = document.getElementById('vault-dropzone');
  const fileInput = document.getElementById('vault-file-input');
  
  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());
    
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      handleVaultFiles(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', (e) => {
      handleVaultFiles(e.target.files);
    });
  }
  
  // Escape key closes modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeVaultPortal();
  });
});

function handleVaultFiles(files) {
  const fileList = document.getElementById('vault-file-list');
  if (!fileList) return;
  
  Array.from(files).forEach(file => {
    const item = document.createElement('div');
    item.className = 'vault-file-item';
    item.innerHTML = `
      <span>📄</span>
      <div style="flex: 1;">
        <div style="font-weight: 500;">${file.name}</div>
        <div style="font-size: 0.8rem; color: #9ca3af;">${(file.size/1024/1024).toFixed(2)} MB</div>
      </div>
      <button onclick="this.parentElement.remove()" style="background: none; border: none; cursor: pointer;">✕</button>
    `;
    fileList.appendChild(item);
  });
}

// ========================================
// DEVICE DETECTION
// ========================================

function detectDevice() {
  const width = window.innerWidth;
  
  if (width < 481) return 'mobile';
  if (width < 769) return 'tablet';
  if (width < 1201) return 'desktop';
  if (width < 1601) return 'large-desktop';
  return 'tv';
}

function applyDeviceClass() {
  const device = detectDevice();
  document.body.setAttribute('data-device', device);
}

// ========================================
// MOBILE NAVIGATION
// ========================================

function toggleMobileNav() {
  const nav = document.querySelector('.mobile-nav');
  if (nav) {
    nav.classList.toggle('active');
  }
}

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', function() {
  applyDeviceClass();
  
  window.addEventListener('resize', () => {
    applyDeviceClass();
  });
});

// ========================================
// UTILITY FUNCTIONS
// ========================================

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(new Date(date));
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
}

console.log('Semptify Core App Loaded');
