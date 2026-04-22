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
  // TODO: Implement actual upload to backend
  // This will send to user's connected cloud storage
  console.log('Vault upload initiated...');
  
  const files = document.getElementById('vault-file-input')?.files;
  const docType = document.getElementById('vault-doc-type')?.value;
  const description = document.getElementById('vault-description')?.value;
  const addTimestamp = document.getElementById('vault-timestamp')?.checked;
  
  if (!files || files.length === 0) {
    alert('Please select files to upload');
    return;
  }
  
  // Simulate upload
  const formData = new FormData();
  Array.from(files).forEach(file => formData.append('files', file));
  if (docType) formData.append('documentType', docType);
  if (description) formData.append('description', description);
  if (addTimestamp) formData.append('timestamp', 'true');
  
  // TODO: fetch('/api/vault/upload', { method: 'POST', body: formData })
  
  alert(`${files.length} file(s) queued for upload to your vault`);
  closeVaultPortal();
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
