/**
 * Location Detection Utility for Semptify
 * Provides geolocation services and state-specific support information
 */

window.LocationDetect = {
    // Initialize location detection
    init: function(options) {
        this.options = options || {};
        this.stateSelectId = this.options.stateSelectId;
        this.countyInputId = this.options.countyInputId;
        this.cityInputId = this.options.cityInputId;
        this.zipInputId = this.options.zipInputId;
        this.onDetected = this.options.onDetected || function() {};
        this.onError = this.options.onError || function() {};

        console.log('Location detection initialized');
    },

    // Refresh location detection
    refresh: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                this.handleSuccess.bind(this),
                this.handleError.bind(this)
            );
        } else {
            this.onError('Geolocation not supported');
        }
    },

    // Handle successful geolocation
    handleSuccess: function(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;

        // For now, default to Minnesota since we're focused on MN tenant rights
        const location = {
            state: 'MN',
            city: '',
            county: '',
            zip: '',
            latitude: lat,
            longitude: lng
        };

        this.updateForm(location);
        this.onDetected(location);
    },

    // Handle geolocation error
    handleError: function(error) {
        console.log('Geolocation error:', error.message);
        this.onError(error.message);
    },

    // Update form fields with detected location
    updateForm: function(location) {
        if (this.stateSelectId && location.state) {
            const stateSelect = document.getElementById(this.stateSelectId);
            if (stateSelect) {
                stateSelect.value = location.state;
            }
        }

        if (this.cityInputId && location.city) {
            const cityInput = document.getElementById(this.cityInputId);
            if (cityInput) {
                cityInput.value = location.city;
            }
        }

        if (this.countyInputId && location.county) {
            const countyInput = document.getElementById(this.countyInputId);
            if (countyInput) {
                countyInput.value = location.county;
            }
        }

        if (this.zipInputId && location.zip) {
            const zipInput = document.getElementById(this.zipInputId);
            if (zipInput) {
                zipInput.value = location.zip;
            }
        }
    },

    // Get support message for state
    getSupportMessage: function(state) {
        const messages = {
            'MN': '● Full Minnesota tenant rights support available',
            'WI': '◆ Limited Wisconsin tenant rights support',
            'IA': '◆ Limited Iowa tenant rights support',
            'SD': '◆ Limited South Dakota tenant rights support',
            'default': '◆ Limited tenant rights support for this state'
        };

        return messages[state] || messages['default'];
    }
};
