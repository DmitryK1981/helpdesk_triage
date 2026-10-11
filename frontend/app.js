const CATEGORY_LABELS = { billing: 'Оплата', support: 'Поддержка', complaint: 'Жалоба', other: 'Другое' };
const CATEGORY_ORDER = ['billing', 'support', 'complaint', 'other'];
const CONFIDENCE_LABELS = { high: 'высокая', medium: 'средняя', low: 'низкая' };
const CHANNEL_LABELS = { email: 'почта', form: 'форма на сайте', chat: 'чат' };

let currentPage = 0;
let pageSize = 20;
let lastTotal = 0;

// ---------- Tabs ----------
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'history') {
      loadStats();
      loadHistory();
    }
  });
});

// ---------- Submit form ----------
const textEl = document.getElementById('text');
const countEl = document.getElementById('count');
textEl.addEventListener('input', () => { countEl.textContent = textEl.value.length; });

document.getElementById('triage-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const errorMsg = document.getElementById('error-msg');
  errorMsg.textContent = '';
  btn.disabled = true;
  btn.textContent = 'Отправка...';

  const payload = {
    text: textEl.value,
    channel: document.getElementById('channel').value,
    client_id: document.getElementById('client_id').value,
  };

  try {
    const res = await fetch('/triage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      errorMsg.textContent = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else {
      renderResult(data);
      textEl.value = '';
      countEl.textContent = '0';
      textEl.focus();
    }
  } catch (err) {
    errorMsg.textContent = 'Сетевая ошибка: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Отправить';
  }
});

document.getElementById('clear-btn').addEventListener('click', () => {
  textEl.value = '';
  countEl.textContent = '0';
  document.getElementById('error-msg').textContent = '';
  document.getElementById('result-panel').style.display = 'none';
  textEl.focus();
});

function renderResult(data) {
  const panel = document.getElementById('result-panel');
  panel.style.display = 'block';
  document.getElementById('badge-category').textContent = 'категория: ' + CATEGORY_LABELS[data.category];
  document.getElementById('badge-category').className = 'badge cat-' + data.category;
  const confBadge = document.getElementById('badge-confidence');
  confBadge.textContent = 'уверенность: ' + CONFIDENCE_LABELS[data.confidence];
  confBadge.className = 'badge conf-' + data.confidence;
  const escBadge = document.getElementById('badge-escalate');
  escBadge.textContent = data.escalate ? 'эскалация: да' : 'эскалация: нет';
  escBadge.className = 'badge esc-' + data.escalate;
  document.getElementById('draft-reply').textContent = data.draft_reply;
}

// ---------- Stats ----------
async function loadStats() {
  const res = await fetch('/stats');
  const s = await res.json();

  document.getElementById('stat-total').textContent = s.total;
  const escPct = s.total ? Math.round((s.escalated / s.total) * 100) : 0;
  document.getElementById('stat-escalated').textContent = `${escPct}% (${s.escalated})`;
  const errEl = document.getElementById('stat-errors');
  errEl.textContent = s.errors;
  errEl.className = 'stat-value' + (s.errors > 0 ? ' danger' : '');

  const maxCount = Math.max(1, ...CATEGORY_ORDER.map(c => s.by_category[c] || 0));
  const chart = document.getElementById('cat-chart');
  chart.innerHTML = CATEGORY_ORDER.map((cat, i) => {
    const count = s.by_category[cat] || 0;
    const pct = Math.round((count / maxCount) * 100);
    return `
      <div class="cat-row">
        <span class="cat-name">${CATEGORY_LABELS[cat]}</span>
        <div class="cat-track"><div class="cat-fill" style="width:${pct}%;background:var(--series-${i + 1})"></div></div>
        <span class="cat-count">${count}</span>
      </div>`;
  }).join('');
}

