// Web Research module — vanilla JS, matches existing app.js style.
// Handles: provider status, search, URL extraction, deep research tasks, monitors.
// Never fabricates data; shows real API responses or clear error states.

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function get(id) { return document.getElementById(id); }
  function val(id) { return (get(id) || {}).value || ''; }

  async function apiPost(path, payload) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return r.json();
  }

  async function apiGet(path) {
    const r = await fetch(path);
    return r.json();
  }

  function fmt(obj) {
    return JSON.stringify(obj, null, 2);
  }

  function setLoading(id, msg) {
    const el = get(id);
    if (el) el.textContent = msg || 'Working…';
  }

  function isSafeUrl(url) {
    if (typeof url !== 'string') return false;
    const lower = url.trim().toLowerCase();
    return lower.startsWith('https://') || lower.startsWith('http://');
  }

  function createSafeLink(url, label) {
    if (!isSafeUrl(url)) {
      return document.createTextNode(label || url || '');
    }
    const a = document.createElement('a');
    a.href = url.trim();
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = label || url;
    a.style.color = '#1b6ca8';
    a.style.textDecoration = 'underline';
    return a;
  }

  // ---------------------------------------------------------------------------
  // Sub-tab switching inside the research section
  // ---------------------------------------------------------------------------
  const PANELS = ['search', 'answers', 'findall', 'extract', 'tasks', 'monitors', 'enrich'];

  window.researchTab = function (name) {
    PANELS.forEach(function (p) {
      const panel = get('rpanel-' + p);
      const tab = get('rtab-' + p);
      if (panel) panel.classList.toggle('hidden', p !== name);
      if (tab) tab.classList.toggle('active', p === name);
    });
    if (name === 'monitors') loadMonitors();
    if (name === 'tasks') loadTaskHistory();
  };

  function renderTaskHistory(container, tasks) {
    container.replaceChildren();
    if (!tasks.length) return;
    const heading = document.createElement('h3');
    heading.textContent = 'Recent tasks';
    container.appendChild(heading);
    tasks.slice(0, 10).forEach(function (task) {
      const row = document.createElement('div');
      row.style.cssText = 'padding:.5rem;border-bottom:1px solid #eee;font-size:.9rem';
      const status = document.createElement('strong');
      status.textContent = '[' + (task.status || 'unknown') + '] ';
      status.style.color = task.status === 'completed' ? '#1a7a1a' : task.status === 'failed' ? '#a00' : '#555';
      row.append(status, document.createTextNode((task.question || '').substring(0, 80)));
      const detail = document.createElement('small');
      detail.textContent = 'ID: ' + (task.task_id || '') + ' | ' + (task.created_at || '').substring(0, 10);
      const view = document.createElement('button');
      view.textContent = 'View report';
      view.style.cssText = 'font-size:.8rem;padding:.2rem .45rem;margin-left:.5rem';
      view.addEventListener('click', function () {
        researchTab('tasks');
        const target = get('r-task-out');
        target.textContent = 'Loading saved report…';
        apiGet('/api/research/tasks/' + encodeURIComponent(task.task_id)).then(function (report) {
          renderTaskRecord(target, report);
        }).catch(function () { target.textContent = 'Could not load saved report.'; });
      });
      row.append(document.createElement('br'), detail, view);
      container.appendChild(row);
    });
  }

  function renderMonitors(container, monitors, note) {
    container.replaceChildren();
    if (!monitors.length) {
      const empty = document.createElement('small');
      empty.textContent = 'No monitors configured. Create one above.';
      container.appendChild(empty);
    }
    monitors.forEach(function (monitor) {
      const row = document.createElement('div');
      row.style.cssText = 'padding:.6rem;border-bottom:1px solid #eee;font-size:.9rem';
      const remove = document.createElement('button');
      remove.textContent = 'Delete';
      remove.style.cssText = 'float:right;font-size:.8rem;padding:.2rem .5rem';
      remove.addEventListener('click', function () { deleteMonitor(monitor.monitor_id); });
      const eventsButton = document.createElement('button');
      eventsButton.textContent = 'Check for updates';
      eventsButton.style.cssText = 'float:right;font-size:.8rem;padding:.2rem .5rem;margin-right:.35rem';
      const eventsBox = document.createElement('pre');
      eventsBox.hidden = true;
      eventsButton.addEventListener('click', function () {
        eventsBox.hidden = false;
        eventsBox.textContent = 'Checking provider events…';
        apiGet('/api/research/monitors/' + encodeURIComponent(monitor.monitor_id) + '/events')
          .then(function (data) {
            eventsBox.replaceChildren();
            if (data.error) { eventsBox.textContent = 'Error: ' + data.error; return; }
            const events = data.events || [];
            if (!events.length) {
              eventsBox.textContent = data.note || 'No new events found.';
              if (data.limitations && data.limitations.length) {
                eventsBox.appendChild(document.createTextNode('\n\nLimitations:\n'));
                data.limitations.forEach(function (l) {
                  eventsBox.appendChild(document.createTextNode('  • ' + l + '\n'));
                });
              }
              return;
            }
            events.forEach(function (event, index) {
              eventsBox.appendChild(document.createTextNode((index + 1) + '. ' + (event.event_date || 'Date unavailable') + '\n'));
              if (event.content) {
                eventsBox.appendChild(document.createTextNode(event.content + '\n'));
              }
              (event.sources || []).forEach(function (source) {
                eventsBox.appendChild(document.createTextNode('Source: ' + (source.title || '') + ' '));
                if (source.url) {
                  eventsBox.appendChild(createSafeLink(source.url, source.url));
                }
                eventsBox.appendChild(document.createTextNode('\n'));
              });
              eventsBox.appendChild(document.createTextNode('\n'));
            });
            if (data.limitations && data.limitations.length) {
              eventsBox.appendChild(document.createTextNode('Limitations:\n'));
              data.limitations.forEach(function (l) {
                eventsBox.appendChild(document.createTextNode('  • ' + l + '\n'));
              });
            }
          })
          .catch(function () { eventsBox.textContent = 'Could not retrieve monitor events.'; });
      });
      const label = document.createElement('strong');
      label.textContent = (monitor.query || '').substring(0, 80);
      const detail = document.createElement('small');
      detail.textContent = 'ID: ' + (monitor.monitor_id || '') + ' | Status: ' + (monitor.status || 'unknown') +
        ' | Provider: ' + (monitor.provider || 'unknown') +
        (monitor.last_event_at ? ' | Last event: ' + monitor.last_event_at.substring(0, 10) : '');
      row.append(remove, eventsButton, label, document.createElement('br'), detail, eventsBox);
      container.appendChild(row);
    });
    if (note) {
      const noteEl = document.createElement('small');
      noteEl.style.color = '#52616b';
      noteEl.textContent = note;
      container.append(document.createElement('br'), noteEl);
    }
  }

  // ---------------------------------------------------------------------------
  // Provider status
  // ---------------------------------------------------------------------------
  function loadProviderStatus() {
    apiGet('/api/research/status').then(function (data) {
      const note = get('research-provider-note');
      if (!note) return;
      if (data.error) {
        note.textContent = 'Provider status unavailable.';
        return;
      }
      const mode = data.mode === 'live-web'
        ? '🌐 Live web research active (Parallel.ai).'
        : '💾 Local-only mode — no PARALLEL_API_KEY configured. Research uses local corpus only.';
      note.textContent = mode;
    }).catch(function () {
      const note = get('research-provider-note');
      if (note) note.textContent = 'Provider status unavailable.';
    });
  }

  // ---------------------------------------------------------------------------
  // Feature A: Search
  // ---------------------------------------------------------------------------
  function initSearch() {
    const btn = get('r-search-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const query = val('r-query').trim();
      if (!query) { get('r-search-out').textContent = 'Please enter a query.'; return; }

      const kwRaw = val('r-keywords').trim();
      const searchQueries = kwRaw
        ? kwRaw.split(',').map(function (s) { return s.trim(); }).filter(Boolean).slice(0, 3)
        : undefined;

      setLoading('r-search-out', 'Searching…');
      btn.disabled = true;

      apiPost('/api/research/search', {
        query: query,
        search_queries: searchQueries,
        max_results: 10
      }).then(function (data) {
        btn.disabled = false;
        renderSearchResults(get('r-search-out'), data);
      }).catch(function () {
        btn.disabled = false;
        get('r-search-out').textContent = 'Local service unavailable.';
      });
    });
  }

  function initQuickAnswer() {
    const btn = get('r-answer-btn');
    const out = get('r-answer-out');
    if (!btn || !out) return;
    btn.addEventListener('click', function () {
      const question = val('r-answer-question').trim();
      if (!question) { out.textContent = 'Enter a question first.'; return; }
      btn.disabled = true;
      out.textContent = 'Researching live sources with Parallel. This may take up to about a minute…';
      apiPost('/api/research/responses', {
        question: question,
        effort: val('r-answer-effort') || 'low'
      }).then(function (data) {
        out.replaceChildren();
        if (data.error) { out.textContent = data.error; return; }
        const answer = document.createElement('p');
        answer.style.whiteSpace = 'pre-wrap';
        answer.textContent = data.answer || 'No answer text was returned.';
        out.appendChild(answer);
        const citations = Array.isArray(data.citations) ? data.citations : [];
        if (citations.length) {
          const heading = document.createElement('strong');
          heading.textContent = 'Sources supplied by Parallel';
          const list = document.createElement('ul');
          citations.forEach(function (source) {
            if (!source || typeof source.url !== 'string') return;
            const item = document.createElement('li');
            item.appendChild(createSafeLink(source.url, source.title || source.url));
            list.appendChild(item);
          });
          out.append(heading, list);
        } else {
          const noSources = document.createElement('p');
          noSources.textContent = 'No citation annotations were returned. Treat this answer as unverified.';
          out.appendChild(noSources);
        }
        (data.limitations || []).forEach(function (limitation) {
          const note = document.createElement('small');
          note.style.display = 'block';
          note.textContent = limitation;
          out.appendChild(note);
        });
      }).catch(function () {
        out.textContent = 'Local service unavailable.';
      }).finally(function () { btn.disabled = false; });
    });
  }

  function initFindAll() {
    const prepare = get('r-findall-ingest-btn');
    const start = get('r-findall-run-btn');
    const out = get('r-findall-out');
    if (!prepare || !start || !out) return;
    get('r-findall-generator').addEventListener('change', function () {
      const preview = val('r-findall-generator') === 'preview';
      get('r-findall-limit').min = preview ? '5' : '1';
      get('r-findall-limit').max = preview ? '10' : '25';
      if (preview && Number(val('r-findall-limit')) < 5) get('r-findall-limit').value = '5';
      if (!preview && Number(val('r-findall-limit')) > 25) get('r-findall-limit').value = '25';
    });
    prepare.addEventListener('click', function () {
      const objective = val('r-findall-objective').trim();
      if (!objective) { out.textContent = 'Enter a discovery objective first.'; return; }
      prepare.disabled = true;
      out.textContent = 'Preparing suggested criteria…';
      apiPost('/api/research/findall/ingest', { objective: objective }).then(function (schema) {
        prepare.disabled = false;
        if (schema.error) { out.textContent = schema.error; return; }
        get('r-findall-entity').value = schema.entity_type || '';
        get('r-findall-conditions').value = JSON.stringify(schema.match_conditions || [], null, 2);
        get('r-findall-generator').value = 'preview';
        get('r-findall-schema').classList.remove('hidden');
        out.textContent = 'Review and edit the suggested criteria before starting the run.';
      }).catch(function () {
        prepare.disabled = false;
        out.textContent = 'Local service unavailable.';
      });
    });
    start.addEventListener('click', function () {
      const objective = val('r-findall-objective').trim();
      let conditions;
      try { conditions = JSON.parse(val('r-findall-conditions')); }
      catch (_) { out.textContent = 'Match conditions must be valid JSON.'; return; }
      const limit = Number(val('r-findall-limit')) || 5;
      const generator = val('r-findall-generator') || 'preview';
      start.disabled = true;
      out.textContent = 'Starting FindAll. Polling for candidate matches…';
      apiPost('/api/research/findall/runs', {
        objective: objective, entity_type: val('r-findall-entity').trim(),
        match_conditions: conditions, generator: generator, match_limit: limit
      }).then(function (data) {
        start.disabled = false;
        if (data.error) { out.textContent = data.error; return; }
        if (!data.findall_id) { renderFindAll(out, data); return; }
        renderFindAll(out, data);
        pollFindAll(data.findall_id, 0);
      }).catch(function () {
        start.disabled = false;
        out.textContent = 'Local service unavailable.';
      });
    });
  }

  function renderFindAll(container, data) {
    container.replaceChildren();
    const run = data.result && data.result.run ? data.result.run : data;
    const state = run.status && typeof run.status === 'object' ? run.status.status : run.status;
    const heading = document.createElement('strong');
    heading.textContent = 'FindAll status: ' + (state || 'submitted');
    container.appendChild(heading);
    const counts = run.status && run.status.metrics;
    if (counts) {
      const metric = document.createElement('p');
      metric.textContent = 'Candidates generated: ' + (counts.generated_candidates_count || 0) +
        ' · matches: ' + (counts.matched_candidates_count || 0);
      container.appendChild(metric);
    }
    const snapshot = data.result && data.result.candidates ? data.result : null;
    if (!snapshot || !snapshot.candidates || !snapshot.candidates.length) {
      const note = document.createElement('p');
      note.textContent = state === 'completed' ? 'No candidates were returned.' : 'Waiting for candidates…';
      container.appendChild(note);
      return;
    }
    snapshot.candidates.slice(0, 50).forEach(function (candidate) {
      const card = document.createElement('article');
      card.style.cssText = 'margin-top:.8rem;padding:.8rem;border:1px solid #e1e5e9;border-radius:.6rem';
      const title = document.createElement('strong');
      title.textContent = (candidate.name || 'Unnamed entity') + ' · ' + (candidate.match_status || 'unverified');
      card.appendChild(title);
      if (candidate.url) {
        card.appendChild(document.createElement('br'));
        card.appendChild(createSafeLink(candidate.url, candidate.url));
      }
      if (candidate.description) {
        const desc = document.createElement('p');
        desc.textContent = candidate.description;
        card.appendChild(desc);
      }
      if (candidate.output && typeof candidate.output === 'object') {
        const fields = document.createElement('ul');
        Object.keys(candidate.output).forEach(function (key) {
          const value = candidate.output[key];
          const row = document.createElement('li');
          row.textContent = key + ': ' + (value && typeof value === 'object' ? (value.value || JSON.stringify(value)) : String(value));
          fields.appendChild(row);
        });
        card.appendChild(fields);
      }
      (candidate.basis || []).forEach(function (basis) {
        (basis.citations || []).forEach(function (citation) {
          const source = document.createElement('p');
          source.appendChild(createSafeLink(citation.url, citation.title || citation.url || 'Source'));
          if (citation.excerpts && citation.excerpts.length) {
            source.appendChild(document.createTextNode(' — ' + citation.excerpts.join(' ').slice(0, 500)));
          }
          card.appendChild(source);
        });
      });
      container.appendChild(card);
    });
  }

  function pollFindAll(findallId, attempts) {
    if (attempts >= 60) { setLoading('r-findall-out', 'Run is still active. Poll again later using this run ID: ' + findallId); return; }
    setTimeout(function () {
      apiGet('/api/research/findall/runs/' + encodeURIComponent(findallId) + '?include_result=1')
        .then(function (data) {
          if (data.error) { setLoading('r-findall-out', data.error); return; }
          renderFindAll(get('r-findall-out'), data);
          const state = data.status && typeof data.status === 'object' ? data.status.status : data.status;
          if (!['completed', 'failed', 'cancelled', 'error'].includes(state)) pollFindAll(findallId, attempts + 1);
        }).catch(function () { pollFindAll(findallId, attempts + 1); });
    }, 5000);
  }

  function renderSearchResults(container, data) {
    if (!container) return;
    container.replaceChildren();
    if (!data) return;
    if (data.error) {
      container.textContent = 'Error: ' + data.error;
      return;
    }
    if (!data.results || data.results.length === 0) {
      const emptyMsg = 'No results found.' +
        (data.limitations && data.limitations.length ? '\n\nLimitations:\n' + data.limitations.map(function (l) { return '  • ' + l; }).join('\n') : '');
      container.textContent = emptyMsg;
      return;
    }
    container.appendChild(document.createTextNode(
      'Provider: ' + (data.provider || 'unknown') + '\nResults: ' + (data.total_results != null ? data.total_results : data.results.length) + '\n\n'
    ));
    data.results.forEach(function (r, i) {
      container.appendChild(document.createTextNode((i + 1) + '. ' + (r.title || 'Untitled') + '\n   URL: '));
      if (r.url) {
        container.appendChild(createSafeLink(r.url, r.url));
        container.appendChild(document.createTextNode('\n'));
      } else {
        container.appendChild(document.createTextNode('N/A\n'));
      }
      if (r.publish_date) {
        container.appendChild(document.createTextNode('   Published: ' + r.publish_date + '\n'));
      }
      if (r.source_domain) {
        container.appendChild(document.createTextNode('   Source: ' + r.source_domain + '\n'));
      }
      const excerpts = r.excerpts || [];
      if (excerpts.length) {
        container.appendChild(document.createTextNode('   ' + excerpts[0].substring(0, 300) + '\n'));
      }
      container.appendChild(document.createTextNode('\n'));
    });
    if (data.limitations && data.limitations.length) {
      container.appendChild(document.createTextNode('Limitations:\n'));
      data.limitations.forEach(function (l) {
        container.appendChild(document.createTextNode('  • ' + l + '\n'));
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Feature B: Extract
  // ---------------------------------------------------------------------------
  function initExtract() {
    const btn = get('r-extract-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const url = val('r-extract-url').trim();
      if (!url) { get('r-extract-out').textContent = 'Please enter a URL.'; return; }

      setLoading('r-extract-out', 'Extracting…');
      btn.disabled = true;

      apiPost('/api/research/extract', {
        urls: [url],
        objective: val('r-extract-obj').trim() || undefined
      }).then(function (data) {
        btn.disabled = false;
        renderExtractResult(get('r-extract-out'), data);
      }).catch(function () {
        btn.disabled = false;
        get('r-extract-out').textContent = 'Local service unavailable.';
      });
    });
  }

  function renderExtractResult(container, data) {
    if (!container) return;
    container.replaceChildren();
    if (!data) return;
    if (data.error) {
      container.textContent = 'Error: ' + data.error;
      return;
    }
    container.appendChild(document.createTextNode('Provider: ' + (data.provider || 'unknown') + '\n\n'));
    const results = data.results || [];
    const errors = data.errors || [];

    if (results.length === 0 && errors.length > 0) {
      errors.forEach(function (e) {
        container.appendChild(document.createTextNode('REJECTED: ' + e.url + '\n  Reason: ' + (e.error || 'unknown') + '\n'));
      });
    }

    results.forEach(function (r) {
      container.appendChild(document.createTextNode('URL: '));
      if (r.url) {
        container.appendChild(createSafeLink(r.url, r.url));
        container.appendChild(document.createTextNode('\n'));
      } else {
        container.appendChild(document.createTextNode('N/A\n'));
      }
      if (r.title) container.appendChild(document.createTextNode('Title: ' + r.title + '\n'));
      if (r.publish_date) container.appendChild(document.createTextNode('Published: ' + r.publish_date + '\n'));
      container.appendChild(document.createTextNode('\n'));

      const excerpts = r.excerpts || [];
      if (excerpts.length) {
        container.appendChild(document.createTextNode('Excerpts:\n'));
        excerpts.forEach(function (e) {
          container.appendChild(document.createTextNode('  ' + e.substring(0, 500) + '\n'));
        });
      }
      if (r.full_content && !excerpts.length) {
        container.appendChild(document.createTextNode('Content (first 1000 chars):\n' + r.full_content.substring(0, 1000) + '\n'));
      }
      if (r.error) container.appendChild(document.createTextNode('Error: ' + r.error + '\n'));
      container.appendChild(document.createTextNode('\n'));
    });

    if (data.limitations && data.limitations.length) {
      container.appendChild(document.createTextNode('Limitations:\n'));
      data.limitations.forEach(function (l) {
        container.appendChild(document.createTextNode('  • ' + l + '\n'));
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Feature C: Deep Research Tasks
  // ---------------------------------------------------------------------------
  function initTasks() {
    const btn = get('r-task-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const question = val('r-task-q').trim();
      if (!question) { get('r-task-out').textContent = 'Please enter a research question.'; return; }

      const processor = val('r-task-proc') || 'pro';
      setLoading('r-task-out', 'Creating research task…');
      btn.disabled = true;

      apiPost('/api/research/tasks', {
        question: question,
        processor: processor
      }).then(function (data) {
        btn.disabled = false;
        renderTaskRecord(get('r-task-out'), data);
        loadTaskHistory();

        // If task is already completed (local mode), done.
        if (data.status === 'completed' || data.status === 'failed') return;

        // Start polling for live tasks
        if (data.task_id) pollTask(data.task_id, 0);
      }).catch(function () {
        btn.disabled = false;
        get('r-task-out').textContent = 'Local service unavailable.';
      });
    });
  }

  function pollTask(taskId, attempts) {
    if (attempts > 120) {  // 10 minutes at 5s intervals
      setLoading('r-task-out', 'Task is still running. Check task history for updates.');
      loadTaskHistory();
      return;
    }
    setTimeout(function () {
      apiGet('/api/research/tasks/' + taskId).then(function (data) {
        const out = get('r-task-out');
        renderTaskRecord(out, data);
        loadTaskHistory();
        if (data.status !== 'completed' && data.status !== 'failed' && data.status !== 'cancelled') {
          pollTask(taskId, attempts + 1);
        }
      }).catch(function () {
        // Network error during poll — retry
        pollTask(taskId, attempts + 1);
      });
    }, 5000);
  }

  function renderTaskRecord(container, data) {
    if (!container) return;
    container.replaceChildren();
    if (!data) return;
    if (data.error) {
      container.textContent = 'Error: ' + data.error;
      return;
    }
    const lines = [
      'Task ID: ' + (data.task_id || 'N/A'),
      'Status: ' + (data.status || 'unknown'),
      'Provider: ' + (data.provider || 'N/A'),
      'Processor: ' + (data.processor || 'N/A'),
      'Created: ' + (data.created_at || 'N/A'),
      ''
    ];
    if (data.error_message) lines.push('Error: ' + data.error_message, '');
    container.appendChild(document.createTextNode(lines.join('\n') + '\n'));

    const result = data.result;
    if (result) {
      if (result.summary) {
        container.appendChild(document.createTextNode('=== Research Summary ===\n' + result.summary + '\n\n'));
      }
      const sources = result.sources || [];
      if (sources.length) {
        container.appendChild(document.createTextNode('=== Sources ===\n'));
        sources.forEach(function (s, i) {
          container.appendChild(document.createTextNode((i + 1) + '. ' + (s.title || s.url || 'N/A') + '\n   '));
          if (s.url) {
            container.appendChild(createSafeLink(s.url, s.url));
            container.appendChild(document.createTextNode('\n'));
          } else {
            container.appendChild(document.createTextNode('N/A\n'));
          }
          if (s.published_at) {
            container.appendChild(document.createTextNode('   Published: ' + s.published_at + '\n'));
          }
        });
        container.appendChild(document.createTextNode('\n'));
      }
      if (result.limitations && result.limitations.length) {
        container.appendChild(document.createTextNode('Limitations:\n'));
        result.limitations.forEach(function (l) {
          container.appendChild(document.createTextNode('  • ' + l + '\n'));
        });
      }
    }
  }

  function loadTaskHistory() {
    const container = get('r-task-history');
    if (!container) return;
    apiGet('/api/research/tasks').then(function (data) {
      renderTaskHistory(container, data.error || !data.tasks ? [] : data.tasks);
    }).catch(function () {});
  }

  // ---------------------------------------------------------------------------
  // Feature D: Monitors
  // ---------------------------------------------------------------------------
  function initMonitors() {
    const btn = get('r-monitor-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const query = val('r-monitor-q').trim();
      if (!query) return;
      btn.disabled = true;
      apiPost('/api/research/monitors', { query: query }).then(function (data) {
        btn.disabled = false;
        if (data.error) {
          alert('Error: ' + data.error);
          return;
        }
        get('r-monitor-q').value = '';
        loadMonitors();
      }).catch(function () {
        btn.disabled = false;
      });
    });
  }

  function loadMonitors() {
    const container = get('r-monitors-list');
    if (!container) return;
    container.textContent = 'Loading…';
    apiGet('/api/research/monitors').then(function (data) {
      if (data.error) {
        container.textContent = 'Could not load monitors: ' + data.error;
        return;
      }
      renderMonitors(container, data.monitors || [], data.note);
    }).catch(function () {
      container.textContent = 'Could not load monitors.';
    });
  }

  function deleteMonitor(monitorId) {
    if (!confirm('Delete this monitor?')) return;
    apiPost('/api/research/monitors/' + monitorId + '/delete', {}).then(function (data) {
      if (data.error) { alert('Error: ' + data.error); return; }
      loadMonitors();
    }).catch(function () {});
  };

  function initEnrichment() {
    const btn = get('r-enrich-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const record = {};
      [['title', 'r-enrich-title'], ['id', 'r-enrich-id'], ['vendor', 'r-enrich-vendor'],
        ['product', 'r-enrich-product'], ['description', 'r-enrich-description'],
        ['source_url', 'r-enrich-source']].forEach(function (field) {
        const value = val(field[1]).trim();
        if (value) record[field[0]] = value;
      });
      const fields = Array.from(document.querySelectorAll('[data-enrich-field]:checked'))
        .map(function (item) { return item.dataset.enrichField; });
      const out = get('r-enrich-out');
      out.textContent = 'Submitting public record fields for enrichment…';
      btn.disabled = true;
      apiPost('/api/research/enrich', { record: record, fields: fields, processor: 'base' })
        .then(function (data) {
          btn.disabled = false;
          renderTaskRecord(out, data);
          if (data.task_id && data.status !== 'completed' && data.status !== 'failed') {
            pollTaskInto(data.task_id, 'r-enrich-out', 0);
          }
        })
        .catch(function () { btn.disabled = false; out.textContent = 'Local service unavailable.'; });
    });
  }

  function pollTaskInto(taskId, targetId, attempts) {
    if (attempts > 120) { setLoading(targetId, 'Task is still running. Check task history for updates.'); return; }
    setTimeout(function () {
      apiGet('/api/research/tasks/' + encodeURIComponent(taskId)).then(function (data) {
        const target = get(targetId);
        renderTaskRecord(target, data);
        if (data.status !== 'completed' && data.status !== 'failed' && data.status !== 'cancelled') {
          pollTaskInto(taskId, targetId, attempts + 1);
        }
      }).catch(function () { pollTaskInto(taskId, targetId, attempts + 1); });
    }, 5000);
  }

  // ---------------------------------------------------------------------------
  // Initialise
  // ---------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-research-tab]').forEach(function (tab) {
      tab.addEventListener('click', function () { researchTab(tab.dataset.researchTab); });
    });
    loadProviderStatus();
    initSearch();
    initQuickAnswer();
    initFindAll();
    initExtract();
    initTasks();
    initMonitors();
    initEnrichment();
  });

})();
