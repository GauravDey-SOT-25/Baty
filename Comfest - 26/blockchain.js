const menuButton = document.querySelector('.menu-toggle');
const menuOverlay = document.querySelector('.menu-overlay');

menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'Open menu' : 'Close menu');
  menuOverlay.classList.toggle('is-open', !isOpen);
  menuOverlay.setAttribute('aria-hidden', String(isOpen));
  document.body.classList.toggle('menu-open', !isOpen);
});

menuOverlay.addEventListener('click', (event) => {
  if (event.target === menuOverlay) menuButton.click();
});

menuOverlay.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open menu');
    menuOverlay.classList.remove('is-open');
    menuOverlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-open');
  });
});

const tabs = [...document.querySelectorAll('.code-tab')];
const samples = [...document.querySelectorAll('.code-sample')];
const activeFile = document.querySelector('#active-file');
const codePaths = {
  solidity: 'contracts / TrustRegistry.sol',
  api: 'backend / app.py',
  hash: 'backend / hasher.py',
};

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    const selected = tab.dataset.code;
    tabs.forEach((item) => {
      const active = item === tab;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-selected', String(active));
    });
    samples.forEach((sample) => {
      const active = sample.dataset.sample === selected;
      sample.hidden = !active;
      sample.classList.toggle('is-visible', active);
    });
    activeFile.textContent = codePaths[selected];
  });
});

const demoModeTabs = [...document.querySelectorAll('.demo-mode-tabs button')];
const checkForm = document.querySelector('#inline-check-form');
const registerForm = document.querySelector('#inline-register-form');
const demoMessage = document.querySelector('#demo-message');
const demoDetails = document.querySelector('#demo-details');
const verdictValue = document.querySelector('#verdict-value');
const verdictScore = document.querySelector('#verdict-score');
const verdictPill = document.querySelector('#verdict-pill');
const verdictLabel = document.querySelector('#verdict-label');
const resultTitle = document.querySelector('#result-title');
const resultModeLabel = document.querySelector('#result-mode-label');
const stepRows = [...document.querySelectorAll('#demo-steps .demo-step')];
const backendStatus = document.querySelector('#backend-status');
const manualCertToggle = document.querySelector('#inline-manual-cert');
const manualCertInput = document.querySelector('#inline-cert-fingerprint');
const scanSubmit = document.querySelector('#inline-check-submit');
const API_BASE = 'http://127.0.0.1:5000';
const STEP_TITLES = ['VirusTotal reputation', 'Google Safe Browsing', 'Live SSL/TLS certificate', 'Blockchain trust record', 'Oracle quorum and stake'];

