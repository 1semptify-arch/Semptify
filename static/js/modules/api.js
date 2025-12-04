/**
 * ============================================================================
 * SEMPTIFY API CLIENT
 * ============================================================================
 * 
 * Centralized API client with:
 * - Consistent error handling
 * - Request/response interceptors
 * - Automatic token refresh
 * - Request deduplication
 * - Retry logic
 * - TypeScript-friendly structure
 */

const API_BASE_URL = window.location.origin;
const DEFAULT_TIMEOUT = 30000;

/**
 * API Error class for structured error handling
 */
class ApiError extends Error {
  constructor(message, status, code, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.data = data;
    this.timestamp = new Date().toISOString();
  }

  /**
   * Check if error is a client error (4xx)
   */
  isClientError() {
    return this.status >= 400 && this.status < 500;
  }

  /**
   * Check if error is a server error (5xx)
   */
  isServerError() {
    return this.status >= 500;
  }

  /**
   * Check if error is network-related
   */
  isNetworkError() {
    return this.status === 0 || this.code === 'NETWORK_ERROR';
  }
}

/**
 * Request queue for deduplication
 */
const pendingRequests = new Map();

/**
 * Generate a unique key for request deduplication
 */
function getRequestKey(method, url, body) {
  return `${method}:${url}:${JSON.stringify(body || '')}`;
}

/**
 * Main API client
 */
