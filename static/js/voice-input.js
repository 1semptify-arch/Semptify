/**
 * 🎤 Voice Input System for Semptify
 * Accessibility feature - speak instead of type
 * 
 * Usage:
 *   1. Click microphone button
 *   2. Speak your text
 *   3. Auto-fills the input field
 */

class VoiceInput {
  constructor() {
    this.recognition = null;
    this.isListening = false;
    this.currentTarget = null;
    this.supported = this.checkSupport();
    
    if (this.supported) {
      this.init();
    }
  }

  checkSupport() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }

  init() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    
    // Configuration
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';
    this.recognition.maxAlternatives = 1;

    // Event handlers
    this.recognition.onstart = () => this.onStart();
    this.recognition.onend = () => this.onEnd();
    this.recognition.onresult = (e) => this.onResult(e);
    this.recognition.onerror = (e) => this.onError(e);

    // Auto-add voice buttons to inputs
    this.enhanceInputs();
    
    // Watch for new inputs (dynamic content)
    this.observeDOM();

    console.log('🎤 Voice input ready');
  }

  enhanceInputs() {
    // Find all text inputs and textareas that don't have voice buttons yet
    const inputs = document.querySelectorAll(
      'input[type="text"]:not([data-voice-enhanced]), ' +
      'input[type="search"]:not([data-voice-enhanced]), ' +
      'input:not([type]):not([data-voice-enhanced]), ' +
      'textarea:not([data-voice-enhanced])'
    );

    inputs.forEach(input => this.addVoiceButton(input));
  }

  addVoiceButton(input) {
    // Skip hidden, disabled, or already enhanced inputs
    if (input.type === 'hidden' || input.disabled || input.dataset.voiceEnhanced) {
      return;
    }

    // Mark as enhanced
    input.dataset.voiceEnhanced = 'true';

    // Create wrapper if needed
    let wrapper = input.parentElement;
    if (!wrapper.classList.contains('voice-input-wrapper')) {
      wrapper = document.createElement('div');
      wrapper.className = 'voice-input-wrapper';
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
    }

    // Create voice button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'voice-btn';
    btn.setAttribute('aria-label', 'Voice input');
    btn.setAttribute('title', 'Click to speak');
    btn.innerHTML = '<i class="fas fa-microphone"></i>';
    
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.toggleListening(input, btn);
    });

    wrapper.appendChild(btn);
  }

  toggleListening(input, btn) {
    if (this.isListening) {
      this.stop();
    } else {
      this.start(input, btn);
    }
  }

  start(input, btn) {
    if (!this.supported) {
      this.showNotSupported();
      return;
    }

    this.currentTarget = input;
    this.currentButton = btn;
    
    try {
      this.recognition.start();
    } catch (e) {
      // Already started
      console.log('Recognition already active');
    }
  }

  stop() {
    if (this.recognition) {
      this.recognition.stop();
    }
  }

  onStart() {
    this.isListening = true;
    
    if (this.currentButton) {
      this.currentButton.classList.add('listening');
      this.currentButton.innerHTML = '<i class="fas fa-circle voice-pulse"></i>';
    }
    
    if (this.currentTarget) {
      this.currentTarget.classList.add('voice-active');
      this.currentTarget.placeholder = '🎤 Listening...';
    }

    this.showToast('🎤 Listening... Speak now', 'info');
  }

  onEnd() {
    this.isListening = false;
    
    if (this.currentButton) {
      this.currentButton.classList.remove('listening');
      this.currentButton.innerHTML = '<i class="fas fa-microphone"></i>';
    }
    
    if (this.currentTarget) {
      this.currentTarget.classList.remove('voice-active');
      this.currentTarget.placeholder = this.currentTarget.dataset.originalPlaceholder || '';
    }
  }

  onResult(event) {
    let finalTranscript = '';
    let interimTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    if (this.currentTarget) {
      // Store original placeholder
      if (!this.currentTarget.dataset.originalPlaceholder) {
        this.currentTarget.dataset.originalPlaceholder = this.currentTarget.placeholder;
      }

      if (finalTranscript) {
        // Append to existing value or replace
        const existingValue = this.currentTarget.value;
        if (existingValue && !existingValue.endsWith(' ')) {
          this.currentTarget.value = existingValue + ' ' + finalTranscript;
        } else {
          this.currentTarget.value = existingValue + finalTranscript;
        }
        
        // Trigger input event for frameworks
        this.currentTarget.dispatchEvent(new Event('input', { bubbles: true }));
        this.currentTarget.dispatchEvent(new Event('change', { bubbles: true }));
        
        this.showToast('✅ Got it!', 'success');
      } else if (interimTranscript) {
        // Show interim in placeholder
        this.currentTarget.placeholder = '🎤 ' + interimTranscript + '...';
      }
    }
  }

  onError(event) {
    this.isListening = false;
    
    let message = 'Voice input error';
    
    switch (event.error) {
      case 'no-speech':
        message = "Didn't hear anything. Try again?";
        break;
      case 'audio-capture':
        message = 'No microphone found';
        break;
      case 'not-allowed':
        message = 'Microphone access denied. Check browser settings.';
        break;
      case 'network':
        message = 'Network error. Check connection.';
        break;
      default:
        message = `Error: ${event.error}`;
    }

    this.showToast('❌ ' + message, 'error');
    this.onEnd();
  }

  showNotSupported() {
    this.showToast('Voice input not supported in this browser. Try Chrome or Edge.', 'warning');
  }

  showToast(message, type = 'info') {
    // Use existing toast system if available
    if (window.showToast) {
      window.showToast(message, type);
      return;
    }

    // Fallback toast
    let container = document.getElementById('voice-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'voice-toast-container';
      container.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
      `;
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `voice-toast voice-toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  observeDOM() {
    // Watch for dynamically added inputs
    const observer = new MutationObserver((mutations) => {
      let hasNewInputs = false;
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === 1) {
            if (node.matches?.('input, textarea') || node.querySelector?.('input, textarea')) {
              hasNewInputs = true;
            }
          }
        });
      });
      
      if (hasNewInputs) {
        setTimeout(() => this.enhanceInputs(), 100);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Global voice command (press and hold spacebar)
  enableGlobalHotkey() {
    let spaceHeld = false;
    
    document.addEventListener('keydown', (e) => {
      // Spacebar held while not in input
      if (e.code === 'Space' && !spaceHeld && !this.isInputFocused()) {
        e.preventDefault();
        spaceHeld = true;
        
        // Find first visible input
        const input = document.querySelector('input:not([type="hidden"]), textarea');
        if (input) {
          input.focus();
          const btn = input.parentElement?.querySelector('.voice-btn');
          if (btn) {
            this.start(input, btn);
          }
        }
      }
    });

    document.addEventListener('keyup', (e) => {
      if (e.code === 'Space' && spaceHeld) {
        spaceHeld = false;
        this.stop();
      }
    });
  }

  isInputFocused() {
    const active = document.activeElement;
    return active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
  }
}

