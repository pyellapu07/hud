/* ═══════════════════════════════════════════════════════════════════════════
   Personal OS — app.js
   Modules: Store · Settings · Tasks · BuyList · Jobs · Assets · Goals
            · Calendar · UI
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ── Store (localStorage wrapper) ─────────────────────────────────────────── */
const Store = {
  get(key, def = []) {
    try { return JSON.parse(localStorage.getItem(key)) ?? def; }
    catch { return def; }
  },
  set(key, val) { localStorage.setItem(key, JSON.stringify(val)); },
  id() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); },
};

/* ── Settings ─────────────────────────────────────────────────────────────── */
const Settings = {
  defaults: { name: 'Pradeep', jobsGoal: 20, calClientId: '' },
  get()    { return { ...this.defaults, ...Store.get('pos_settings', {}) }; },
  save() {
    const s = this.get();
    s.name       = document.getElementById('inp-name').value.trim()    || s.name;
    s.jobsGoal   = parseInt(document.getElementById('inp-jobs-goal').value) || s.jobsGoal;
    s.calClientId= document.getElementById('inp-cal-id').value.trim();
    Store.set('pos_settings', s);
    UI.closeModal();
    App.init();
  },
};

/* ── Tasks ────────────────────────────────────────────────────────────────── */
const Tasks = {
  all() { return Store.get('pos_tasks', []); },

  save() {
    const id       = document.getElementById('task-edit-id').value;
    const text     = document.getElementById('inp-task-text').value.trim();
    const priority = document.getElementById('inp-task-priority').value;
    const due      = document.getElementById('inp-task-due').value;
    const goalId   = document.getElementById('inp-task-goal').value;
    if (!text) return;

    const tasks = this.all();
    if (id) {
      const t = tasks.find(t => t.id === id);
      if (t) Object.assign(t, { text, priority, due, goalId });
    } else {
      tasks.push({ id: Store.id(), text, priority, due, goalId, done: false, createdAt: Date.now() });
    }
    Store.set('pos_tasks', tasks);
    UI.closeModal();
    this.render();
  },

  toggle(id) {
    const tasks = this.all();
    const t = tasks.find(t => t.id === id);
    if (t) { t.done = !t.done; t.completedAt = t.done ? Date.now() : null; }
    Store.set('pos_tasks', tasks);
    this.render();
  },

  delete(id) {
    Store.set('pos_tasks', this.all().filter(t => t.id !== id));
    this.render();
  },

  topSuggestion() {
    const active = this.all().filter(t => !t.done);
    if (!active.length) return null;
    const score = t => {
      let s = 0;
      if (t.priority === 'high')   s += 30;
      if (t.priority === 'medium') s += 15;
      if (t.due) {
        const days = (new Date(t.due) - new Date()) / 86400000;
        if (days < 1) s += 40;
        else if (days < 3) s += 20;
        else if (days < 7) s += 10;
      }
      s += Math.min((Date.now() - t.createdAt) / 3600000, 20); // age bonus
      return s;
    };
    return active.sort((a, b) => score(b) - score(a))[0];
  },

  render() {
    const list    = document.getElementById('task-list');
    const suggest = document.getElementById('task-suggestion');
    const tasks   = this.all();
    const active  = tasks.filter(t => !t.done);
    const done    = tasks.filter(t => t.done);

    // Suggestion
    const top = this.topSuggestion();
    if (top) {
      suggest.textContent = `⚡ Focus on: ${top.text}`;
      suggest.classList.remove('hidden');
    } else {
      suggest.classList.add('hidden');
    }

    list.innerHTML = '';

    if (!tasks.length) {
      list.innerHTML = '<p class="empty-state">No tasks yet — add one above</p>';
      return;
    }

    const priorityOrder = { high: 0, medium: 1, low: 2 };
    active.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

    active.forEach(t => list.appendChild(this._row(t)));

    if (done.length) {
      const div = document.createElement('div');
      div.className = 'section-divider';
      div.textContent = `Completed (${done.length})`;
      list.appendChild(div);
      done.slice(0, 5).forEach(t => list.appendChild(this._row(t)));
    }
  },

  _row(t) {
    const row = document.createElement('div');
    row.className = `item-row ${t.done ? 'done' : ''}`;
    row.innerHTML = `
      <span class="priority-dot ${t.priority}"></span>
      <span class="item-text">${esc(t.text)}</span>
      ${t.due ? `<span class="item-meta">${fmtDate(t.due)}</span>` : ''}
      <div class="item-actions">
        <button class="icon-btn" title="Edit"   onclick="UI.openTask('${t.id}')">✏️</button>
        <button class="icon-btn" title="Delete" onclick="Tasks.delete('${t.id}')">🗑️</button>
      </div>
    `;
    row.querySelector('.item-text').onclick = () => this.toggle(t.id);
    row.querySelector('.item-text').style.cursor = 'pointer';
    return row;
  },
};

