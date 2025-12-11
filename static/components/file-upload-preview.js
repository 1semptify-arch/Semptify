/**
 * Semptify Universal File Upload Preview
 * 
 * Auto-attaches to ALL file inputs site-wide.
 * Provides preview, rename, and skip functionality.
 * 
 * Include this script on any page:
 * <script src="/static/components/file-upload-preview.js"></script>
 */

(function() {
    'use strict';

    // Styles for the preview modal
    const styles = `
        .semptify-preview-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }
        
        .semptify-preview-overlay.active {
            opacity: 1;
            visibility: visible;
        }
        
        .semptify-preview-modal {
            background: white;
            border-radius: 16px;
            max-width: 500px;
            width: 90%;
            max-height: 85vh;
            overflow: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            transform: scale(0.9);
            transition: transform 0.3s ease;
        }
        
        .semptify-preview-overlay.active .semptify-preview-modal {
            transform: scale(1);
        }
        
        .semptify-preview-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .semptify-preview-header h3 {
            margin: 0;
            font-size: 1.1rem;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .semptify-preview-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #94a3b8;
            padding: 0;
            line-height: 1;
        }
        
        .semptify-preview-close:hover {
            color: #64748b;
        }
        
        .semptify-preview-body {
            padding: 1.5rem;
        }
        
        .semptify-file-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .semptify-file-item {
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
        
        .semptify-file-thumb {
            width: 80px;
            height: 80px;
            border-radius: 8px;
            overflow: hidden;
            background: #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        
        .semptify-file-thumb img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .semptify-file-thumb .icon {
            font-size: 2.5rem;
        }
        
        .semptify-file-info {
            flex: 1;
            min-width: 0;
        }
        
        .semptify-file-name-input {
            width: 100%;
            padding: 0.5rem 0.75rem;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            transition: border-color 0.2s;
        }
        
        .semptify-file-name-input:focus {
            outline: none;
            border-color: #3b82f6;
        }
        
        .semptify-file-meta {
            display: flex;
            gap: 1rem;
            font-size: 0.8rem;
            color: #64748b;
        }
        
        .semptify-file-remove {
            background: #fee2e2;
            color: #dc2626;
            border: none;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1rem;
            flex-shrink: 0;
            align-self: flex-start;
        }
        
        .semptify-file-remove:hover {
            background: #fecaca;
        }
        
        .semptify-preview-footer {
            padding: 1rem 1.5rem;
            border-top: 1px solid #e2e8f0;
            display: flex;
            gap: 0.75rem;
            background: #f8fafc;
            border-radius: 0 0 16px 16px;
        }
        
        .semptify-btn {
            padding: 0.75rem 1.25rem;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .semptify-btn-skip {
            background: #f1f5f9;
            color: #64748b;
            flex: 1;
        }
        
        .semptify-btn-skip:hover {
            background: #e2e8f0;
        }
        
        .semptify-btn-upload {
            background: #3b82f6;
            color: white;
            flex: 2;
        }
        
        .semptify-btn-upload:hover {
            background: #2563eb;
        }
        
        .semptify-btn-cancel {
            background: white;
            color: #64748b;
            border: 1px solid #e2e8f0;
        }
        
        .semptify-btn-cancel:hover {
            background: #f8fafc;
        }
        
        .semptify-empty-state {
            text-align: center;
            padding: 2rem;
            color: #94a3b8;
        }
        
        @media (max-width: 500px) {
            .semptify-preview-modal {
                width: 95%;
                margin: 1rem;
            }
            
            .semptify-file-item {
                flex-direction: column;
            }
            
            .semptify-file-thumb {
                width: 100%;
                height: 120px;
            }
            
            .semptify-preview-footer {
                flex-direction: column;
            }
        }
    `;

    // Inject styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);

    // Create modal HTML
    const modalHTML = `
        <div class="semptify-preview-overlay" id="semptifyPreviewOverlay">
            <div class="semptify-preview-modal">
                <div class="semptify-preview-header">
                    <h3>📎 Preview Files</h3>
                    <button class="semptify-preview-close" onclick="SemptifyUpload.close()">&times;</button>
                </div>
                <div class="semptify-preview-body">
                    <div class="semptify-file-list" id="semptifyFileList"></div>
                </div>
                <div class="semptify-preview-footer">
                    <button class="semptify-btn semptify-btn-cancel" onclick="SemptifyUpload.close()">✕ Cancel</button>
                    <button class="semptify-btn semptify-btn-skip" onclick="SemptifyUpload.skipAndUpload()">⏩ Skip</button>
                    <button class="semptify-btn semptify-btn-upload" onclick="SemptifyUpload.confirmAndUpload()">📤 Upload</button>
                </div>
            </div>
        </div>
    `;

    // State
    let currentFiles = [];
    let currentInput = null;
    let originalCallback = null;

    // File type icons
    const fileIcons = {
        'pdf': '📕',
        'doc': '📘',
        'docx': '📘',
        'xls': '📊',
        'xlsx': '📊',
        'txt': '📝',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️',
        'gif': '🖼️',
        'webp': '🖼️',
        'default': '📄'
    };

    // Format file size
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // Get file extension
    function getExt(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    // Get icon for file type
    function getIcon(filename) {
        const ext = getExt(filename);
        return fileIcons[ext] || fileIcons.default;
    }

    // Render file list
    function renderFiles() {
        const list = document.getElementById('semptifyFileList');
        
        if (currentFiles.length === 0) {
            list.innerHTML = '<div class="semptify-empty-state">No files selected</div>';
            return;
        }
        
        list.innerHTML = currentFiles.map((fileData, index) => {
            const file = fileData.file;
            const ext = getExt(file.name);
            const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
            
            return `
                <div class="semptify-file-item" data-index="${index}">
                    <div class="semptify-file-thumb" id="thumb-${index}">
                        ${isImage ? '' : `<span class="icon">${getIcon(file.name)}</span>`}
                    </div>
                    <div class="semptify-file-info">
                        <input type="text" 
                               class="semptify-file-name-input" 
                               value="${nameWithoutExt}"
                               data-index="${index}"
                               data-ext="${ext}"
                               placeholder="File name">
                        <div class="semptify-file-meta">
                            <span>${formatSize(file.size)}</span>
                            <span>${ext.toUpperCase()}</span>
                        </div>
                    </div>
                    <button class="semptify-file-remove" onclick="SemptifyUpload.removeFile(${index})">✕</button>
                </div>
            `;
        }).join('');
        
        // Load image thumbnails
        currentFiles.forEach((fileData, index) => {
            const file = fileData.file;
            const ext = getExt(file.name);
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const thumb = document.getElementById(`thumb-${index}`);
                    if (thumb) {
                        thumb.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Public API
    window.SemptifyUpload = {
        // Initialize - call on DOM ready
        init: function() {
            // Inject modal if not exists
            if (!document.getElementById('semptifyPreviewOverlay')) {
                const div = document.createElement('div');
                div.innerHTML = modalHTML;
                document.body.appendChild(div.firstElementChild);
            }
            
            // Attach to all file inputs
            this.attachToInputs();
            
            // Watch for dynamically added inputs
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {
                            if (node.matches && node.matches('input[type="file"]')) {
                                this.attachToInput(node);
                            }
                            const inputs = node.querySelectorAll ? node.querySelectorAll('input[type="file"]') : [];
                            inputs.forEach(input => this.attachToInput(input));
                        }
                    });
                });
            });
            
            observer.observe(document.body, { childList: true, subtree: true });
            
            // Close on overlay click
            document.getElementById('semptifyPreviewOverlay').addEventListener('click', (e) => {
                if (e.target.id === 'semptifyPreviewOverlay') {
                    this.close();
                }
            });
            
            // Close on Escape
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.close();
                }
            });
        },
        
        // Attach to all current file inputs
        attachToInputs: function() {
            document.querySelectorAll('input[type="file"]').forEach(input => {
                this.attachToInput(input);
            });
        },
        
        // Attach to a single input
        attachToInput: function(input) {
            // Skip if already attached
            if (input.dataset.semptifyAttached) return;
            input.dataset.semptifyAttached = 'true';
            
            // Store original onchange if exists
            const originalOnchange = input.onchange;
            
            // Override change handler
            input.addEventListener('change', (e) => {
                e.stopPropagation();
                
                const files = Array.from(e.target.files);
                if (files.length === 0) return;
                
                // Store state
                currentFiles = files.map(f => ({ file: f, newName: f.name }));
                currentInput = input;
                originalCallback = originalOnchange;
                
                // Show preview modal
                this.open();
            });
            
            // Clear the native onchange to prevent double-firing
            input.onchange = null;
        },
        
        // Open the preview modal
        open: function() {
            renderFiles();
            document.getElementById('semptifyPreviewOverlay').classList.add('active');
            document.body.style.overflow = 'hidden';
        },
        
        // Close the preview modal
        close: function() {
            document.getElementById('semptifyPreviewOverlay').classList.remove('active');
            document.body.style.overflow = '';
            
            // Clear the input if cancelled
            if (currentInput) {
                currentInput.value = '';
            }
            
            currentFiles = [];
            currentInput = null;
            originalCallback = null;
        },
        
        // Remove a file from the list
        removeFile: function(index) {
            currentFiles.splice(index, 1);
            renderFiles();
            
            if (currentFiles.length === 0) {
                this.close();
            }
        },
        
        // Skip preview and upload with original names
        skipAndUpload: function() {
            this.processUpload(false);
        },
        
        // Confirm renames and upload
        confirmAndUpload: function() {
            this.processUpload(true);
        },
        
        // Process the upload
        processUpload: function(useRenamedNames) {
            // Gather file data
            const processedFiles = [];
            
            document.querySelectorAll('.semptify-file-name-input').forEach((input, index) => {
                if (currentFiles[index]) {
                    const file = currentFiles[index].file;
                    const ext = input.dataset.ext;
                    const newName = useRenamedNames 
                        ? (input.value.trim() || 'document') + '.' + ext
                        : file.name;
                    
                    // Create renamed file
                    const renamedFile = new File([file], newName, { type: file.type });
                    processedFiles.push(renamedFile);
                }
            });
            
            // Create a new FileList-like object
            const dataTransfer = new DataTransfer();
            processedFiles.forEach(f => dataTransfer.items.add(f));
            
            // Set the files on the input
            if (currentInput) {
                currentInput.files = dataTransfer.files;
                
                // Trigger any existing handlers
                if (originalCallback) {
                    originalCallback.call(currentInput, { target: currentInput });
                }
                
                // Dispatch change event for other listeners
                currentInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Also dispatch a custom event with the processed files
                currentInput.dispatchEvent(new CustomEvent('semptify:upload', {
                    bubbles: true,
                    detail: { files: processedFiles, renamed: useRenamedNames }
                }));
            }
            
            // Close modal
            document.getElementById('semptifyPreviewOverlay').classList.remove('active');
            document.body.style.overflow = '';
            
            currentFiles = [];
            currentInput = null;
            originalCallback = null;
        },
        
        // Disable for a specific input (opt-out)
        disable: function(input) {
            input.dataset.semptifyDisabled = 'true';
        }
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => SemptifyUpload.init());
    } else {
        SemptifyUpload.init();
    }

})();
