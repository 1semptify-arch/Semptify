"""
Offline Manager - Network Connectivity Detection
===========================================

Handles offline/online state detection and user notifications.
"""

import logging
from typing import Optional, Callable
from fastapi import Request

logger = logging.getLogger(__name__)

class OfflineManager:
    """Manages offline/online state detection and user notifications."""
    
    def __init__(self):
        self.is_online = True
        self.callbacks = {
            'online': [],
            'offline': [],
            'reconnect': []
        }
        self.check_interval = 30000  # 30 seconds
        self.max_retries = 3
        self.retry_count = 0
        
    def add_callback(self, event_type: str, callback: Callable):
        """Add callback for offline/online events."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def remove_callback(self, event_type: str, callback: Callable):
        """Remove callback for offline/online events."""
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    def _trigger_callbacks(self, event_type: str, data: dict = None):
        """Trigger all callbacks for an event type."""
        for callback in self.callbacks.get(event_type, []):
            try:
                if data:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                logger.error(f"Offline callback error: {e}")
    
    def check_connectivity(self) -> bool:
        """Check if we have network connectivity."""
        try:
            # Simple connectivity check - try to reach a reliable endpoint
            import httpx
            with httpx.Client(timeout=5) as client:
                response = client.get("https://httpbin.org/get", timeout=5)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Connectivity check failed: {e}")
            return False
    
    def get_offline_html(self) -> str:
        """Generate HTML for offline indicator."""
        return """
        <div id="offline_indicator" style="
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ef4444;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: none;
            animation: slideDown 0.3s ease;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 1l6 6m0 0l-6 6m0 0"/>
                    <circle cx="12" cy="12" r="10"/>
                </svg>
                <span>No Internet Connection</span>
            </div>
            <button onclick="this.parentElement.style.display='none'" style="
                background: none;
                border: 1px solid white;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                margin-left: 12px;
            ">✕</button>
        </div>
        
        <style>
        @keyframes slideDown {
            from {
                transform: translateX(-50%) translateY(-20px);
                opacity: 0;
            }
            to {
                transform: translateX(-50%) translateY(0);
                opacity: 1;
            }
        }
        </style>
        """
    
    def get_online_html(self) -> str:
        """Generate HTML for online indicator."""
        return """
        <div id="online_indicator" style="
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #10b981;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: none;
            animation: slideDown 0.3s ease;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M5 12l5 5m0 0l-5 5m0 0"/>
                    <polyline points="12 7 12 17 7"/>
                </svg>
                <span>Connection Restored</span>
            </div>
        </div>
        """
    
    def get_javascript(self) -> str:
        """Generate JavaScript for offline detection."""
        return """
        <script>
        (function() {
            let isOnline = navigator.onLine;
            let offlineIndicator = null;
            let onlineIndicator = null;
            let checkInterval = null;
            let retryCount = 0;
            const maxRetries = 3;
            
            function createIndicators() {
                // Create offline indicator
                offlineIndicator = document.createElement('div');
                offlineIndicator.innerHTML = `""" + self.get_offline_html().replace(/"/g, '\\"').replace(/'/g, "\\'") + """`;
                document.body.appendChild(offlineIndicator);
                
                // Create online indicator
                onlineIndicator = document.createElement('div');
                onlineIndicator.innerHTML = `""" + self.get_online_html().replace(/"/g, '\\"').replace(/'/g, "\\'") + """`;
                document.body.appendChild(onlineIndicator);
            }
            
            function showOfflineIndicator() {
                if (offlineIndicator) {
                    offlineIndicator.style.display = 'block';
                    setTimeout(() => {
                        offlineIndicator.style.display = 'none';
                    }, 5000);
                }
            }
            
            function showOnlineIndicator() {
                if (onlineIndicator) {
                    onlineIndicator.style.display = 'block';
                    setTimeout(() => {
                        onlineIndicator.style.display = 'none';
                    }, 3000);
                }
            }
            
            function checkConnectivity() {
                // Simple fetch to check connectivity
                fetch('/api/health', { 
                    method: 'HEAD',
                    cache: 'no-cache',
                    timeout: 5000
                })
                .then(response => {
                    if (response.ok) {
                        if (!isOnline) {
                            isOnline = true;
                            showOnlineIndicator();
                            window.dispatchEvent(new CustomEvent('online'));
                        }
                        retryCount = 0;
                    } else {
                        if (isOnline) {
                            isOnline = false;
                            showOfflineIndicator();
                            window.dispatchEvent(new CustomEvent('offline'));
                        }
                    }
                })
                .catch(error => {
                    if (isOnline) {
                        isOnline = false;
                        showOfflineIndicator();
                        window.dispatchEvent(new CustomEvent('offline'));
                    }
                });
            }
            
            function startConnectivityCheck() {
                // Clear existing interval
                if (checkInterval) {
                    clearInterval(checkInterval);
                }
                
                // Start periodic checks
                checkInterval = setInterval(checkConnectivity, 30000);
                
                // Initial check
                checkConnectivity();
            }
            
            // Event listeners
            window.addEventListener('online', function() {
                isOnline = true;
                showOnlineIndicator();
                startConnectivityCheck();
            });
            
            window.addEventListener('offline', function() {
                isOnline = false;
                showOfflineIndicator();
            });
            
            // Page visibility change - check when page becomes visible
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden) {
                    checkConnectivity();
                }
            });
            
            // Initialize
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', startConnectivityCheck);
            } else {
                startConnectivityCheck();
            }
        })();
        </script>
        """

# Global offline manager instance
offline_manager = OfflineManager()

def add_offline_callback(event_type: str, callback: Callable):
    """Add callback for offline/online events."""
    offline_manager.add_callback(event_type, callback)

def remove_offline_callback(event_type: str, callback: Callable):
    """Remove callback for offline/online events."""
    offline_manager.remove_callback(event_type, callback)

def get_offline_indicators() -> str:
    """Get HTML and JavaScript for offline indicators."""
    return offline_manager.get_offline_html() + offline_manager.get_javascript()

def is_offline() -> bool:
    """Check if currently offline."""
    return not offline_manager.is_online