/* ── BuyList ──────────────────────────────────────────────────────────────── */
const BuyList = {
  currentTab: 'all',
  all() { return Store.get('pos_buylist', []); },

  save() {
    const id     = document.getElementById('buy-edit-id').value;
    const name   = document.getElementById('inp-buy-name').value.trim();
    const cat    = document.getElementById('inp-buy-cat').value;
    const budget = document.getElementById('inp-buy-budget').value.trim();
    if (!name) return;

    const items = this.all();
    if (id) {
      const item = items.find(i => i.id === id);
      if (item) Object.assign(item, { name, cat, budget });
    } else {
      items.push({ id: Store.id(), name, cat, budget, bought: false, createdAt: Date.now() });
    }
    Store.set('pos_buylist', items);
    UI.closeModal();
    this.render();
  },

  toggle(id) {
    const items = this.all();
    const item  = items.find(i => i.id === id);
    if (item) item.bought = !item.bought;
    Store.set('pos_buylist', items);
    this.render();
  },

  delete(id) {
    Store.set('pos_buylist', this.all().filter(i => i.id !== id));
    this.render();
  },

  switchTab(tab, el) {
    this.currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    this.render();
  },

  render() {
    const list  = document.getElementById('buy-list');
    let   items = this.all();
    if (this.currentTab !== 'all') items = items.filter(i => i.cat === this.currentTab);

    const active = items.filter(i => !i.bought);
    const bought = items.filter(i => i.bought);

    list.innerHTML = '';
    if (!items.length) {
      list.innerHTML = '<p class="empty-state">Nothing here — add something!</p>';
      return;
    }

    active.forEach(i => list.appendChild(this._row(i)));
    if (bought.length) {
      const div = document.createElement('div');
      div.className = 'section-divider';
      div.textContent = `Bought (${bought.length})`;
      list.appendChild(div);
      bought.forEach(i => list.appendChild(this._row(i)));
    }
  },

  _row(i) {
    const row = document.createElement('div');
    row.className = `item-row ${i.bought ? 'done' : ''}`;
    row.innerHTML = `
      <span class="cat-badge ${i.cat}">${catIcon(i.cat)}</span>
      <span class="item-text">${esc(i.name)}</span>
      ${i.budget ? `<span class="item-meta">${esc(i.budget)}</span>` : ''}
      <div class="item-actions">
        <button class="icon-btn" onclick="UI.openBuy('${i.id}')">✏️</button>
        <button class="icon-btn" onclick="BuyList.delete('${i.id}')">🗑️</button>
      </div>
    `;
    row.querySelector('.item-text').onclick = () => this.toggle(i.id);
    row.querySelector('.item-text').style.cursor = 'pointer';
    return row;
  },
};

