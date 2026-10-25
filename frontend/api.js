/**
 * CrisisSense AI — Backend API Client & SSE Stream Wrapper
 * Connects frontend HUD to the FastAPI Bayesian decision engine.
 * Includes automatic offline demo fallback detection.
 */

(function () {
  'use strict';

  // Determine API base: if port 8000 use relative path; otherwise default to http://localhost:8000
  const DEFAULT_PORT = '8000';
  const API_BASE = (window.location.port === DEFAULT_PORT)
    ? ''
    : 'http://localhost:8000';

  let isOnline = false;
  let activeEventSource = null;
  const listeners = {
    connectionChange: []
  };

  function notifyConnection(status) {
    if (isOnline !== status) {
      isOnline = status;
      listeners.connectionChange.forEach(fn => fn(isOnline));
    }
  }

  async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    try {
      const resp = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });
      if (!resp.ok) {
        throw new Error(`API HTTP ${resp.status}`);
      }
      notifyConnection(true);
      return await resp.json();
    } catch (err) {
      notifyConnection(false);
      throw err;
    }
  }

  const CrisisSenseAPI = {
    get isOnline() {
      return isOnline;
    },

    onConnectionChange(fn) {
      listeners.connectionChange.push(fn);
    },

    async checkHealth() {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const resp = await fetch(`${API_BASE}/scenarios`, { signal: controller.signal });
        clearTimeout(timeoutId);
        const ok = resp.ok;
        notifyConnection(ok);
        return ok;
      } catch (e) {
        notifyConnection(false);
        return false;
      }
    },

    async getScenarios() {
      return await apiFetch('/scenarios');
    },

    async startEpisode(scenario = 'twin_cascade', seed = 42, speed = 1.0) {
      return await apiFetch('/episode/start', {
        method: 'POST',
        body: JSON.stringify({ scenario, seed, speed })
      });
    },

    async getMinuteState(minute) {
      return await apiFetch(`/episode/state/${minute}`);
    },

    async getTimeline() {
      return await apiFetch('/episode/timeline');
    },

    async injectAdversity(injectType, target = null, value = null) {
      return await apiFetch('/inject', {
        method: 'POST',
        body: JSON.stringify({
          inject_type: injectType,
          target,
          value
        })
      });
    },

    async getCapAlert(format = 'json') {
      const url = `${API_BASE}/cap-alert?format=${format}`;
      const resp = await fetch(url);
      if (format === 'xml') {
        return await resp.text();
      }
      return await resp.json();
    },

    startStream(onMinuteUpdate, onComplete, onError) {
      this.stopStream();
      try {
        const streamUrl = `${API_BASE}/stream`;
        activeEventSource = new EventSource(streamUrl);

        activeEventSource.addEventListener('minute_update', (e) => {
          notifyConnection(true);
          try {
            const data = JSON.parse(e.data);
            if (onMinuteUpdate) onMinuteUpdate(data);
          } catch (err) {
            console.error('Failed to parse SSE payload:', err);
          }
        });

        activeEventSource.addEventListener('episode_complete', (e) => {
          if (onComplete) onComplete(e.data);
          CrisisSenseAPI.stopStream();
        });

        activeEventSource.onerror = (err) => {
          notifyConnection(false);
          if (onError) onError(err);
          CrisisSenseAPI.stopStream();
        };
      } catch (err) {
        notifyConnection(false);
        if (onError) onError(err);
      }
    },

    stopStream() {
      if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
      }
    }
  };

  // Expose globally
  window.CrisisSenseAPI = CrisisSenseAPI;
})();
