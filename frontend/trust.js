'use strict';

const trustById = id => document.getElementById(id);
const trustOut = trustById('trust-inspect-output');

trustById('trust-inspect').addEventListener('click', async () => {
  trustOut.textContent = 'Inspecting the domain using the selected checks…';
  try {
    const result = await trustPost('/api/trust/inspect', {
      url: trustById('trust-url').value,
      check_tls: trustById('trust-check-tls').checked,
      check_reputation: trustById('trust-check-reputation').checked
    });
    trustOut.textContent = JSON.stringify(result, null, 2);
    trustById('trust-register-url').value = result.domain || trustById('trust-url').value;
    if (result.tls?.certificate_fingerprint) {
      trustById('trust-fingerprint').value = result.tls.certificate_fingerprint;
      trustById('trust-fingerprint-source').textContent = result.tls.certificate_valid
        ? 'Fingerprint from a certificate that passed local TLS validation.'
        : 'Fingerprint came from the current TLS endpoint; certificate validation failed.';
    }
  } catch (error) {
    trustOut.textContent = error?.message || 'Local URL trust inspection failed.';
  }
});

trustById('trust-register').addEventListener('click', async () => {
  trustById('trust-register-output').textContent = 'Saving a local user-maintained record…';
  try {
    const result = await trustPost('/api/trust/register', {
      url: trustById('trust-register-url').value,
      certificate_fingerprint: trustById('trust-fingerprint').value,
      metadata: trustById('trust-metadata').value
    });
    trustById('trust-register-output').textContent = JSON.stringify(result, null, 2);
    await loadTrustRecords();
  } catch (error) {
    trustById('trust-register-output').textContent = error?.message || 'Could not save the local record.';
  }
});

trustById('trust-revoke').addEventListener('click', async () => {
  trustById('trust-register-output').textContent = 'Revoking the local record…';
  try {
    const result = await trustPost('/api/trust/revoke', {
      url: trustById('trust-register-url').value,
      reason: trustById('trust-revoke-reason').value
    });
    trustById('trust-register-output').textContent = JSON.stringify(result, null, 2);
    await loadTrustRecords();
  } catch (error) {
    trustById('trust-register-output').textContent = error?.message || 'Could not revoke the local record.';
  }
});

trustById('trust-refresh').addEventListener('click', loadTrustRecords);
loadTrustRecords();
loadTrustStatus();

async function trustPost(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

async function loadTrustStatus() {
  const status = trustById('trust-status');
  try {
    const response = await fetch('/api/trust/status');
    const result = await response.json();
    const enabled = [];
    if (result.google_safe_browsing_configured) enabled.push('Google Safe Browsing key configured');
    if (result.virustotal_configured) enabled.push('VirusTotal key configured');
    status.textContent = `Local-only ledger · blockchain disconnected · reputation checks default off${enabled.length ? ` · ${enabled.join(' · ')}` : ''}`;
  } catch (_) {
    status.textContent = 'Local registry status is unavailable.';
  }
}

async function loadTrustRecords() {
  const list = trustById('trust-records');
  list.replaceChildren();
  try {
    const response = await fetch('/api/trust/records');
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Local records unavailable');
    if (!payload.records.length) {
      list.textContent = 'No local records yet.';
      return;
    }
    for (const record of payload.records) {
      const article = document.createElement('article');
      article.className = 'trust-record';
      const heading = document.createElement('div');
      heading.className = 'trust-record-heading';
      const domain = document.createElement('strong');
      domain.textContent = record.domain;
      const state = document.createElement('span');
      state.className = `trust-badge trust-${record.status}`;
      state.textContent = record.status === 'active' ? 'Local record active' : 'Revoked locally';
      heading.append(domain, state);
      const fingerprint = document.createElement('code');
      fingerprint.textContent = `SHA-256 ${record.certificate_fingerprint}`;
      const detail = document.createElement('small');
      detail.textContent = [record.metadata, `Updated ${record.updated_at}`].filter(Boolean).join(' · ');
      article.append(heading, fingerprint, detail);
      if (record.status === 'active') {
        const choose = document.createElement('button');
        choose.type = 'button';
        choose.textContent = 'Use domain in revoke form';
        choose.addEventListener('click', () => {
          trustById('trust-register-url').value = record.domain;
          trustById('trust-register-output').textContent = 'Add a reason, then revoke this local record if needed.';
        });
        article.append(choose);
      }
      list.append(article);
    }
  } catch (error) {
    list.textContent = error?.message || 'Local records are unavailable.';
  }
}