/* ── Jobs ─────────────────────────────────────────────────────────────────── */
const Jobs = {
  all() { return Store.get('pos_jobs', []); },

  save() {
    const company  = document.getElementById('inp-job-company').value.trim();
    const role     = document.getElementById('inp-job-role').value.trim();
    const platform = document.getElementById('inp-job-platform').value.trim();
    const status   = document.getElementById('inp-job-status').value;
    const notes    = document.getElementById('inp-job-notes').value.trim();
    if (!company) return;

    const jobs = this.all();
    jobs.push({ id: Store.id(), company, role, platform, status, notes, date: today() });
    Store.set('pos_jobs', jobs);
    UI.closeModal();
    this.render();
  },

  updateStatus(id, status) {
    const jobs = this.all();
    const j = jobs.find(j => j.id === id);
    if (j) j.status = status;
    Store.set('pos_jobs', jobs);
    this.render();
  },

  delete(id) {
    Store.set('pos_jobs', this.all().filter(j => j.id !== id));
    this.render();
  },

  todayCount() { return this.all().filter(j => j.date === today()).length; },

  streak() {
    const jobs   = this.all();
    const goal   = Settings.get().jobsGoal;
    const byDate = {};
    jobs.forEach(j => { byDate[j.date] = (byDate[j.date] || 0) + 1; });

    let streak = 0;
    const d = new Date();
    // Don't count today in streak yet
    d.setDate(d.getDate() - 1);
    while (true) {
      const key = d.toISOString().slice(0, 10);
      if ((byDate[key] || 0) >= goal) { streak++; d.setDate(d.getDate() - 1); }
      else break;
    }
    return streak;
  },

  render() {
    const s       = Settings.get();
    const count   = this.todayCount();
    const pct     = Math.min((count / s.jobsGoal) * 100, 100);
    const streak  = this.streak();

    document.getElementById('jobs-today').textContent        = count;
    document.getElementById('jobs-goal-display').textContent = s.jobsGoal;
    document.getElementById('jobs-bar').style.width          = pct + '%';
    document.getElementById('jobs-streak').textContent       = streak > 0 ? `🔥 ${streak}d` : '';

    // Heatmap — last 35 days
    const heatmap = document.getElementById('jobs-heatmap');
    heatmap.innerHTML = '';
    const jobs   = this.all();
    const byDate = {};
    jobs.forEach(j => { byDate[j.date] = (byDate[j.date] || 0) + 1; });

    for (let i = 34; i >= 0; i--) {
      const d   = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      const cnt = byDate[key] || 0;
      const lvl = cnt === 0 ? 0 : cnt < 5 ? 1 : cnt < 10 ? 2 : cnt < 20 ? 3 : 4;
      const cell = document.createElement('div');
      cell.className  = `heat-cell heat-${lvl}`;
      cell.setAttribute('data-count', cnt);
      cell.setAttribute('data-tip', `${key}: ${cnt} apps`);
      cell.title = `${key}: ${cnt} apps`;
      heatmap.appendChild(cell);
    }

    // Recent
    const recent = document.getElementById('jobs-recent');
    recent.innerHTML = '';
    const sorted = [...jobs].sort((a, b) => b.id.localeCompare(a.id)).slice(0, 4);
    if (!sorted.length) {
      recent.innerHTML = '<p class="empty-state">No applications logged yet</p>';
      return;
    }
    sorted.forEach(j => {
      const row = document.createElement('div');
      row.className = 'item-row';
      row.innerHTML = `
        <span class="item-text">${esc(j.company)}${j.role ? ' — ' + esc(j.role) : ''}</span>
        <span class="status-badge status-${j.status}">${j.status}</span>
        <div class="item-actions">
          <button class="icon-btn" onclick="Jobs.delete('${j.id}')">🗑️</button>
        </div>
      `;
      recent.appendChild(row);
    });
  },
};