const api = {
  /**
   * Get the current auth token
   */
  getToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
  },

  /**
   * Set the auth token
   */
  setToken(token, persistent = false) {
    if (persistent) {
      localStorage.setItem('auth_token', token);
    } else {
      sessionStorage.setItem('auth_token', token);
    }
  },

  /**
   * Clear the auth token
   */
  clearToken() {
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
  },

  /**
   * Get default headers for requests
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...customHeaders
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  },

  /**
   * Core request method with all features
   */
  async request(method, endpoint, options = {}) {
    const {
      body = null,
      headers = {},
      timeout = DEFAULT_TIMEOUT,
      retries = 0,
      retryDelay = 1000,
      dedupe = false,
      signal = null
    } = options;

    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    const requestKey = dedupe ? getRequestKey(method, url, body) : null;

    // Check for pending duplicate request
    if (requestKey && pendingRequests.has(requestKey)) {
      return pendingRequests.get(requestKey);
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Merge signals if provided
    const combinedSignal = signal 
      ? { signal: new AbortController().signal } // TODO: proper signal combination
      : { signal: controller.signal };

    const requestOptions = {
      method: method.toUpperCase(),
      headers: this.getHeaders(headers),
      ...combinedSignal
    };

    if (body && !['GET', 'HEAD'].includes(method.toUpperCase())) {
      requestOptions.body = JSON.stringify(body);
    }

    const requestPromise = (async () => {
      let lastError;
      let attempts = 0;

      while (attempts <= retries) {
        try {
          const response = await fetch(url, requestOptions);
          clearTimeout(timeoutId);

          // Parse response
          let data = null;
          const contentType = response.headers.get('content-type');
          
          if (contentType && contentType.includes('application/json')) {
            try {
              data = await response.json();
            } catch {
              data = null;
            }
          } else if (contentType && contentType.includes('text/')) {
            data = await response.text();
          }

          // Handle error responses
          if (!response.ok) {
            const errorMessage = data?.detail || data?.message || `Request failed with status ${response.status}`;
            throw new ApiError(errorMessage, response.status, data?.code || 'API_ERROR', data);
          }

          return {
            data,
            status: response.status,
            headers: response.headers,
            ok: true
          };

        } catch (error) {
          clearTimeout(timeoutId);
          lastError = error;

          // Don't retry on client errors or abort
          if (error instanceof ApiError && error.isClientError()) {
            throw error;
          }

          if (error.name === 'AbortError') {
            throw new ApiError('Request timed out', 0, 'TIMEOUT');
          }

          // Network error
          if (error.name === 'TypeError') {
            lastError = new ApiError('Network error', 0, 'NETWORK_ERROR');
          }

          // Retry if we have attempts left
          if (attempts < retries) {
            attempts++;
            await new Promise(resolve => setTimeout(resolve, retryDelay * attempts));
            continue;
          }

          throw lastError;
        }
      }

      throw lastError;
    })();

    // Store for deduplication
    if (requestKey) {
      pendingRequests.set(requestKey, requestPromise);
      requestPromise.finally(() => {
        pendingRequests.delete(requestKey);
      });
    }

    return requestPromise;
  },

  /**
   * GET request
   */
  async get(endpoint, options = {}) {
    return this.request('GET', endpoint, options);
  },

  /**
   * POST request
   */
  async post(endpoint, body = null, options = {}) {
    return this.request('POST', endpoint, { ...options, body });
  },

  /**
   * PUT request
   */
  async put(endpoint, body = null, options = {}) {
    return this.request('PUT', endpoint, { ...options, body });
  },

  /**
   * PATCH request
   */
  async patch(endpoint, body = null, options = {}) {
    return this.request('PATCH', endpoint, { ...options, body });
  },

  /**
   * DELETE request
   */
  async delete(endpoint, options = {}) {
    return this.request('DELETE', endpoint, options);
  },

  /**
   * Upload file with progress tracking
   */
  async upload(endpoint, file, options = {}) {
    const {
      fieldName = 'file',
      additionalData = {},
      onProgress = null,
      headers = {}
    } = options;

    const formData = new FormData();
    formData.append(fieldName, file);

    // Add additional form data
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value);
    });

    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent, event.loaded, event.total);
          }
        });
      }

      xhr.addEventListener('load', () => {
        let data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch {
          data = xhr.responseText;
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve({ data, status: xhr.status, ok: true });
        } else {
          reject(new ApiError(
            data?.detail || 'Upload failed',
            xhr.status,
            data?.code || 'UPLOAD_ERROR',
            data
          ));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new ApiError('Network error during upload', 0, 'NETWORK_ERROR'));
      });

      xhr.addEventListener('abort', () => {
        reject(new ApiError('Upload aborted', 0, 'ABORTED'));
      });

      xhr.open('POST', url);

      // Set auth header
      const token = this.getToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      // Set custom headers
      Object.entries(headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });

      xhr.send(formData);
    });
  },

  /**
   * Download file
   */
  async download(endpoint, filename = null) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new ApiError('Download failed', response.status, 'DOWNLOAD_ERROR');
    }

    const blob = await response.blob();
    
    // Get filename from Content-Disposition header or use provided
    const contentDisposition = response.headers.get('Content-Disposition');
    let downloadFilename = filename;
    
    if (!downloadFilename && contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match) {
        downloadFilename = match[1].replace(/['"]/g, '');
      }
    }

    downloadFilename = downloadFilename || 'download';

    // Create download link
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = downloadFilename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    return { filename: downloadFilename, size: blob.size };
  }
};

// ============================================================================
// API ENDPOINTS - Organized by domain
// ============================================================================

/**
 * Authentication API
 */
const authApi = {
  async login(email, password) {
    const response = await api.post('/api/auth/login', { email, password });
    if (response.data?.access_token) {
      api.setToken(response.data.access_token);
    }
    return response;
  },

  async register(userData) {
    return api.post('/api/auth/register', userData);
  },

  async logout() {
    try {
      await api.post('/api/auth/logout');
    } finally {
      api.clearToken();
    }
  },

  async refreshToken() {
    const response = await api.post('/api/auth/refresh');
    if (response.data?.access_token) {
      api.setToken(response.data.access_token);
    }
    return response;
  },

  async getCurrentUser() {
    return api.get('/api/auth/me');
  },

  async updateProfile(data) {
    return api.patch('/api/auth/profile', data);
  }
};

/**
 * Documents API
 */
const documentsApi = {
  async list(params = {}) {
    const searchParams = new URLSearchParams(params);
    return api.get(`/api/documents?${searchParams}`);
  },

  async get(documentId) {
    return api.get(`/api/documents/${documentId}`);
  },

  async upload(file, metadata = {}, onProgress = null) {
    return api.upload('/api/documents/upload', file, {
      additionalData: metadata,
      onProgress
    });
  },

  async delete(documentId) {
    return api.delete(`/api/documents/${documentId}`);
  },

  async analyze(documentId) {
    return api.post(`/api/documents/${documentId}/analyze`);
  },

  async download(documentId) {
    return api.download(`/api/documents/${documentId}/download`);
  }
};

