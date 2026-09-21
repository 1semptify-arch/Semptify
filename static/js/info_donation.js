/* info_donation.js — drives the /help-the-next-tenant page.
 * Zones reveal in order: resolve → consent → per-item → review → mine.
 * All state lives server-side under /api/info-donation/*; this file only
 * renders and calls it. Nothing is sent until the explicit submit click.
 */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const zones = ['zone-need-help', 'zone-resolve', 'zone-consent', 'zone-items', 'zone-review', 'zone-mine', 'zone-dismiss'];

  let catalog = null;
  let status = null;
  let mine = [];

  async function api(path, method, body) {
    const opts = { method: method || 'GET', headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(path, opts);
    if (resp.status === 401) {
      $('donation-status-line').textContent = 'Your session has ended — open Semptify again to continue.';
      return null;
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const msg = (data && data.detail) || 'Something did not go through. Try again.';
      $('donation-status-line').textContent = msg;
      return { __error: true, status: resp.status, detail: msg };
    }
    return data;
  }

  function show(id) { const el = $(id); if (el) el.hidden = false; }
  function hide(id) { const el = $(id); if (el) el.hidden = true; }

  function render() {
    zones.forEach((z) => { if (z !== 'zone-need-help') hide(z); });

    if (!status.resolved) {
      show('zone-resolve');
      return;
    }
    if (status.dismissed) {
      $('donation-status-line').textContent = 'Sharing is off — nothing will be sent. If things change, this page stays available.';
      show('zone-mine');
      renderMine();
      return;
    }
    if (!status.consented) {
      $('consent-text').textContent = catalog.consent_text;
      show('zone-consent');
      return;
    }
    renderForm();
    show('zone-items');
    show('zone-mine');
    renderMine();
    show('zone-dismiss');
  }

  function renderForm() {
    const form = $('donation-form');
    if (form.dataset.built) return;
    form.dataset.built = '1';
    catalog.items.forEach((item) => {
      const field = document.createElement('div');
      field.className = 'donation-field';
      const label = document.createElement('label');
      label.textContent = item.label;
      label.htmlFor = 'item-' + item.key;
      field.appendChild(label);

      if (item.kind === 'choice' || item.kind === 'bool') {
        const sel = document.createElement('select');
        sel.className = 'form-select';
        sel.id = 'item-' + item.key;
        sel.dataset.key = item.key;
        sel.dataset.kind = item.kind;
        const blank = document.createElement('option');
        blank.value = '';
        blank.textContent = '— skip —';
        sel.appendChild(blank);
        const opts = item.kind === 'bool'
          ? [{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }]
          : item.options;
        opts.forEach((o) => {
          const opt = document.createElement('option');
          opt.value = o.value;
          opt.textContent = o.label;
          sel.appendChild(opt);
        });
        field.appendChild(sel);
      } else if (item.kind === 'multichoice') {
        const box = document.createElement('fieldset');
        box.dataset.key = item.key;
        item.options.forEach((o) => {
          const row = document.createElement('label');
          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.value = o.value;
          row.appendChild(cb);
          row.appendChild(document.createTextNode(' ' + o.label));
          box.appendChild(row);
        });
        field.appendChild(box);
      } else {
        const ta = document.createElement('textarea');
        ta.className = 'form-textarea';
        ta.id = 'item-' + item.key;
        ta.dataset.key = item.key;
        ta.rows = 3;
        ta.maxLength = 2000;
        field.appendChild(ta);
      }
      form.appendChild(field);
    });
  }

  function collectAnswers() {
    const answers = {};
    document.querySelectorAll('#donation-form select[data-key]').forEach((sel) => {
      if (!sel.value) return;
      answers[sel.dataset.key] = sel.dataset.kind === 'bool' ? sel.value === 'true' : sel.value;
    });
    document.querySelectorAll('#donation-form fieldset[data-key]').forEach((fs) => {
      const vals = Array.from(fs.querySelectorAll('input[type=checkbox]:checked')).map((c) => c.value);
      if (vals.length) answers[fs.dataset.key] = vals;
    });
    document.querySelectorAll('#donation-form textarea[data-key]').forEach((ta) => {
      if (ta.value.trim()) answers[ta.dataset.key] = ta.value.trim();
    });
    return answers;
  }

  function labelFor(item, value) {
    if (item.kind === 'bool') {
      return value === true || value === 'true' ? 'Yes' : 'No';
    }
    if (item.kind === 'choice') {
      const o = item.options.find((o) => o.value === value);
      return o ? o.label : String(value);
    }
    if (item.kind === 'multichoice') {
      return value.map((v) => {
        const o = item.options.find((o) => o.value === v);
        return o ? o.label : v;
      }).join(', ');
    }
    return String(value);
  }

  function renderReview() {
    const answers = collectAnswers();
    const dl = $('review-list');
    dl.innerHTML = '';
    if (!Object.keys(answers).length) {
      const p = document.createElement('p');
      p.className = 'text-muted';
      p.textContent = 'You have not answered anything yet — go back and pick what you want to share, or share nothing at all.';
      dl.appendChild(p);
      return;
    }
    catalog.items.forEach((item) => {
      if (!(item.key in answers)) return;
      const dt = document.createElement('dt');
      dt.textContent = item.label;
      const dd = document.createElement('dd');
      dd.textContent = labelFor(item, answers[item.key]);
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    show('zone-review');
    $('zone-review').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderMine() {
    const ul = $('mine-list');
    ul.innerHTML = '';
    if (!mine.length) {
      const li = document.createElement('li');
      li.className = 'shell-note';
      li.textContent = 'Nothing shared yet.';
      ul.appendChild(li);
      return;
    }
    mine.forEach((row) => {
      const li = document.createElement('li');
      const item = catalog.items.find((i) => i.key === row.item_key);
      const label = item ? item.label : row.item_key;
      let display = row.value;
      if (item) display = labelFor(item, row.value);
      const span = document.createElement('span');
      span.textContent = label + ': ' + display + (row.moderation === 'pending' ? ' (awaiting review)' : '');
      li.appendChild(span);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'shell-btn shell-btn--sm';
      btn.textContent = 'Take back';
      btn.addEventListener('click', async () => {
        const res = await api('/api/info-donation/mine/' + encodeURIComponent(row.id), 'DELETE');
        if (res && !res.__error) await reloadMine();
      });
      li.appendChild(btn);
      ul.appendChild(li);
    });
  }

  async function reloadMine() {
    const data = await api('/api/info-donation/mine');
    if (data && !data.__error) {
      mine = data.items;
      renderMine();
    }
  }

  async function reloadStatus() {
    const data = await api('/api/info-donation/status');
    if (data && !data.__error) status = data;
  }

  function bind() {
    $('btn-resolved').addEventListener('click', async () => {
      const res = await api('/api/info-donation/resolved', 'POST', { source: 'self_reported' });
      if (res && !res.__error) { await reloadStatus(); render(); }
    });
    $('btn-not-resolved').addEventListener('click', () => { $('resolve-msg').hidden = false; });
    $('btn-consent').addEventListener('click', async () => {
      const res = await api('/api/info-donation/consent', 'POST', { consent_version: catalog.consent_version });
      if (res && !res.__error) { await reloadStatus(); render(); }
    });
    $('btn-decline').addEventListener('click', () => {
      $('decline-msg').hidden = false;
      show('zone-dismiss');
    });
    $('btn-to-review').addEventListener('click', renderReview);
    $('btn-back').addEventListener('click', () => { hide('zone-review'); });
    $('btn-submit').addEventListener('click', async () => {
      const answers = collectAnswers();
      if (!Object.keys(answers).length) { hide('zone-review'); return; }
      const res = await api('/api/info-donation/donate', 'POST', { items: answers });
      if (res && !res.__error) {
        hide('zone-review');
        $('donation-status-line').textContent = 'Shared. Thank you — it goes toward helping the next tenant.';
        await reloadMine();
      }
    });
    $('btn-withdraw-all').addEventListener('click', async () => {
      const res = await api('/api/info-donation/withdraw-all', 'POST', {});
      if (res && !res.__error) { await reloadStatus(); await reloadMine(); render(); }
    });
    $('btn-dismiss').addEventListener('click', async () => {
      const res = await api('/api/info-donation/dismiss', 'POST', {});
      if (res && !res.__error) { await reloadStatus(); render(); }
    });
  }

  async function init() {
    catalog = await api('/api/info-donation/catalog');
    if (!catalog || catalog.__error) return;
    await reloadStatus();
    if (!status) return;
    if (status.consented) await reloadMine();
    bind();
    render();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