/* ── Assets ───────────────────────────────────────────────────────────────── */
const Assets = {
  all() { return Store.get('pos_assets', []); },

  onTypeChange() {
    const type = document.getElementById('inp-asset-type').value;
    document.getElementById('gold-fields').classList.toggle('hidden', type !== 'gold');
    document.getElementById('value-field').classList.toggle('hidden', type === 'gold');
  },

  save() {
    const id       = document.getElementById('asset-edit-id').value;
    const name     = document.getElementById('inp-asset-name').value.trim();
    const type     = document.getElementById('inp-asset-type').value;
    const qty      = parseFloat(document.getElementById('inp-asset-qty').value)      || 0;
    const buyPrice = parseFloat(document.getElementById('inp-asset-buyprice').value) || 0;
    const value    = parseFloat(document.getElementById('inp-asset-value').value)    || 0;
    if (!name) return;

    const assets = this.all();
    const obj = { id: id || Store.id(), name, type, qty, buyPrice, manualValue: value, updatedAt: Date.now() };

    if (id) {
      const idx = assets.findIndex(a => a.id === id);
      if (idx > -1) assets[idx] = obj;
    } else {
      assets.push(obj);
    }
    Store.set('pos_assets', assets);
    UI.closeModal();
    this.render();
  },

  delete(id) {
    Store.set('pos_assets', this.all().filter(a => a.id !== id));
    this.render();
  },

  currentValue(a) {
    if (a.type === 'gold') return (a.qty || 0) * (a.goldPrice || a.buyPrice || 0);
    return a.manualValue || 0;
  },

  netWorth() { return this.all().reduce((s, a) => s + this.currentValue(a), 0); },

  async fetchGoldPrice() {
    try {
      // Use Yahoo Finance gold futures (CORS-friendly)
      const r = await fetch('https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=1d');
      const d = await r.json();
      const usdPerOz = d.chart.result[0].meta.regularMarketPrice;
      // Convert: 1 troy oz = 31.1035g, USD→INR (approx — use live rate if available)
      let usdInr = 84;
      try {
        const fx = await fetch('https://open.er-api.com/v6/latest/USD');
        const fd = await fx.json();
        usdInr = fd.rates?.INR || 84;
      } catch {}
      return (usdPerOz / 31.1035) * usdInr;
    } catch { return null; }
  },

  async refreshGold() {
    const btn = document.querySelector('.gold-refresh');
    if (btn) btn.textContent = 'Fetching…';
    const price = await this.fetchGoldPrice();
    if (price) {
      const assets = this.all();
      assets.filter(a => a.type === 'gold').forEach(a => { a.goldPrice = price; a.updatedAt = Date.now(); });
      Store.set('pos_assets', assets);
    }
    this.render();
  },

  render() {
    const assets = this.all();
    const nw     = this.netWorth();

    // Net worth banner
    const nwEl = document.getElementById('net-worth');
    nwEl.innerHTML = `
      <div>
        <div class="net-worth-label">Total Net Worth</div>
        <div class="net-worth-value">₹${fmt(nw)}</div>
      </div>
      <div class="net-worth-change">${assets.length} asset${assets.length !== 1 ? 's' : ''} tracked</div>
    `;

    // Asset cards
    const grid = document.getElementById('asset-list');
    grid.innerHTML = '';
    if (!assets.length) {
      grid.innerHTML = '<p class="empty-state">Add your first asset above</p>';
    }
    assets.forEach(a => {
      const val      = this.currentValue(a);
      const cost     = a.type === 'gold' ? (a.qty || 0) * (a.buyPrice || 0) : a.manualValue || 0;
      const gain     = val - cost;
      const gainPct  = cost ? ((gain / cost) * 100).toFixed(1) : 0;
      const gainCls  = gain >= 0 ? 'up' : 'down';
      const gainSign = gain >= 0 ? '+' : '';

      const card = document.createElement('div');
      card.className = 'asset-card';
      card.innerHTML = `
        <button class="asset-edit" onclick="UI.openAsset('${a.id}')">✏️</button>
        <div class="asset-type-badge">${a.type.toUpperCase()}</div>
        <div class="asset-name">${esc(a.name)}</div>
        <div class="asset-value">₹${fmt(val)}</div>
        ${a.type === 'gold' ? `
          <div class="asset-gain ${gainCls}">${gainSign}₹${fmt(gain)} (${gainSign}${gainPct}%)</div>
          <div class="asset-gain ${gainCls}" style="font-size:10px">
            ${a.qty}g · ₹${fmt(a.goldPrice || a.buyPrice)}/g
          </div>
          <button class="gold-refresh" onclick="Assets.refreshGold()">
            🔄 Refresh live price
          </button>
        ` : `<div class="asset-gain" style="color:var(--muted);font-size:11px">Manual entry</div>`}
        <button class="icon-btn" style="margin-top:6px;opacity:1;color:var(--red)" onclick="Assets.delete('${a.id}')">Delete</button>
      `;
      grid.appendChild(card);
    });
  },
};