// CSS Styles for voice input
const voiceStyles = document.createElement('style');
voiceStyles.textContent = `
  .voice-input-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
    width: 100%;
  }

  .voice-input-wrapper input,
  .voice-input-wrapper textarea {
    padding-right: 44px !important;
    width: 100%;
  }

  .voice-btn {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: var(--surface-secondary, #f1f5f9);
    color: var(--text-secondary, #64748b);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: all 0.2s ease;
    z-index: 5;
  }

  .voice-btn:hover {
    background: var(--primary-light, #dbeafe);
    color: var(--primary, #3b82f6);
    transform: translateY(-50%) scale(1.1);
  }

  .voice-btn.listening {
    background: var(--danger, #ef4444);
    color: white;
    animation: voice-glow 1.5s ease-in-out infinite;
  }

  @keyframes voice-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
    50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  }

  .voice-pulse {
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .voice-active {
    border-color: var(--danger, #ef4444) !important;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
  }

  /* Toast styles */
  .voice-toast {
    padding: 12px 20px;
    border-radius: 10px;
    background: var(--surface-primary, white);
    color: var(--text-primary, #1e293b);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    font-size: 14px;
    font-weight: 500;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.3s ease;
    margin-top: 8px;
  }

  .voice-toast.show {
    opacity: 1;
    transform: translateY(0);
  }

  .voice-toast-success { border-left: 4px solid #22c55e; }
  .voice-toast-error { border-left: 4px solid #ef4444; }
  .voice-toast-warning { border-left: 4px solid #f59e0b; }
  .voice-toast-info { border-left: 4px solid #3b82f6; }

  /* Floating voice button for pages */
  .floating-voice-btn {
    position: fixed;
    bottom: 100px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: none;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: white;
    font-size: 1.25rem;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
    z-index: 1000;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .floating-voice-btn:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 30px rgba(59, 130, 246, 0.5);
  }

  .floating-voice-btn.listening {
    background: linear-gradient(135deg, #ef4444, #f97316);
    animation: voice-glow 1.5s ease-in-out infinite;
  }

  /* Mobile adjustments */
  @media (max-width: 768px) {
    .voice-btn {
      width: 36px;
      height: 36px;
      font-size: 16px;
    }

    .floating-voice-btn {
      bottom: 80px;
      right: 16px;
      width: 50px;
      height: 50px;
    }
  }
`;
document.head.appendChild(voiceStyles);

// Initialize when DOM ready
let voiceInput;
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    voiceInput = new VoiceInput();
  });
} else {
  voiceInput = new VoiceInput();
}

// Export for use
window.VoiceInput = VoiceInput;
window.voiceInput = voiceInput;
