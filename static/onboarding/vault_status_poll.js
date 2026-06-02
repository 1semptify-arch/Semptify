// Simple polling helper for onboarding vault status
// Usage: call `startVaultStatusPoll(onComplete, onPending, opts)` after POST /onboarding/api/vault/security returns success

async function fetchVaultStatus() {
  const res = await fetch('/onboarding/api/vault/status', { credentials: 'include' });
  if (!res.ok) throw new Error('status fetch failed');
  return res.json();
}

export async function pollVaultStatus({
  interval = 2500,
  timeout = 60000,
  onPending = () => {},
  onComplete = () => {},
  onError = (e) => { console.error('vault poll error', e); }
} = {}) {
  const start = Date.now();
  while (true) {
    try {
      const s = await fetchVaultStatus();
      if (s.vault_initialized && s.document_uploaded) {
        onComplete(s);
        return s;
      }
      onPending(s);
    } catch (e) {
      onError(e);
    }
    if (Date.now() - start > timeout) throw new Error('timeout waiting for vault status');
    await new Promise(r => setTimeout(r, interval));
  }
}

// Example no-module usage (include via <script> tag) — attaches to window
if (typeof window !== 'undefined') {
  window.pollVaultStatus = async function(opts) { return pollVaultStatus(opts); };
}