/* ── Goals ────────────────────────────────────────────────────────────────── */
const Goals = {
  all() { return Store.get('pos_goals', []); },

  save() {
    const name    = document.getElementById('inp-goal-name').value.trim();
    const target  = parseFloat(document.getElementById('inp-goal-target').value)  || 0;
    const current = parseFloat(document.getElementById('inp-goal-current').value) || 0;
    const date    = document.getElementById('inp-goal-date').value;
    if (!name || !target) return;

    const goals = this.all();
    goals.push({ id: Store.id(), name, target, current, date, createdAt: Date.now() });
    Store.set('pos_goals', goals);
    UI.closeModal();
    this.render();
  },

  delete(id) {
    Store.set('pos_goals', this.all().filter(g => g.id !== id));
    this.render();
  },

  render() {
    const list  = document.getElementById('goal-list');
    const goals = this.all();
    list.innerHTML = '';
    if (!goals.length) return;

    goals.forEach(g => {
      const pct    = Math.min((g.current / g.target) * 100, 100).toFixed(0);
      const left   = g.target - g.current;
      const item   = document.createElement('div');
      item.className = 'goal-item';
      item.innerHTML = `
        <div class="goal-header">
          <span class="goal-name">${esc(g.name)}</span>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="goal-pct">${pct}%</span>
            <button class="icon-btn" onclick="Goals.delete('${g.id}')">🗑️</button>
          </div>
        </div>
        <div class="goal-track"><div class="goal-fill" style="width:${pct}%"></div></div>
        <div class="goal-sub">₹${fmt(g.current)} saved · ₹${fmt(left)} to go${g.date ? ' · by ' + fmtDate(g.date) : ''}</div>
      `;
      list.appendChild(item);
    });
  },
};