function normalizeInputUrl(value) { const trimmed = value.trim(); return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`; }
function setBackendStatus(state) {
  backendStatus.dataset.state = state;
  backendStatus.replaceChildren(document.createElement('b'), document.createTextNode(state === 'online' ? ' BACKEND ONLINE' : ' BACKEND OFFLINE'));
}
function showMessage(message, kind = '') {
  demoMessage.textContent = message;
  demoMessage.dataset.kind = kind;
  demoMessage.hidden = !message;
}
function setSteps(values) {
  stepRows.forEach((row, index) => {
    const value = values[index] || {};
    row.querySelector('b').textContent = value.title || STEP_TITLES[index];
    row.querySelector('small').textContent = value.detail || 'Waiting for scan';
    row.querySelector('.demo-state').textContent = value.state || 'READY';
    row.dataset.state = (value.state || 'ready').toLowerCase().replace(/[^a-z0-9-]/g, '-');
  });
}
function addDetail(label, value) {
  if (value === undefined || value === null || value === '') return;
  const row = document.createElement('div');
  const key = document.createElement('span');
  const val = document.createElement('code');
  key.textContent = label;
  val.textContent = Array.isArray(value) ? (value.length ? value.join(' · ') : 'None returned') : (typeof value === 'string' ? value : JSON.stringify(value));
  row.append(key, val);
  demoDetails.append(row);
}
function addDetailGroup(title, fields) {
  const group = document.createElement('section');
  group.className = 'demo-detail-group';
  const heading = document.createElement('h4');
  heading.textContent = title;
  group.append(heading);
  demoDetails.append(group);
  fields.forEach(([label, value]) => addDetail(label, value));
}
function showCheckDetails(data) {
  const cert = data.live_certificate || {};
  const record = data.blockchain_record || null;
  const intel = data.threat_intelligence || {};
  const vt = intel.virustotal || {};
  const gsb = intel.google_safe_browsing || {};
  const sig = record?.eip712_signature || {};
  const score = data.trust_score;
  demoDetails.replaceChildren();
  demoDetails.hidden = false;
  addDetailGroup('ASSESSMENT', [
    ['Canonical URL', data.canonical_url], ['Domain', data.domain], ['Trust score', score === undefined ? null : `${score} / 100`], ['Summary', data.summary], ['Explanation', data.explanation], ['Indicators', data.indicators || []],
  ]);
  addDetailGroup('LEDGER & CERTIFICATE', [
    ['Domain SHA-256', data.url_hash], ['Ledger status', record ? (record.is_trusted ? 'Trusted record' : 'Revoked record') : 'No record'], ['Recorded certificate', record?.cert_fingerprint], ['Live TLS status', cert.success ? 'Handshake successful' : (cert.error || cert.status || 'Unavailable')], ['Live certificate SHA-256', cert.fingerprint], ['Certificate issuer', cert.issuer], ['Certificate subject', cert.subject], ['Certificate expires', cert.expires],
    ['Fingerprint comparison', record && cert.success ? (record.cert_fingerprint?.toLowerCase() === cert.fingerprint?.toLowerCase() ? 'Match' : 'Mismatch') : 'Not comparable'],
  ]);
  addDetailGroup('CONSENSUS & CRYPTOGRAPHIC PROOF', [
    ['Primary verifier', record?.primary_verifier || record?.verifier_id], ['Oracle quorum', record?.quorum_details?.map((node) => `${node.name || node.id || 'Validator'}${node.signed ? ' · signed' : ''}`) || record?.oracle_quorum], ['Consensus score', record?.consensus_score === undefined ? null : `${record.consensus_score}%`], ['Stake locked', record?.stake_locked], ['IPFS snapshot CID', record?.ipfs_cid], ['Merkle state root', record?.merkle_root], ['Merkle proof siblings', record?.merkle_proof], ['EIP-712 signature', sig.signature || (sig.v ? `v=${sig.v} · r=${sig.r || ''} · s=${sig.s || ''}` : null)], ['Transaction hash', record?.tx_hash], ['Block number', record?.block_number], ['Gas used', record?.gas_used], ['Base fee', record?.base_fee],
  ]);
  addDetailGroup('THREAT INTELLIGENCE', [
    ['VirusTotal', vt.status || 'No result'], ['VirusTotal detections', vt.success ? `${vt.malicious_count || 0} malicious / ${vt.total_engines || '—'} engines` : (vt.error || 'Unavailable')], ['VirusTotal categories', vt.categories || []], ['Google Safe Browsing', gsb.status || 'No result'], ['Google threat categories', gsb.threat_types || []], ['Combined threat flag', intel.is_threat_detected ? 'Threat reported' : 'No threat reported by available sources'],
  ]);
}
function showRegistrationDetails(data) {
  const transaction = data.transaction || {};
  const record = transaction.record || {};
  demoDetails.replaceChildren();
  demoDetails.hidden = false;
  addDetailGroup('REGISTERED TRUST RECORD', [
    ['Canonical URL', data.url], ['Domain', data.domain], ['Domain SHA-256', data.url_hash], ['Certificate SHA-256', data.cert_fingerprint], ['Transaction hash', transaction.tx_hash || transaction.transaction_hash], ['Block number', transaction.block_number], ['Merkle root', transaction.merkle_root || record.merkle_root], ['IPFS CID', transaction.ipfs_cid || record.ipfs_cid], ['Verifier', record.primary_verifier || record.verifier_id], ['Consensus', transaction.consensus_score === undefined ? null : `${transaction.consensus_score}%`],
  ]);
}
async function apiRequest(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, signal: AbortSignal.timeout(20000) });
  } catch (error) {
    if (error.name === 'TimeoutError') throw new Error('The scan timed out. Check the backend and try again.');
    throw new Error('Baty backend is offline. Start it with: python Parallel/run_demo.py');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.success === false) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
async function animatePipeline() {
  const descriptions = ['Checking domain reputation with VirusTotal…', 'Querying Google Safe Browsing…', 'Inspecting the live TLS certificate…', 'Looking up the trust record and Merkle proof…', 'Reviewing available validator quorum evidence…'];
  for (let index = 0; index < stepRows.length; index += 1) {
    setSteps(stepRows.map((row, rowIndex) => ({ detail: rowIndex < index ? 'Complete' : rowIndex === index ? descriptions[index] : 'Queued', state: rowIndex < index ? 'DONE' : rowIndex === index ? 'RUNNING' : 'WAITING' })));
    await wait(360);
  }
}
function finalCheckSteps(data) {
  const intel = data.threat_intelligence || {};
  const vt = intel.virustotal || {};
  const gsb = intel.google_safe_browsing || {};
  const cert = data.live_certificate || {};
  const record = data.blockchain_record;
  const nodes = record?.quorum_details || [];
  const quorum = nodes.length ? `${nodes.filter((node) => node.signed).length}/${nodes.length} validators signed` : (record?.oracle_quorum?.length ? `${record.oracle_quorum.length} validators in record` : 'No attested quorum');
  return [
    { detail: vt.success ? `${vt.malicious_count || 0} malicious / ${vt.total_engines || '—'} engines` : (vt.status || vt.error || 'Unavailable'), state: vt.is_threat ? 'FLAGGED' : vt.success ? 'CHECKED' : 'UNAVAILABLE' },
    { detail: gsb.status || gsb.error || 'Unavailable', state: gsb.is_threat ? 'FLAGGED' : gsb.success ? 'CHECKED' : 'UNAVAILABLE' },
    { detail: cert.success ? `${cert.issuer || 'Valid certificate'}${cert.fingerprint ? ` · ${cert.fingerprint.slice(0, 14)}…` : ''}` : (cert.error || 'Certificate unavailable'), state: cert.success ? 'CHECKED' : 'REVIEW' },
    { detail: record ? `${record.is_trusted ? 'Trusted record' : 'Revoked record'}${record.merkle_root ? ` · root ${record.merkle_root.slice(0, 12)}…` : ''}` : 'No matching trust record', state: record ? (record.is_trusted ? 'FOUND' : 'REVOKED') : 'NOT FOUND' },
    { detail: quorum, state: nodes.length ? (nodes.every((node) => node.signed) ? 'CONSENSUS' : 'REVIEW') : record?.oracle_quorum?.length ? 'RECORDED' : 'NO RECORD' },
  ];
}
async function runCheck(url) {
  resultTitle.textContent = 'VERIFICATION PIPELINE';
  resultModeLabel.textContent = '5 LIVE CHECKS';
  demoDetails.hidden = true;
  verdictLabel.textContent = 'TRUST ASSESSMENT';
  verdictValue.textContent = 'Scanning…';
  verdictScore.textContent = '—';
  verdictPill.textContent = 'IN PROGRESS';
  showMessage('Running the scanner pipeline. Results will include the evidence returned by each available source.');
  scanSubmit.disabled = true;
  scanSubmit.querySelector('.button-label').textContent = 'SCANNING…';
  const animation = animatePipeline();
  try {
    const data = await apiRequest(`/api/check?url=${encodeURIComponent(url)}`);
    await animation;
    const threat = Boolean(data.threat_intelligence?.is_threat_detected);
    const cert = data.live_certificate || {};
    const record = data.blockchain_record;
    verdictValue.textContent = data.trust_verdict || 'Assessment complete';
    verdictScore.textContent = data.trust_score ?? '—';
    verdictPill.textContent = threat ? 'THREAT FLAGGED' : record?.is_trusted ? 'TRUST RECORD FOUND' : 'UNVERIFIED';
    verdictPill.dataset.state = threat ? 'danger' : record?.is_trusted ? 'success' : 'neutral';
    setSteps(finalCheckSteps(data));
    showMessage(data.summary || data.explanation || 'Assessment completed. Review the returned evidence below.', threat ? 'error' : 'success');
    showCheckDetails(data);
  } catch (error) {
    await animation;
    verdictValue.textContent = 'Could not assess';
    verdictScore.textContent = '—';
    verdictPill.textContent = 'CHECK FAILED';
    verdictPill.dataset.state = 'danger';
    showMessage(error.message, 'error');
    setSteps(STEP_TITLES.map((title) => ({ title, detail: 'No result returned', state: 'ERROR' })));
  } finally {
    scanSubmit.disabled = false;
    scanSubmit.querySelector('.button-label').textContent = 'RUN ↗';
  }
}
checkForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const value = new FormData(checkForm).get('url')?.trim();
  if (value) runCheck(normalizeInputUrl(value));
});
document.querySelectorAll('.demo-presets [data-url]').forEach((button) => {
  button.addEventListener('click', () => {
    const isCheckMode = !checkForm.hidden;
    if (!isCheckMode) demoModeTabs.find((tab) => tab.dataset.mode === 'check')?.click();
    const url = button.dataset.url;
    document.querySelector('#inline-check-url').value = url;
    runCheck(url);
  });
});
manualCertToggle.addEventListener('change', () => {
  manualCertInput.hidden = !manualCertToggle.checked;
  manualCertInput.required = manualCertToggle.checked;
  if (!manualCertToggle.checked) manualCertInput.value = '';
});
registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!registerForm.reportValidity()) return;
  const submit = registerForm.querySelector('button[type="submit"]');
  const form = new FormData(registerForm);
  const url = normalizeInputUrl(form.get('url'));
  const metadata = form.get('metadata')?.trim() || '';
  const certFingerprint = manualCertToggle.checked ? form.get('cert_fingerprint')?.trim() : '';
  submit.disabled = true;
  submit.textContent = 'REGISTERING…';
  resultTitle.textContent = 'TRUST REGISTRATION';
  resultModeLabel.textContent = 'LEDGER WRITE';
  demoDetails.hidden = true;
  verdictValue.textContent = 'Registering…';
  verdictScore.textContent = '—';
  verdictPill.textContent = 'IN PROGRESS';
  showMessage('Collecting the certificate and submitting the trust record to the configured ledger…');
  setSteps([
    { title: 'Normalize the domain', detail: 'Preparing canonical URL', state: 'RUNNING' },
    { title: 'Compute SHA-256', detail: 'Preparing domain key', state: 'WAITING' },
    { title: 'Inspect live TLS', detail: certFingerprint ? 'Using supplied certificate fingerprint' : 'Fetching live certificate', state: 'WAITING' },
    { title: 'Write trust record', detail: 'Configured ledger', state: 'WAITING' },
    { title: 'Attach proof', detail: 'Transaction and Merkle state', state: 'WAITING' },
  ]);
  try {
    const payload = { url, metadata };
    if (certFingerprint) payload.cert_fingerprint = certFingerprint;
    const data = await apiRequest('/api/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    verdictLabel.textContent = 'REGISTRATION';
    verdictValue.textContent = 'Trust record created';
    verdictPill.textContent = 'REGISTERED';
    verdictPill.dataset.state = 'success';
    verdictScore.textContent = '100';
    setSteps([
      { title: 'Normalize the domain', detail: data.domain || data.url, state: 'DONE' },
      { title: 'Compute SHA-256', detail: data.url_hash || 'Hash recorded', state: 'DONE' },
      { title: 'Inspect live TLS', detail: data.cert_fingerprint || 'Fingerprint recorded', state: 'DONE' },
      { title: 'Write trust record', detail: 'Saved to configured ledger', state: 'DONE' },
      { title: 'Attach proof', detail: data.transaction?.block_number ? `Block #${data.transaction.block_number}` : 'Transaction returned', state: 'DONE' },
    ]);
    showMessage(data.message || 'Trust record saved to the configured ledger.', 'success');
    showRegistrationDetails(data);
  } catch (error) {
    verdictValue.textContent = 'Registration failed';
    verdictPill.textContent = 'NOT REGISTERED';
    verdictPill.dataset.state = 'danger';
    verdictScore.textContent = '—';
    showMessage(error.message, 'error');
    setSteps(STEP_TITLES.map((title) => ({ title, detail: 'Registration did not complete', state: 'ERROR' })));
  } finally {
    submit.disabled = false;
    submit.textContent = 'REGISTER TRUST ↗';
  }
});
demoModeTabs.forEach((button) => {
  button.addEventListener('click', () => {
    const recordMode = button.dataset.mode === 'record';
    demoModeTabs.forEach((tab) => {
      const selected = tab === button;
      tab.classList.toggle('is-active', selected);
      tab.setAttribute('aria-selected', String(selected));
    });
    checkForm.hidden = recordMode;
    registerForm.hidden = !recordMode;
    document.querySelector('.demo-presets').hidden = recordMode;
    resultTitle.textContent = recordMode ? 'TRUST REGISTRATION' : 'VERIFICATION PIPELINE';
    resultModeLabel.textContent = recordMode ? 'LEDGER WRITE' : '5 LIVE CHECKS';
    demoDetails.hidden = true;
    verdictLabel.textContent = recordMode ? 'REGISTRATION' : 'TRUST ASSESSMENT';
    verdictValue.textContent = 'Not checked';
    verdictScore.textContent = '—';
    verdictPill.textContent = 'AWAITING URL';
    verdictPill.dataset.state = 'neutral';
    showMessage(recordMode ? 'Save a domain, its live or supplied TLS fingerprint, and optional label to the configured ledger.' : 'Enter a URL, choose a quick check, or register a trust record. Pipeline evidence appears here after each run.');
setSteps(recordMode ? [
      { title: 'Check verifier access', detail: 'Configured validator', state: 'READY' },
      { title: 'Hash the domain', detail: 'SHA-256 domain key', state: 'READY' },
      { title: 'Attach TLS fingerprint', detail: 'Live or supplied X.509 fingerprint', state: 'READY' },
      { title: 'Write trust record', detail: 'Configured ledger', state: 'READY' },
      { title: 'Attach proof', detail: 'Transaction and Merkle state', state: 'READY' },
    ] : []);
  });
});
apiRequest('/api/status').then((data) => {
  setBackendStatus('online');
  backendStatus.title = data.blockchain?.mode ? `Chain mode: ${data.blockchain.mode}` : 'Baty backend connected';
}).catch(() => {
  setBackendStatus('offline');
  backendStatus.title = 'Run python Parallel/run_demo.py to enable live checks';
});
document.querySelector('.copy-code').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  const visible = document.querySelector('.code-sample.is-visible');
  try {
    await navigator.clipboard.writeText(visible.innerText);
    button.innerHTML = 'COPIED <span>✓</span>';
  } catch {
    button.innerHTML = 'SELECT CODE <span>↗</span>';
  }
  window.setTimeout(() => { button.innerHTML = 'COPY <span>▣</span>'; }, 1500);
});
