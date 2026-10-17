'use strict';

const val = id => document.getElementById(id).value;
document.body.classList.add('landing-mode');

document.getElementById('analyze-message').addEventListener('click', () =>
  submitForm('/api/message', {text: val('msg'), sender: val('sender')}, 'out-message'));
document.getElementById('analyze-url').addEventListener('click', () =>
  submitForm('/api/url', {url: val('urlvalue')}, 'out-url'));
document.getElementById('ask-assistant').addEventListener('click', () =>
  submitForm(document.getElementById('use-modal-model').checked ? '/api/modal/assistant' : '/api/assistant', {
    question: val('question'), include_local_records: document.getElementById('include-local-records').checked
  }, 'out-assistant'));
document.getElementById('search-incidents').addEventListener('click', () =>
  submitForm('/api/incidents', {description: val('incident')}, 'out-incidents'));

function showWorkspaceTab(name) {
  document.body.classList.toggle('landing-mode', name === 'home');
  document.querySelectorAll('#workspace>section').forEach(section =>
    section.classList.toggle('hidden', section.id !== name));
  document.querySelectorAll('.sidebar nav button[data-tab]').forEach(button =>
    button.classList.toggle('active', button.dataset.tab === name));
  if (name === 'research' && window.researchTab) window.researchTab('search');
  window.scrollTo({top: 0, behavior: 'smooth'});
}

document.querySelectorAll('.sidebar nav button[data-tab]').forEach(button =>
  button.addEventListener('click', () => showWorkspaceTab(button.dataset.tab)));
showWorkspaceTab('home');
document.querySelectorAll('[data-open-tab]').forEach(button =>
  button.addEventListener('click', event => {
    event.preventDefault();
    showWorkspaceTab(button.dataset.openTab);
  }));
document.querySelectorAll('[data-open-research]').forEach(button =>
  button.addEventListener('click', () => {
    showWorkspaceTab('research');
    if (window.researchTab) window.researchTab(button.dataset.openResearch);
  }));

const researchExamples = {
  search: ['Find current public security information with ranked sources and publication details.', 'Search recent vendor advisories for actively exploited VPN vulnerabilities', 'search', 'Search'],
  answers: ['Ask a question and receive a synthesized answer with live-web citations.', 'What mitigations do vendors currently recommend for this exposed vulnerability?', 'answers', 'Responses'],
  extract: ['Extract relevant information from a public security advisory or URL.', 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog', 'extract', 'Extract'],
  tasks: ['Delegate a longer investigation and receive a structured report with sources.', 'Research ransomware campaigns targeting healthcare and summarize verified mitigations.', 'tasks', 'Deep Research'],
  findall: ['Discover entities using structured match criteria and inspect supporting sources.', 'FindAll actively exploited vulnerabilities affecting internet-facing VPN products', 'findall', 'FindAll'],
  monitors: ['Watch for new public events matching a security query.', 'New security advisories for products in our technology stack', 'monitors', 'Monitor']
};
document.querySelectorAll('[data-home-research]').forEach(button => button.addEventListener('click', () => {
  const item = researchExamples[button.dataset.homeResearch];
  if (!item) return;
  document.querySelectorAll('[data-home-research]').forEach(tab => tab.classList.toggle('selected', tab === button));
  document.getElementById('playground-desc').textContent = item[0];
  document.getElementById('playground-example').textContent = item[1];
  const action = document.querySelector('.playground-prompt button');
  action.dataset.openResearch = item[2];
  action.textContent = 'Try ' + item[3] + ' ↗';
}));

document.getElementById('landing-account').addEventListener('click', () =>
  document.getElementById('account-shortcut').click());
document.getElementById('account-shortcut').addEventListener('click', () => showWorkspaceTab('account'));

fetch('/api/health').then(response => response.json()).then(status => {
  const ready = status.model_available && status.model_runtime_available;
  const detail = ready
    ? (status.adapter_enabled ? 'Local Qwen runtime ready · adapter enabled' : 'Local Qwen runtime ready · base model')
    : 'Local model or MLX runtime unavailable';
  const model = document.getElementById('model-status');
  if (model) model.textContent = detail;
  const landing = document.getElementById('landing-model-status');
  if (landing) landing.textContent = detail;
  const workspace = document.getElementById('workspace-status');
  if (workspace) workspace.textContent = ready ? 'Local model ready' : 'Local service ready';
}).catch(() => {
  const model = document.getElementById('model-status');
  if (model) model.textContent = 'Local service unavailable';
  const landing = document.getElementById('landing-model-status');
  if (landing) landing.textContent = 'Local service unavailable';
  const workspace = document.getElementById('workspace-status');
  if (workspace) workspace.textContent = 'Local service unavailable';
});

async function submitForm(path, payload, target) {
  const box = document.getElementById(target);
  box.textContent = path === '/api/modal/assistant'
    ? 'Sending question to the authenticated Modal model…'
    : 'Analyzing locally…';
  try {
    const headers = {'Content-Type': 'application/json'};
    if (path === '/api/modal/assistant') {
      if (!window.firebaseCloud) throw new Error('Firebase sign-in is not ready.');
      headers.Authorization = `Bearer ${await window.firebaseCloud.getIdToken()}`;
    }
    const response = await fetch(path, {method: 'POST', headers, body: JSON.stringify(payload)});
    const result = await response.json();
    box.textContent = JSON.stringify(result, null, 2);
    if ((path === '/api/assistant' || path === '/api/modal/assistant') &&
        typeof result.answer === 'string' && window.firebaseCloud) {
      try {
        await window.firebaseCloud.saveAssistantExchange({
          question: payload.question, answer: result.answer, answerBasis: result.answer_basis
        });
      } catch (error) {
        document.getElementById('cloud-sync-status').textContent =
          `Answer completed, but Firebase backup failed (${typeof error?.code === 'string' ? error.code : 'unknown error'}).`;
      }
    }
  } catch (error) {
    box.textContent = error?.message || 'Local service unavailable.';
  }
}

document.getElementById('use-modal-model').addEventListener('change', event => {
  const useModal = event.target.checked;
  document.getElementById('ask-assistant').textContent = useModal ? 'Send to Modal' : 'Run locally';
  document.getElementById('modal-disclosure').textContent = useModal
    ? 'Your question, including any OCR text you add, is sent to Modal for cloud inference; the image itself is not. The Firebase sign-in token is forwarded only to authenticate the request. Modal answers are unverified. Local retrieval and database backup are separate choices.'
    : 'Local model is selected. Cloud inference sends the question to Modal only when selected; the Firebase sign-in token is used only for authentication. OCR images are processed locally and not sent.';
});