/* ── Calendar ─────────────────────────────────────────────────────────────── */
const Calendar = {
  connected: false,
  events: [],

  connect() {
    const clientId = Settings.get().calClientId;
    if (!clientId) {
      alert('Paste your Google Calendar Client ID in Settings (⚙) first.\n\nGet one free at console.cloud.google.com — takes ~2 minutes.');
      return;
    }
    this._loadGapi(clientId);
  },

  _loadGapi(clientId) {
    if (window.gapi) { this._init(clientId); return; }
    const s = document.createElement('script');
    s.src = 'https://apis.google.com/js/api.js';
    s.onload = () => this._init(clientId);
    document.head.appendChild(s);
  },

  _init(clientId) {
    gapi.load('client:auth2', async () => {
      try {
        await gapi.client.init({
          clientId,
          scope: 'https://www.googleapis.com/auth/calendar.readonly',
          discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest'],
        });
        const auth = gapi.auth2.getAuthInstance();
        if (!auth.isSignedIn.get()) await auth.signIn();
        this.connected = true;
        document.getElementById('cal-btn').textContent = 'Refresh';
        document.getElementById('cal-btn').onclick = () => Calendar.fetchEvents();
        await this.fetchEvents();
      } catch (e) {
        console.error(e);
        alert('Calendar connect failed: ' + (e.details || e.message || JSON.stringify(e)));
      }
    });
  },

  async fetchEvents() {
    const now   = new Date();
    const end   = new Date(); end.setHours(23, 59, 59);
    try {
      const res = await gapi.client.calendar.events.list({
        calendarId: 'primary',
        timeMin: now.toISOString(),
        timeMax: end.toISOString(),
        singleEvents: true,
        orderBy: 'startTime',
        maxResults: 10,
      });
      this.events = res.result.items || [];
      this.render();
      this._updateMeetingBanner();
    } catch (e) { console.error(e); }
  },

  _meetLink(e) {
    if (e.hangoutLink) return e.hangoutLink;
    const desc = (e.description || '') + (e.location || '');
    const m = desc.match(/https:\/\/(meet\.google\.com|zoom\.us|teams\.microsoft\.com|whereby\.com)\/\S+/);
    return m ? m[0] : null;
  },

  _updateMeetingBanner() {
    const banner = document.getElementById('meeting-banner');
    if (!this.events.length) { banner.classList.add('hidden'); return; }
    const next = this.events[0];
    const link = this._meetLink(next);
    const start = next.start?.dateTime ? new Date(next.start.dateTime) : null;
    const mins  = start ? Math.round((start - new Date()) / 60000) : null;

    document.getElementById('meeting-label').textContent =
      `${next.summary}${mins !== null ? ` — in ${mins}m` : ''}`;

    const joinEl = document.getElementById('meeting-join');
    if (link) { joinEl.href = link; joinEl.classList.remove('hidden'); }
    else joinEl.classList.add('hidden');

    banner.classList.remove('hidden');
  },

  render() {
    const body = document.getElementById('calendar-body');
    body.innerHTML = '';

    if (!this.connected) {
      body.innerHTML = `
        <div class="cal-connect-state">
          <div style="font-size:40px">📅</div>
          <p>Connect your Google Calendar to see today's meetings with one-click join links.</p>
          <p style="font-size:11px;margin-top:4px">Requires a free Google Cloud project · takes ~2 min to set up</p>
        </div>`;
      return;
    }

    if (!this.events.length) {
      body.innerHTML = '<p class="cal-empty">No more events today 🎉</p>';
      return;
    }

    this.events.forEach(e => {
      const start = e.start?.dateTime || e.start?.date || '';
      const timeStr = start.includes('T')
        ? new Date(start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'All day';
      const link = this._meetLink(e);

      const row = document.createElement('div');
      row.className = 'cal-event';
      row.innerHTML = `
        <span class="cal-time">${timeStr}</span>
        <div class="cal-info">
          <div class="cal-title">${esc(e.summary || '(No title)')}</div>
          ${e.location ? `<div class="cal-loc">${esc(e.location)}</div>` : ''}
        </div>
        ${link ? `<a class="cal-join" href="${link}" target="_blank">Join</a>` : ''}
      `;
      body.appendChild(row);
    });
  },
};

/* ── UI (modal orchestration + header) ───────────────────────────────────── */
const UI = {
  openTask(id) {
    const tasks = Tasks.all();
    const t     = id ? tasks.find(t => t.id === id) : null;
    document.getElementById('modal-task-title').textContent = t ? 'Edit Task' : 'New Task';
    document.getElementById('task-edit-id').value         = t?.id       || '';
    document.getElementById('inp-task-text').value        = t?.text     || '';
    document.getElementById('inp-task-priority').value    = t?.priority || 'medium';
    document.getElementById('inp-task-due').value         = t?.due      || '';

    // Populate goal dropdown
    const sel = document.getElementById('inp-task-goal');
    sel.innerHTML = '<option value="">— None —</option>';
    Goals.all().forEach(g => {
      const o = document.createElement('option');
      o.value = g.id; o.textContent = g.name;
      if (t?.goalId === g.id) o.selected = true;
      sel.appendChild(o);
    });
    document.getElementById('inp-task-goal').value = t?.goalId || '';

    this._open('modal-task');
    setTimeout(() => document.getElementById('inp-task-text').focus(), 50);
  },

  openBuy(id) {
    const items = BuyList.all();
    const item  = id ? items.find(i => i.id === id) : null;
    document.getElementById('buy-edit-id').value     = item?.id     || '';
    document.getElementById('inp-buy-name').value    = item?.name   || '';
    document.getElementById('inp-buy-cat').value     = item?.cat    || 'someday';
    document.getElementById('inp-buy-budget').value  = item?.budget || '';
    this._open('modal-buy');
    setTimeout(() => document.getElementById('inp-buy-name').focus(), 50);
  },

  openJob() {
    ['inp-job-company','inp-job-role','inp-job-platform','inp-job-notes'].forEach(id => {
      document.getElementById(id).value = '';
    });
    document.getElementById('inp-job-status').value = 'applied';
    this._open('modal-job');
    setTimeout(() => document.getElementById('inp-job-company').focus(), 50);
  },

  openAsset(id) {
    const assets = Assets.all();
    const a      = id ? assets.find(a => a.id === id) : null;
    document.getElementById('modal-asset-title').textContent = a ? 'Edit Asset' : 'Add Asset';
    document.getElementById('asset-edit-id').value         = a?.id          || '';
    document.getElementById('inp-asset-name').value        = a?.name        || '';
    document.getElementById('inp-asset-type').value        = a?.type        || 'gold';
    document.getElementById('inp-asset-qty').value         = a?.qty         || '';
    document.getElementById('inp-asset-buyprice').value    = a?.buyPrice    || '';
    document.getElementById('inp-asset-value').value       = a?.manualValue || '';
    Assets.onTypeChange();
    this._open('modal-asset');
  },

  openGoal() {
    ['inp-goal-name','inp-goal-target','inp-goal-current','inp-goal-date'].forEach(id => {
      document.getElementById(id).value = '';
    });
    this._open('modal-goal');
    setTimeout(() => document.getElementById('inp-goal-name').focus(), 50);
  },

  openSettings(focus) {
    const s = Settings.get();
    document.getElementById('inp-name').value      = s.name;
    document.getElementById('inp-jobs-goal').value = s.jobsGoal;
    document.getElementById('inp-cal-id').value    = s.calClientId || '';
    this._open('modal-settings');
    if (focus === 'jobs') setTimeout(() => document.getElementById('inp-jobs-goal').focus(), 50);
  },

  _open(id) {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById(id).classList.remove('hidden');
  },

  closeModal() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    document.getElementById('overlay').classList.add('hidden');
  },
};

