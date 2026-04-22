/**
 * Location Detection Script for Semptify
 * Auto-detects user's state based on browser geolocation
 * Syncs with backend Positronic Brain/Mesh for cross-module awareness
 * Defaults to Minnesota if detection fails
 */

const LocationDetect = {
    // Default state (Minnesota)
    defaultState: 'MN',
    
    // API endpoint for backend sync
    apiBase: '/api/location',
    
    // State abbreviation to name mapping
    stateNames: {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
    },

    // Supported states (Minnesota and neighboring states for now)
    supportedStates: ['MN', 'WI', 'IA', 'SD', 'ND'],

    /**
     * Initialize location detection
     * @param {Object} options - Configuration options
     * @param {string} options.stateSelectId - ID of the state select element
     * @param {string} options.countyInputId - ID of the county input element (optional)
     * @param {string} options.cityInputId - ID of the city input element (optional)
     * @param {string} options.zipInputId - ID of the ZIP input element (optional)
     * @param {boolean} options.autoDetect - Whether to auto-detect on load (default: true)
     * @param {boolean} options.syncBackend - Whether to sync with backend (default: true)
     * @param {Function} options.onDetected - Callback when location is detected
     * @param {Function} options.onError - Callback when detection fails
     */
    init: async function(options = {}) {
        this.options = {
            stateSelectId: options.stateSelectId || 'state',
            countyInputId: options.countyInputId || 'county',
            cityInputId: options.cityInputId || 'city',
            zipInputId: options.zipInputId || 'zip',
            autoDetect: options.autoDetect !== false,
            syncBackend: options.syncBackend !== false,
            onDetected: options.onDetected || function() {},
            onError: options.onError || function() {}
        };

        // Try to load from backend first (has session-based location)
        if (this.options.syncBackend) {
            const loadedFromBackend = await this.loadFromBackend();
            if (loadedFromBackend) {
                console.log('[LocationDetect] Using location from backend');
                return;
            }
        }

        // Check for saved location preference in localStorage
        const savedState = localStorage.getItem('semptify_user_state');
        if (savedState) {
            this.setStateValue(savedState);
            console.log('[LocationDetect] Using saved state preference:', savedState);
            
            // Sync to backend if not already there
            if (this.options.syncBackend) {
                this.syncWithBackend({ state_code: savedState, detection_method: 'localStorage' });
            }
            return;
        }

        // Auto-detect if enabled
        if (this.options.autoDetect) {
            this.detectLocation();
        }
    },

    /**
     * Detect user's location using browser Geolocation API
     */
    detectLocation: function() {
        if (!navigator.geolocation) {
            console.warn('[LocationDetect] Geolocation not supported, using default');
            this.setStateValue(this.defaultState);
            this.options.onError({ message: 'Geolocation not supported' });
            return;
        }

        // Show loading indicator if state select exists
        const stateSelect = document.getElementById(this.options.stateSelectId);
        if (stateSelect) {
            stateSelect.disabled = true;
            const originalOption = stateSelect.querySelector('option[value=""]');
            if (originalOption) {
                originalOption.textContent = 'Detecting location...';
            }
        }

        navigator.geolocation.getCurrentPosition(
            (position) => this.handlePositionSuccess(position),
            (error) => this.handlePositionError(error),
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000 // Cache for 5 minutes
            }
        );
    },

    /**
     * Handle successful geolocation
     */
    handlePositionSuccess: function(position) {
        const { latitude, longitude } = position.coords;
        console.log('[LocationDetect] Got coordinates:', latitude, longitude);
        
        // Use reverse geocoding to get state
        this.reverseGeocode(latitude, longitude);
    },

    /**
     * Handle geolocation error
     */
    handlePositionError: function(error) {
        console.warn('[LocationDetect] Geolocation error:', error.message);
        this.resetStateSelect();
        this.setStateValue(this.defaultState);
        this.options.onError(error);
    },

    /**
     * Reverse geocode coordinates to get location details
     * Uses free Nominatim API (OpenStreetMap)
     */
    reverseGeocode: async function(lat, lon) {
        try {
            // Using Nominatim (OpenStreetMap) - free, no API key required
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&addressdetails=1`,
                {
                    headers: {
                        'Accept-Language': 'en-US,en',
                        'User-Agent': 'Semptify-TenantRights/1.0'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Geocoding request failed');
            }

            const data = await response.json();
            this.processGeocodeResult(data);

        } catch (error) {
            console.error('[LocationDetect] Reverse geocoding failed:', error);
            this.resetStateSelect();
            this.setStateValue(this.defaultState);
            this.options.onError(error);
        }
    },

    /**
     * Process reverse geocoding result
     */
    processGeocodeResult: function(data) {
        const address = data.address || {};
        
        // Get state from response
        let stateCode = null;
        const stateName = address.state;
        
        if (stateName) {
            // Find state code from name
            for (const [code, name] of Object.entries(this.stateNames)) {
                if (name.toLowerCase() === stateName.toLowerCase()) {
                    stateCode = code;
                    break;
                }
            }
        }

        // Also try ISO 3166-2 code if available
        if (!stateCode && address['ISO3166-2-lvl4']) {
            stateCode = address['ISO3166-2-lvl4'].replace('US-', '');
        }

        console.log('[LocationDetect] Detected state:', stateCode, '(' + stateName + ')');

        // Reset select state
        this.resetStateSelect();

        // Prepare location data for backend sync
        const locationData = {
            state_code: stateCode || this.defaultState,
            county: address.county ? address.county.replace(' County', '') : null,
            city: address.city || address.town || address.village || null,
            zip_code: address.postcode ? address.postcode.substring(0, 5) : null,
            detection_method: 'geolocation',
        };

        // Set detected values in form
        if (stateCode) {
            this.setStateValue(stateCode);
            localStorage.setItem('semptify_user_state', stateCode);
        } else {
            this.setStateValue(this.defaultState);
        }

        // Fill in other fields if available
        if (locationData.county) {
            this.setInputValue(this.options.countyInputId, locationData.county);
        }
        if (locationData.city) {
            this.setInputValue(this.options.cityInputId, locationData.city);
        }
        if (locationData.zip_code) {
            this.setInputValue(this.options.zipInputId, locationData.zip_code);
        }

        // Sync with backend (Positronic Brain)
        this.syncWithBackend(locationData);

        // Call success callback
        this.options.onDetected({
            state: stateCode || this.defaultState,
            stateName: stateName || this.stateNames[this.defaultState],
            county: locationData.county,
            city: locationData.city,
            zip: locationData.zip_code,
            raw: data
        });
    },

    /**
     * Sync location with backend API (Positronic Brain integration)
     */
    syncWithBackend: async function(locationData) {
        try {
            const response = await fetch(this.apiBase + '/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(locationData),
                credentials: 'include',  // Include cookies for session
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('[LocationDetect] Backend synced:', result);
                
                // Store support level
                if (result.support_level) {
                    localStorage.setItem('semptify_support_level', result.support_level);
                }
            } else {
                console.warn('[LocationDetect] Backend sync failed:', response.status);
            }
        } catch (error) {
            console.warn('[LocationDetect] Backend sync error:', error);
            // Continue anyway - frontend still works without backend sync
        }
    },

    /**
     * Load location from backend on init
     */
    loadFromBackend: async function() {
        try {
            const response = await fetch(this.apiBase + '/current', {
                credentials: 'include',
            });
            
            if (response.ok) {
                const location = await response.json();
                console.log('[LocationDetect] Loaded from backend:', location);
                
                if (location.state_code && location.detection_method !== 'default') {
                    this.setStateValue(location.state_code);
                    if (location.county) this.setInputValue(this.options.countyInputId, location.county);
                    if (location.city) this.setInputValue(this.options.cityInputId, location.city);
                    if (location.zip_code) this.setInputValue(this.options.zipInputId, location.zip_code);
                    
                    localStorage.setItem('semptify_user_state', location.state_code);
                    return true;  // Found saved location
                }
            }
        } catch (error) {
            console.debug('[LocationDetect] Backend load failed:', error);
        }
        return false;  // No saved location
    },

    /**
     * Get legal resources for current location
     */
    getLegalResources: async function() {
        try {
            const response = await fetch(this.apiBase + '/resources', {
                credentials: 'include',
            });
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.warn('[LocationDetect] Failed to get legal resources:', error);
        }
        return null;
    },

    /**
     * Get eviction timeline for current state
     */
    getEvictionTimeline: async function() {
        try {
            const response = await fetch(this.apiBase + '/eviction-timeline', {
                credentials: 'include',
            });
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.warn('[LocationDetect] Failed to get eviction timeline:', error);
        }
        return null;
    },

    /**
     * Reset state select to normal state
     */
    resetStateSelect: function() {
        const stateSelect = document.getElementById(this.options.stateSelectId);
        if (stateSelect) {
            stateSelect.disabled = false;
            const defaultOption = stateSelect.querySelector('option[value=""]');
            if (defaultOption) {
                defaultOption.textContent = 'Select...';
            }
        }
    },

    /**
     * Set the value of the state select element
     */
    setStateValue: function(stateCode) {
        const stateSelect = document.getElementById(this.options.stateSelectId);
        if (stateSelect) {
            // Check if option exists
            const option = stateSelect.querySelector(`option[value="${stateCode}"]`);
            if (option) {
                stateSelect.value = stateCode;
            } else {
                // If state not in dropdown, default to MN
                console.log('[LocationDetect] State', stateCode, 'not in dropdown, defaulting to MN');
                stateSelect.value = this.defaultState;
            }
            
            // Trigger change event
            stateSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
    },

    /**
     * Set the value of an input element
     */
    setInputValue: function(elementId, value) {
        const element = document.getElementById(elementId);
        if (element && value && !element.value) {
            element.value = value;
            element.dispatchEvent(new Event('input', { bubbles: true }));
        }
    },

    /**
     * Clear saved location preference
     */
    clearSavedLocation: function() {
        localStorage.removeItem('semptify_user_state');
        console.log('[LocationDetect] Cleared saved location preference');
    },

    /**
     * Manually trigger location detection
     */
    refresh: function() {
        this.clearSavedLocation();
        this.detectLocation();
    },

    /**
     * Check if a state is supported (has full tenant rights info)
     */
    isStateSupported: function(stateCode) {
        return this.supportedStates.includes(stateCode);
    },

    /**
     * Get support status message for a state
     */
    getSupportMessage: function(stateCode) {
        if (stateCode === 'MN') {
            return 'Full support available for Minnesota tenant rights.';
        } else if (this.isStateSupported(stateCode)) {
            return `Limited support available for ${this.stateNames[stateCode]}. Some features may reference Minnesota resources.`;
        } else {
            return `${this.stateNames[stateCode]} is outside our primary service area. Features will reference Minnesota resources.`;
        }
    }
};

// Auto-initialize when DOM is ready (can be disabled by setting data-auto-init="false" on script tag)
document.addEventListener('DOMContentLoaded', function() {
    const scriptTag = document.querySelector('script[src*="location-detect"]');
    const autoInit = scriptTag ? scriptTag.getAttribute('data-auto-init') !== 'false' : true;
    
    if (autoInit && document.getElementById('state')) {
        LocationDetect.init();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LocationDetect;
}