/**
 * Timeline API
 */
const timelineApi = {
  async get(params = {}) {
    const searchParams = new URLSearchParams(params);
    return api.get(`/api/timeline?${searchParams}`);
  },

  async addEvent(eventData) {
    return api.post('/api/timeline/events', eventData);
  },

  async updateEvent(eventId, eventData) {
    return api.put(`/api/timeline/events/${eventId}`, eventData);
  },

  async deleteEvent(eventId) {
    return api.delete(`/api/timeline/events/${eventId}`);
  }
};

/**
 * Calendar API
 */
const calendarApi = {
  async getEvents(startDate, endDate) {
    return api.get(`/api/calendar/events?start=${startDate}&end=${endDate}`);
  },

  async createEvent(eventData) {
    return api.post('/api/calendar/events', eventData);
  },

  async updateEvent(eventId, eventData) {
    return api.put(`/api/calendar/events/${eventId}`, eventData);
  },

  async deleteEvent(eventId) {
    return api.delete(`/api/calendar/events/${eventId}`);
  }
};

/**
 * Vault API
 */
const vaultApi = {
  async getSecrets(category = null) {
    const endpoint = category ? `/api/vault?category=${category}` : '/api/vault';
    return api.get(endpoint);
  },

  async addSecret(secretData) {
    return api.post('/api/vault', secretData);
  },

  async updateSecret(secretId, secretData) {
    return api.put(`/api/vault/${secretId}`, secretData);
  },

  async deleteSecret(secretId) {
    return api.delete(`/api/vault/${secretId}`);
  }
};

/**
 * Cloud Sync API
 */
const syncApi = {
  async getStatus() {
    return api.get('/api/sync/status');
  },

  async fullSync() {
    return api.post('/api/sync/full');
  },

  async configure(config) {
    return api.post('/api/sync/configure', config);
  },

  async listProviders() {
    return api.get('/api/sync/providers');
  }
};

/**
 * Copilot/AI API
 */
const copilotApi = {
  async analyze(text) {
    return api.post('/api/copilot/analyze', { text });
  },

  async suggest(context) {
    return api.post('/api/copilot/suggest', context);
  },

  async chat(message, conversationId = null) {
    return api.post('/api/copilot/chat', { message, conversation_id: conversationId });
  }
};

/**
 * System/Health API
 */
const systemApi = {
  async health() {
    return api.get('/api/health', { dedupe: true });
  },

  async status() {
    return api.get('/api/status');
  },

  async metrics() {
    return api.get('/api/metrics');
  }
};

/**
 * Eviction Forms API
 */
const evictionApi = {
  async getForms() {
    return api.get('/api/eviction/forms');
  },

  async getForm(formId) {
    return api.get(`/api/eviction/forms/${formId}`);
  },

  async submitForm(formId, data) {
    return api.post(`/api/eviction/forms/${formId}/submit`, data);
  },

  async getFlows() {
    return api.get('/api/eviction/flows');
  },

  async startFlow(flowId, initialData = {}) {
    return api.post(`/api/eviction/flows/${flowId}/start`, initialData);
  },

  async continueFlow(sessionId, stepData) {
    return api.post(`/api/eviction/flows/continue/${sessionId}`, stepData);
  }
};

// ============================================================================
// EXPORTS
// ============================================================================

// Make available globally for non-module scripts
window.api = api;
window.ApiError = ApiError;
window.authApi = authApi;
window.documentsApi = documentsApi;
window.timelineApi = timelineApi;
window.calendarApi = calendarApi;
window.vaultApi = vaultApi;
window.syncApi = syncApi;
window.copilotApi = copilotApi;
window.systemApi = systemApi;
window.evictionApi = evictionApi;

// ES Module exports
export {
  api,
  ApiError,
  authApi,
  documentsApi,
  timelineApi,
  calendarApi,
  vaultApi,
  syncApi,
  copilotApi,
  systemApi,
  evictionApi
};