/* ── Header clock ─────────────────────────────────────────────────────────── */
function updateHeader() {
  const name = Settings.get().name;
  const h    = new Date().getHours();
  const greet = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  document.getElementById('greeting').textContent  = `${greet}, ${name} 👋`;
  document.getElementById('date-line').textContent =
    new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

/* ── Keyboard shortcuts ───────────────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'Escape') UI.closeModal();
  if (e.key === 't') UI.openTask();
  if (e.key === 'b') UI.openBuy();
  if (e.key === 'j') UI.openJob();
  if (e.key === 'a') UI.openAsset();
});

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmt(n) {
  if (isNaN(n)) return '0';
  if (n >= 1e7) return (n/1e7).toFixed(2) + ' Cr';
  if (n >= 1e5) return (n/1e5).toFixed(2) + ' L';
  return Math.round(n).toLocaleString('en-IN');
}
function today()   { return new Date().toISOString().slice(0, 10); }
function fmtDate(d) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}
function catIcon(c) { return { urgent:'Urgent', groceries:'Grocery', someday:'Someday' }[c] || c; }

/* ── App bootstrap ────────────────────────────────────────────────────────── */
const App = {
  init() {
    updateHeader();
    Tasks.render();
    BuyList.render();
    Jobs.render();
    Assets.render();
    Goals.render();
    Calendar.render();
  },
};

App.init();
// Refresh header every minute
setInterval(updateHeader, 60000);
// Auto-refresh gold prices on load
Assets.refreshGold();