// ---------- History table ----------
function escapeHtml(s) {
  return (s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function buildQuery() {
  const params = new URLSearchParams();
  params.set('limit', pageSize);
  params.set('offset', currentPage * pageSize);

  const q = document.getElementById('f-q').value.trim();
  const category = document.getElementById('f-category').value;
  const confidence = document.getElementById('f-confidence').value;
  const channel = document.getElementById('f-channel').value;
  const escalate = document.getElementById('f-escalate').value;
  const onlyErrors = document.getElementById('f-errors').checked;

  if (q) params.set('q', q);
  if (category) params.set('category', category);
  if (confidence) params.set('confidence', confidence);
  if (channel) params.set('channel', channel);
  if (escalate) params.set('escalate', escalate);
  if (onlyErrors) params.set('only_errors', 'true');

  return params;
}

let ticketsCache = [];

async function loadHistory() {
  const params = buildQuery();
  const res = await fetch('/tickets?' + params.toString());
  const data = await res.json();
  ticketsCache = data.items;
  lastTotal = data.total;

  const body = document.getElementById('history-body');
  const emptyState = document.getElementById('empty-state');

  if (data.items.length === 0) {
    body.innerHTML = '';
    emptyState.style.display = 'block';
  } else {
    emptyState.style.display = 'none';
    body.innerHTML = data.items.map(r => `
      <tr data-id="${r.id}">
        <td class="mono">${r.id}</td>
        <td class="mono">${new Date(r.created_at).toLocaleString()}</td>
        <td>${escapeHtml(r.client_id)}</td>
        <td>${CHANNEL_LABELS[r.channel] ?? escapeHtml(r.channel)}</td>
        <td class="text-cell" title="${escapeHtml(r.text)}">${escapeHtml(r.text)}</td>
        <td>${r.category ? `<span class="pill cat-${r.category}">${CATEGORY_LABELS[r.category]}</span>` : '<span class="muted">—</span>'}</td>
        <td>${r.confidence ? `<span class="pill conf-${r.confidence}">${CONFIDENCE_LABELS[r.confidence]}</span>` : '<span class="muted">—</span>'}</td>
        <td>${r.escalate ? '<span class="flag-escalate">да</span>' : '<span class="muted">—</span>'}</td>
        <td>${r.error ? '<span class="flag-error" title="' + escapeHtml(r.error) + '">⚠</span>' : '<span class="muted">—</span>'}</td>
      </tr>
    `).join('');

    body.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', () => openDrawer(Number(tr.dataset.id)));
    });
  }

  renderPagination();
}

function renderPagination() {
  const from = lastTotal === 0 ? 0 : currentPage * pageSize + 1;
  const to = Math.min(lastTotal, currentPage * pageSize + pageSize);
  document.getElementById('pagination-info').textContent = `${from}–${to} из ${lastTotal}`;
  document.getElementById('prev-page').disabled = currentPage === 0;
  document.getElementById('next-page').disabled = to >= lastTotal;
}

document.getElementById('refresh-btn').addEventListener('click', () => { currentPage = 0; loadStats(); loadHistory(); });
document.querySelectorAll('.filters input, .filters select').forEach(el => {
  el.addEventListener('change', () => { currentPage = 0; loadHistory(); });
});
document.getElementById('f-q').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { currentPage = 0; loadHistory(); }
});
document.getElementById('page-size').addEventListener('change', (e) => {
  pageSize = Number(e.target.value);
  currentPage = 0;
  loadHistory();
});
document.getElementById('prev-page').addEventListener('click', () => {
  if (currentPage > 0) { currentPage--; loadHistory(); }
});
document.getElementById('next-page').addEventListener('click', () => {
  if ((currentPage + 1) * pageSize < lastTotal) { currentPage++; loadHistory(); }
});

// ---------- Detail drawer ----------
function openDrawer(id) {
  const t = ticketsCache.find(r => r.id === id);
  if (!t) return;

  document.getElementById('d-id').textContent = t.id;
  document.getElementById('d-time').textContent = new Date(t.created_at).toLocaleString();
  document.getElementById('d-client').textContent = `${t.client_id} · ${CHANNEL_LABELS[t.channel] ?? t.channel}`;
  document.getElementById('d-text').textContent = t.text;
  document.getElementById('d-flags').textContent =
    `${CATEGORY_LABELS[t.category] ?? '—'} / ${CONFIDENCE_LABELS[t.confidence] ?? '—'} / эскалация: ${t.escalate ? 'да' : 'нет'}`;
  document.getElementById('d-draft').textContent = t.draft_reply ?? '—';

  const errWrap = document.getElementById('d-error-wrap');
  if (t.error) {
    errWrap.style.display = 'block';
    document.getElementById('d-error').textContent = t.error;
  } else {
    errWrap.style.display = 'none';
  }

  document.getElementById('overlay').classList.add('open');
  document.getElementById('drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('overlay').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
}

document.getElementById('drawer-close').addEventListener('click', closeDrawer);
document.getElementById('overlay').addEventListener('click', closeDrawer);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

// ---------- Init ----------
loadStats();
loadHistory();
