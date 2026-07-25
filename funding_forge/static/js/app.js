/**
 * Funding Forge single-page app.
 *
 * Routes use the hash fragment: #funders, #funders/new, #funders/5,
 * #funders/5/edit, #opportunities, #opportunities/3, etc.
 */

const API_BASE = '/api';
const STATUS_OPTIONS = {
  funder: ['researching', 'applied', 'active', 'closed', 'rejected'],
  contact: ['active', 'inactive', 'champion', 'no_response'],
  opportunity: ['prospect', 'applied', 'in_review', 'awarded', 'declined', 'abandoned'],
  step: ['pending', 'in_progress', 'done', 'blocked'],
  interaction: ['email', 'call', 'meeting', 'note', 'task', 'document'],
  task: ['open', 'in_progress', 'done', 'cancelled'],
};
const TYPE_OPTIONS = {
  funder: ['fiscal_sponsor', 'crowdfunding', 'grant', 'pro_bono_legal', 'foundation', 'tech_credit', 'partnership', 'media', 'other'],
  opportunity: ['grant', 'fiscal_sponsorship', 'crowdfunding', 'pro_bono', 'tech_credit', 'partnership', 'other'],
};

let cachedFunders = [];
let cachedContacts = [];
let cachedOpportunities = [];

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function getHash() {
  const raw = window.location.hash.replace(/^#/, '') || 'dashboard';
  const [route, query] = raw.split('?');
  return { route, params: new URLSearchParams(query || '') };
}

function setHash(route) {
  window.location.hash = route;
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function badge(value) {
  const safe = escapeHtml(value || 'unknown').toLowerCase().replace(/[^a-z0-9_]/g, '_');
  return `<span class="badge badge-${safe}">${escapeHtml(value || 'unknown')}</span>`;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return escapeHtml(iso);
  return d.toLocaleDateString();
}

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return escapeHtml(iso);
  return d.toLocaleString();
}

function toInputDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toISOString().slice(0, 16);
}

function showError(msg) {
  const app = $('#app');
  app.insertAdjacentHTML('afterbegin', `<div class="flash flash-error">${escapeHtml(msg)}</div>`);
  setTimeout(() => { const el = $('.flash-error'); if (el) el.remove(); }, 5000);
}

function showSuccess(msg) {
  const app = $('#app');
  app.insertAdjacentHTML('afterbegin', `<div class="flash flash-success">${escapeHtml(msg)}</div>`);
  setTimeout(() => { const el = $('.flash-success'); if (el) el.remove(); }, 5000);
}

async function api(path, options = {}) {
  const url = API_BASE + path;
  const response = await fetch(url, {
    headers: { 'Accept': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 401) {
    window.location.href = '/unlock';
    return null;
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { const data = await response.json(); detail = data.detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function navLink(route, text) {
  return `<a href="#${route}">${escapeHtml(text)}</a>`;
}

function pageHeader(title, actions = '') {
  return `<div class="page-header"><h1>${escapeHtml(title)}</h1><div class="actions">${actions}</div></div>`;
}

function sectionHeader(title, actions = '') {
  return `<div class="page-header" style="margin-top:1.5rem"><h2>${escapeHtml(title)}</h2><div class="actions">${actions}</div></div>`;
}

function renderTable(headers, rows) {
  if (!rows.length) return '<div class="empty-state">Nothing here yet.</div>';
  const headerHtml = headers.map(h => `<th>${escapeHtml(h)}</th>`).join('');
  const bodyHtml = rows.map(r => `<tr>${r.cells.map(c => `<td>${c}</td>`).join('')}</tr>`).join('');
  return `<table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`;
}

async function loadFunders() {
  cachedFunders = await api('/funders') || [];
  return cachedFunders;
}

async function loadContacts() {
  cachedContacts = await api('/contacts') || [];
  return cachedContacts;
}

async function loadOpportunities() {
  cachedOpportunities = await api('/opportunities') || [];
  return cachedOpportunities;
}

function funderSelect(name, selectedId, required = false) {
  const options = cachedFunders.map(f => `<option value="${f.id}" ${f.id == selectedId ? 'selected' : ''}>${escapeHtml(f.name)}</option>`).join('');
  const req = required ? 'required' : '';
  const empty = required ? '' : '<option value="">—</option>';
  return `<select id="${name}" name="${name}" ${req}>${empty}${options}</select>`;
}

function contactSelect(name, selectedId) {
  const options = cachedContacts.map(c => `<option value="${c.id}" ${c.id == selectedId ? 'selected' : ''}>${escapeHtml(c.name)}${c.funder ? ' — ' + escapeHtml(c.funder.name) : ''}</option>`).join('');
  return `<select id="${name}" name="${name}"><option value="">—</option>${options}</select>`;
}

function opportunitySelect(name, selectedId) {
  const options = cachedOpportunities.map(o => `<option value="${o.id}" ${o.id == selectedId ? 'selected' : ''}>${escapeHtml(o.title)}</option>`).join('');
  return `<select id="${name}" name="${name}"><option value="">—</option>${options}</select>`;
}

function selectOptions(name, options, selected, required = false) {
  const opts = options.map(o => `<option value="${escapeHtml(o)}" ${o == selected ? 'selected' : ''}>${escapeHtml(o)}</option>`).join('');
  const req = required ? 'required' : '';
  return `<select id="${name}" name="${name}" ${req}>${opts}</select>`;
}

function formGroup(label, inputHtml, full = false) {
  return `<div class="form-group ${full ? 'full-width' : ''}"><label>${escapeHtml(label)}</label>${inputHtml}</div>`;
}

function inputText(name, value, placeholder = '', required = false) {
  return `<input type="text" id="${name}" name="${name}" value="${escapeHtml(value || '')}" placeholder="${escapeHtml(placeholder)}" ${required ? 'required' : ''}>`;
}

function inputDate(name, value) {
  return `<input type="datetime-local" id="${name}" name="${name}" value="${toInputDate(value)}">`;
}

function inputFile(name) {
  return `<input type="file" id="${name}" name="${name}">`;
}

function textarea(name, value) {
  return `<textarea id="${name}" name="${name}">${escapeHtml(value || '')}</textarea>`;
}

function formActions(submitText, cancelRoute) {
  return `<div class="form-actions"><button type="submit">${escapeHtml(submitText)}</button><a href="#${cancelRoute}" class="button secondary">Cancel</a></div>`;
}

function collectFormData(form) {
  const data = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'checkbox') {
      data[el.name] = el.checked;
    } else if (el.type === 'datetime-local') {
      data[el.name] = el.value ? new Date(el.value).toISOString() : null;
    } else if (el.type === 'number') {
      data[el.name] = el.value ? Number(el.value) : null;
    } else if (el.type === 'select-one') {
      data[el.name] = el.value ? (isNaN(Number(el.value)) ? el.value : Number(el.value)) : null;
    } else {
      data[el.name] = el.value || null;
    }
  }
  return data;
}

function bindForm(formSelector, submitter) {
  const form = $(formSelector);
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = collectFormData(form);
    try {
      await submitter(data);
    } catch (err) {
      showError(err.message);
    }
  });
}

async function deleteEntity(route, name, redirectRoute) {
  if (!confirm(`Delete ${name}? This cannot be undone.`)) return;
  try {
    await api(route, { method: 'DELETE' });
    showSuccess(`${name} deleted`);
    if (redirectRoute) setHash(redirectRoute);
    else loadView();
  } catch (err) {
    showError(err.message);
  }
}

// =============================================================================
// Views
// =============================================================================

async function dashboard() {
  const stats = await api('/dashboard');
  const app = $('#app');
  let html = pageHeader('Dashboard');
  html += `<div class="grid">
    <div class="stat"><span class="stat-value">${stats.funder_count}</span><span class="stat-label">Funders</span></div>
    <div class="stat"><span class="stat-value">${stats.contact_count}</span><span class="stat-label">Contacts</span></div>
    <div class="stat"><span class="stat-value">${stats.opportunity_count}</span><span class="stat-label">Opportunities</span></div>
    <div class="stat"><span class="stat-value">${stats.open_task_count}</span><span class="stat-label">Open tasks</span></div>
    <div class="stat"><span class="stat-value">${stats.upcoming_deadline_count}</span><span class="stat-label">With deadlines</span></div>
    <div class="stat"><span class="stat-value">${stats.recent_interaction_count}</span><span class="stat-label">Interactions</span></div>
  </div>`;
  app.innerHTML = html;
}

async function funderList() {
  const funders = await loadFunders();
  const app = $('#app');
  const actions = `<a href="#funders/new" class="button">Add funder</a>`;
  let html = pageHeader('Funders', actions);
  const rows = funders.map(f => ({
    cells: [
      navLink(`funders/${f.id}`, f.name),
      escapeHtml(f.type),
      badge(f.status),
      escapeHtml(f.contact_count),
      escapeHtml(f.opportunity_count),
      f.website ? `<a href="${escapeHtml(f.website)}" target="_blank" rel="noopener">Site</a>` : '—',
    ],
  }));
  html += renderTable(['Name', 'Type', 'Status', 'Contacts', 'Opportunities', 'Website'], rows);
  app.innerHTML = html;
}

async function funderForm(id = null) {
  let funder = { type: 'fiscal_sponsor', status: 'researching' };
  if (id) {
    funder = await api(`/funders/${id}`);
  }
  const app = $('#app');
  const title = id ? 'Edit funder' : 'Add funder';
  let html = pageHeader(title);
  html += `<div class="card"><form id="funder-form">
    <div class="form-grid">
      ${formGroup('Name', inputText('name', funder.name, '', true), false)}
      ${formGroup('Type', selectOptions('type', TYPE_OPTIONS.funder, funder.type, true), false)}
      ${formGroup('Status', selectOptions('status', STATUS_OPTIONS.funder, funder.status, true), false)}
      ${formGroup('Website', inputText('website', funder.website), false)}
      ${formGroup('Location', inputText('location', funder.location), false)}
      ${formGroup('Focus / mission', textarea('focus', funder.focus), true)}
      ${formGroup('Notes', textarea('notes', funder.notes), true)}
    </div>
    ${formActions(id ? 'Save changes' : 'Add funder', 'funders')}
  </form></div>`;
  app.innerHTML = html;
  bindForm('#funder-form', async (data) => {
    if (id) {
      await api(`/funders/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Funder updated');
    } else {
      await api('/funders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Funder added');
    }
    setHash('funders');
  });
}

async function funderDetail(id) {
  const funder = await api(`/funders/${id}`);
  const app = $('#app');
  let html = pageHeader(funder.name, `<a href="#funders/${id}/edit" class="button secondary">Edit</a> <button class="danger" id="delete-funder">Delete</button>`);
  html += `<div class="card"><div class="detail-grid">
    <div><strong>Type</strong><p>${escapeHtml(funder.type)}</p></div>
    <div><strong>Status</strong><p>${badge(funder.status)}</p></div>
    <div><strong>Website</strong><p>${funder.website ? `<a href="${escapeHtml(funder.website)}" target="_blank" rel="noopener">${escapeHtml(funder.website)}</a>` : '—'}</p></div>
    <div><strong>Location</strong><p>${escapeHtml(funder.location || '—')}</p></div>
    <div class="full-width"><strong>Focus / mission</strong><p>${escapeHtml(funder.focus || '—')}</p></div>
    <div class="full-width"><strong>Notes</strong><p>${escapeHtml(funder.notes || '—')}</p></div>
  </div></div>`;

  html += sectionHeader('Contacts', `<a href="#contacts/new?funder_id=${id}" class="button button-small">Add contact</a>`);
  const contactRows = (funder.contacts || []).map(c => ({
    cells: [navLink(`contacts/${c.id}`, c.name), escapeHtml(c.role || '—'), escapeHtml(c.email || '—'), badge(c.status)],
  }));
  html += renderTable(['Name', 'Role', 'Email', 'Status'], contactRows);

  html += sectionHeader('Opportunities', `<a href="#opportunities/new?funder_id=${id}" class="button button-small">Add opportunity</a>`);
  const oppRows = (funder.opportunities || []).map(o => ({
    cells: [navLink(`opportunities/${o.id}`, o.title), escapeHtml(o.opportunity_type), badge(o.status), formatDate(o.deadline)],
  }));
  html += renderTable(['Title', 'Type', 'Status', 'Deadline'], oppRows);

  app.innerHTML = html;
  $('#delete-funder').addEventListener('click', () => deleteEntity(`/funders/${id}`, funder.name, 'funders'));
}

async function contactList() {
  const contacts = await loadContacts();
  const app = $('#app');
  const actions = `<a href="#contacts/new" class="button">Add contact</a>`;
  let html = pageHeader('Contacts', actions);
  const rows = contacts.map(c => ({
    cells: [
      navLink(`contacts/${c.id}`, c.name),
      escapeHtml(c.funder ? c.funder.name : '—'),
      escapeHtml(c.role || '—'),
      escapeHtml(c.email || '—'),
      badge(c.status),
    ],
  }));
  html += renderTable(['Name', 'Funder', 'Role', 'Email', 'Status'], rows);
  app.innerHTML = html;
}

async function contactForm(id = null, prefill = {}) {
  await loadFunders();
  let contact = { status: 'active', ...prefill };
  if (id) {
    contact = await api(`/contacts/${id}`);
  }
  const app = $('#app');
  const title = id ? 'Edit contact' : 'Add contact';
  let html = pageHeader(title);
  html += `<div class="card"><form id="contact-form">
    <div class="form-grid">
      ${formGroup('Funder', funderSelect('funder_id', contact.funder_id), false)}
      ${formGroup('Name', inputText('name', contact.name, '', true), false)}
      ${formGroup('Role', inputText('role', contact.role), false)}
      ${formGroup('Email', inputText('email', contact.email), false)}
      ${formGroup('Phone', inputText('phone', contact.phone), false)}
      ${formGroup('Status', selectOptions('status', STATUS_OPTIONS.contact, contact.status, true), false)}
      ${formGroup('Notes', textarea('notes', contact.notes), true)}
    </div>
    ${formActions(id ? 'Save changes' : 'Add contact', 'contacts')}
  </form></div>`;
  app.innerHTML = html;
  bindForm('#contact-form', async (data) => {
    if (id) {
      await api(`/contacts/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Contact updated');
    } else {
      await api('/contacts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Contact added');
    }
    setHash('contacts');
  });
}

async function contactDetail(id) {
  const contact = await api(`/contacts/${id}`);
  const app = $('#app');
  let html = pageHeader(contact.name, `<a href="#contacts/${id}/edit" class="button secondary">Edit</a> <button class="danger" id="delete-contact">Delete</button>`);
  html += `<div class="card"><div class="detail-grid">
    <div><strong>Funder</strong><p>${contact.funder ? navLink(`funders/${contact.funder.id}`, contact.funder.name) : '—'}</p></div>
    <div><strong>Role</strong><p>${escapeHtml(contact.role || '—')}</p></div>
    <div><strong>Email</strong><p>${escapeHtml(contact.email || '—')}</p></div>
    <div><strong>Phone</strong><p>${escapeHtml(contact.phone || '—')}</p></div>
    <div><strong>Status</strong><p>${badge(contact.status)}</p></div>
    <div class="full-width"><strong>Notes</strong><p>${escapeHtml(contact.notes || '—')}</p></div>
  </div></div>`;

  html += sectionHeader('Interactions', `<a href="#interactions/new?contact_id=${id}" class="button button-small">Add interaction</a>`);
  const rows = (contact.interactions || []).map(i => ({
    cells: [badge(i.interaction_type), escapeHtml(i.subject || '—'), formatDateTime(i.date), i.opportunity ? navLink(`opportunities/${i.opportunity.id}`, i.opportunity.title) : '—'],
  }));
  html += renderTable(['Type', 'Subject', 'Date', 'Opportunity'], rows);

  app.innerHTML = html;
  $('#delete-contact').addEventListener('click', () => deleteEntity(`/contacts/${id}`, contact.name, 'contacts'));
}

async function opportunityList() {
  const opportunities = await loadOpportunities();
  const app = $('#app');
  const actions = `<a href="#opportunities/new" class="button">Add opportunity</a>`;
  let html = pageHeader('Opportunities', actions);
  const rows = opportunities.map(o => ({
    cells: [
      navLink(`opportunities/${o.id}`, o.title),
      escapeHtml(o.funder ? o.funder.name : '—'),
      escapeHtml(o.opportunity_type),
      badge(o.status),
      escapeHtml(o.amount || '—'),
      formatDate(o.deadline),
    ],
  }));
  html += renderTable(['Title', 'Funder', 'Type', 'Status', 'Amount', 'Deadline'], rows);
  app.innerHTML = html;
}

async function opportunityForm(id = null, prefill = {}) {
  await loadFunders();
  let opportunity = { opportunity_type: 'grant', status: 'prospect', outcome: 'pending', ...prefill };
  if (id) {
    opportunity = await api(`/opportunities/${id}`);
  }
  const app = $('#app');
  const title = id ? 'Edit opportunity' : 'Add opportunity';
  let html = pageHeader(title);
  html += `<div class="card"><form id="opportunity-form">
    <div class="form-grid">
      ${formGroup('Funder', funderSelect('funder_id', opportunity.funder_id), false)}
      ${formGroup('Title', inputText('title', opportunity.title, '', true), false)}
      ${formGroup('Type', selectOptions('opportunity_type', TYPE_OPTIONS.opportunity, opportunity.opportunity_type, true), false)}
      ${formGroup('Status', selectOptions('status', STATUS_OPTIONS.opportunity, opportunity.status, true), false)}
      ${formGroup('Amount', inputText('amount', opportunity.amount, 'e.g. $5,000 or $5K-$10K'), false)}
      ${formGroup('Deadline', inputDate('deadline', opportunity.deadline), false)}
      ${formGroup('Decision date', inputDate('decision_date', opportunity.decision_date), false)}
      ${formGroup('Outcome', selectOptions('outcome', ['pending', 'approved', 'rejected', 'no_response'], opportunity.outcome), false)}
      ${formGroup('Description', textarea('description', opportunity.description), true)}
      ${formGroup('Requirements', textarea('requirements', opportunity.requirements), true)}
      ${formGroup('Notes', textarea('notes', opportunity.notes), true)}
    </div>
    ${formActions(id ? 'Save changes' : 'Add opportunity', 'opportunities')}
  </form></div>`;
  app.innerHTML = html;
  bindForm('#opportunity-form', async (data) => {
    if (id) {
      await api(`/opportunities/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Opportunity updated');
    } else {
      await api('/opportunities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Opportunity added');
    }
    setHash('opportunities');
  });
}

async function opportunityDetail(id) {
  const opportunity = await api(`/opportunities/${id}`);
  const app = $('#app');
  let html = pageHeader(opportunity.title, `<a href="#opportunities/${id}/edit" class="button secondary">Edit</a> <button class="danger" id="delete-opportunity">Delete</button>`);
  html += `<div class="card"><div class="detail-grid">
    <div><strong>Funder</strong><p>${opportunity.funder ? navLink(`funders/${opportunity.funder.id}`, opportunity.funder.name) : '—'}</p></div>
    <div><strong>Type</strong><p>${escapeHtml(opportunity.opportunity_type)}</p></div>
    <div><strong>Status</strong><p>${badge(opportunity.status)}</p></div>
    <div><strong>Outcome</strong><p>${badge(opportunity.outcome)}</p></div>
    <div><strong>Amount</strong><p>${escapeHtml(opportunity.amount || '—')}</p></div>
    <div><strong>Deadline</strong><p>${formatDate(opportunity.deadline)}</p></div>
    <div><strong>Decision date</strong><p>${formatDate(opportunity.decision_date)}</p></div>
    <div class="full-width"><strong>Description</strong><p>${escapeHtml(opportunity.description || '—')}</p></div>
    <div class="full-width"><strong>Requirements</strong><p>${escapeHtml(opportunity.requirements || '—')}</p></div>
    <div class="full-width"><strong>Notes</strong><p>${escapeHtml(opportunity.notes || '—')}</p></div>
  </div></div>`;

  html += sectionHeader('Application steps', '');
  const stepRows = (opportunity.steps || []).map(s => ({
    cells: [escapeHtml(s.title), badge(s.status), formatDate(s.due_date), `<button class="button button-small toggle-step" data-id="${s.id}" data-status="${s.status}">${s.status === 'done' ? 'Reopen' : 'Done'}</button> <button class="button button-small danger delete-step" data-id="${s.id}">Delete</button>`],
  }));
  html += renderTable(['Title', 'Status', 'Due', 'Actions'], stepRows);
  html += `<div class="card"><form id="step-form"><div class="form-grid">
    ${formGroup('Step title', inputText('title', '', '', true), false)}
    ${formGroup('Due date', inputDate('due_date'), false)}
    ${formGroup('Description', textarea('description', ''), true)}
  </div>${formActions('Add step', `opportunities/${id}`)}</form></div>`;

  html += sectionHeader('Interactions', `<a href="#interactions/new?opportunity_id=${id}" class="button button-small">Add interaction</a>`);
  const interactionRows = (opportunity.interactions || []).map(i => ({
    cells: [badge(i.interaction_type), escapeHtml(i.subject || '—'), formatDateTime(i.date), i.contact ? navLink(`contacts/${i.contact.id}`, i.contact.name) : '—'],
  }));
  html += renderTable(['Type', 'Subject', 'Date', 'Contact'], interactionRows);

  html += sectionHeader('Documents', `<a href="#documents/new?opportunity_id=${id}" class="button button-small">Add document</a>`);
  const docRows = (opportunity.documents || []).map(d => ({
    cells: [escapeHtml(d.original_filename), escapeHtml(d.description || '—'), `<a href="/api/documents/${d.id}" target="_blank">Download</a>`],
  }));
  html += renderTable(['File', 'Description', ''], docRows);

  app.innerHTML = html;
  $('#delete-opportunity').addEventListener('click', () => deleteEntity(`/opportunities/${id}`, opportunity.title, 'opportunities'));

  bindForm('#step-form', async (data) => {
    await api(`/opportunities/${id}/steps`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    showSuccess('Step added');
    setHash(`opportunities/${id}`);
  });

  $$('.toggle-step').forEach(btn => btn.addEventListener('click', async (e) => {
    const stepId = e.currentTarget.dataset.id;
    const newStatus = e.currentTarget.dataset.status === 'done' ? 'pending' : 'done';
    try {
      await api(`/opportunities/${id}/steps/${stepId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: newStatus }) });
      showSuccess('Step updated');
      setHash(`opportunities/${id}`);
    } catch (err) { showError(err.message); }
  }));

  $$('.delete-step').forEach(btn => btn.addEventListener('click', async (e) => {
    const stepId = e.currentTarget.dataset.id;
    if (!confirm('Delete this step?')) return;
    try {
      await api(`/opportunities/${id}/steps/${stepId}`, { method: 'DELETE' });
      showSuccess('Step deleted');
      setHash(`opportunities/${id}`);
    } catch (err) { showError(err.message); }
  }));
}

async function interactionList() {
  const interactions = await api('/interactions');
  const app = $('#app');
  const actions = `<a href="#interactions/new" class="button">Add interaction</a>`;
  let html = pageHeader('Interactions', actions);
  const rows = interactions.map(i => ({
    cells: [badge(i.interaction_type), escapeHtml(i.subject || '—'), formatDateTime(i.date), i.contact ? navLink(`contacts/${i.contact.id}`, i.contact.name) : '—', i.opportunity ? navLink(`opportunities/${i.opportunity.id}`, i.opportunity.title) : '—'],
  }));
  html += renderTable(['Type', 'Subject', 'Date', 'Contact', 'Opportunity'], rows);
  app.innerHTML = html;
}

async function interactionForm(id = null, prefill = {}) {
  await Promise.all([loadFunders(), loadContacts(), loadOpportunities()]);
  let interaction = { interaction_type: 'email', date: new Date().toISOString(), ...prefill };
  if (id) {
    interaction = await api(`/interactions/${id}`);
  }
  const app = $('#app');
  const title = id ? 'Edit interaction' : 'Add interaction';
  let html = pageHeader(title);
  html += `<div class="card"><form id="interaction-form">
    <div class="form-grid">
      ${formGroup('Contact', contactSelect('contact_id', interaction.contact_id), false)}
      ${formGroup('Opportunity', opportunitySelect('opportunity_id', interaction.opportunity_id), false)}
      ${formGroup('Type', selectOptions('interaction_type', STATUS_OPTIONS.interaction, interaction.interaction_type, true), false)}
      ${formGroup('Date', inputDate('date', interaction.date), false)}
      ${formGroup('Subject', inputText('subject', interaction.subject), false)}
      ${formGroup('Follow-up date', inputDate('follow_up_date', interaction.follow_up_date), false)}
      ${formGroup('Notes', textarea('notes', interaction.notes), true)}
    </div>
    ${formActions(id ? 'Save changes' : 'Add interaction', 'interactions')}
  </form></div>`;
  app.innerHTML = html;
  bindForm('#interaction-form', async (data) => {
    if (id) {
      await api(`/interactions/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Interaction updated');
    } else {
      await api('/interactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Interaction added');
    }
    setHash('interactions');
  });
}

async function taskList() {
  const tasks = await api('/tasks');
  const app = $('#app');
  const actions = `<a href="#tasks/new" class="button">Add task</a>`;
  let html = pageHeader('Tasks', actions);
  const rows = tasks.map(t => ({
    cells: [escapeHtml(t.title), badge(t.status), formatDate(t.due_date), escapeHtml(t.related_type || '—'), escapeHtml(t.related_id || '—'), `<button class="button button-small toggle-task" data-id="${t.id}" data-status="${t.status}">${t.status === 'done' ? 'Reopen' : 'Done'}</button> <a href="#tasks/${t.id}/edit" class="button button-small secondary">Edit</a>`],
  }));
  html += renderTable(['Title', 'Status', 'Due', 'Related type', 'Related ID', 'Actions'], rows);
  app.innerHTML = html;
  $$('.toggle-task').forEach(btn => btn.addEventListener('click', async (e) => {
    const taskId = e.currentTarget.dataset.id;
    const newStatus = e.currentTarget.dataset.status === 'done' ? 'open' : 'done';
    try {
      await api(`/tasks/${taskId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: newStatus }) });
      showSuccess('Task updated');
      setHash('tasks');
    } catch (err) { showError(err.message); }
  }));
}

async function taskForm(id = null) {
  let task = { status: 'open' };
  if (id) {
    task = await api(`/tasks/${id}`);
  }
  const app = $('#app');
  const title = id ? 'Edit task' : 'Add task';
  let html = pageHeader(title);
  html += `<div class="card"><form id="task-form">
    <div class="form-grid">
      ${formGroup('Title', inputText('title', task.title, '', true), false)}
      ${formGroup('Status', selectOptions('status', STATUS_OPTIONS.task, task.status, true), false)}
      ${formGroup('Due date', inputDate('due_date', task.due_date), false)}
      ${formGroup('Related type', inputText('related_type', task.related_type, 'funder, contact, opportunity'), false)}
      ${formGroup('Related ID', `<input type="number" id="related_id" name="related_id" value="${task.related_id || ''}">`, false)}
      ${formGroup('Notes', textarea('notes', task.notes), true)}
    </div>
    ${formActions(id ? 'Save changes' : 'Add task', 'tasks')}
  </form></div>`;
  app.innerHTML = html;
  bindForm('#task-form', async (data) => {
    if (id) {
      await api(`/tasks/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Task updated');
    } else {
      await api('/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      showSuccess('Task added');
    }
    setHash('tasks');
  });
}

async function documentList() {
  const documents = await api('/documents');
  const app = $('#app');
  const actions = `<a href="#documents/new" class="button">Add document</a>`;
  let html = pageHeader('Documents', actions);
  const rows = documents.map(d => ({
    cells: [escapeHtml(d.original_filename), escapeHtml(d.description || '—'), escapeHtml(d.mime_type || '—'), d.opportunity ? navLink(`opportunities/${d.opportunity.id}`, d.opportunity.title) : '—', `<a href="/api/documents/${d.id}" target="_blank">Download</a>`],
  }));
  html += renderTable(['File', 'Description', 'Type', 'Opportunity', ''], rows);
  app.innerHTML = html;
}

async function documentForm(prefill = {}) {
  await Promise.all([loadFunders(), loadOpportunities()]);
  const app = $('#app');
  let html = pageHeader('Upload document');
  html += `<div class="card"><form id="document-form" enctype="multipart/form-data">
    <div class="form-grid">
      ${formGroup('File', inputFile('file'), false)}
      ${formGroup('Description', textarea('description'), true)}
      ${formGroup('Opportunity', opportunitySelect('opportunity_id', prefill.opportunity_id), false)}
      ${formGroup('Related type', inputText('related_type', prefill.related_type || '', 'funder, contact, opportunity'), false)}
      ${formGroup('Related ID', `<input type="number" id="related_id" name="related_id" value="${prefill.related_id || ''}">`, false)}
    </div>
    ${formActions('Upload', 'documents')}
  </form></div>`;
  app.innerHTML = html;
  $('#document-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    if (!formData.get('file').size) {
      showError('Please choose a file');
      return;
    }
    try {
      await api('/documents', { method: 'POST', body: formData });
      showSuccess('Document uploaded');
      setHash('documents');
    } catch (err) { showError(err.message); }
  });
}

// =============================================================================
// Routing
// =============================================================================

function setActiveNav(route) {
  $$('.nav-link').forEach(a => a.classList.remove('active'));
  const entity = route.split('/')[0];
  const active = $(`.nav-link[data-view="${entity}"]`);
  if (active) active.classList.add('active');
}

async function loadView() {
  const { route, params } = getHash();
  setActiveNav(route);
  const parts = route.split('/').filter(Boolean);
  const [entity, id, action] = parts;

  try {
    if (entity === 'funders') {
      if (!id) await funderList();
      else if (id === 'new') await funderForm(null, Object.fromEntries(params));
      else if (action === 'edit') await funderForm(Number(id));
      else await funderDetail(Number(id));
    } else if (entity === 'contacts') {
      if (!id) await contactList();
      else if (id === 'new') await contactForm(null, Object.fromEntries(params));
      else if (action === 'edit') await contactForm(Number(id));
      else await contactDetail(Number(id));
    } else if (entity === 'opportunities') {
      if (!id) await opportunityList();
      else if (id === 'new') await opportunityForm(null, Object.fromEntries(params));
      else if (action === 'edit') await opportunityForm(Number(id));
      else await opportunityDetail(Number(id));
    } else if (entity === 'interactions') {
      if (!id) await interactionList();
      else if (id === 'new') await interactionForm(null, Object.fromEntries(params));
      else if (action === 'edit') await interactionForm(Number(id));
      else await interactionList();
    } else if (entity === 'tasks') {
      if (!id) await taskList();
      else if (id === 'new') await taskForm();
      else if (action === 'edit') await taskForm(Number(id));
      else await taskList();
    } else if (entity === 'documents') {
      if (id === 'new') await documentForm(Object.fromEntries(params));
      else await documentList();
    } else {
      await dashboard();
    }
  } catch (err) {
    $('#app').innerHTML = `<div class="flash flash-error">${escapeHtml(err.message)}</div>`;
  }
}

function setupSeedButton() {
  const btn = $('#seed-button');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    if (!confirm('Seed the suggested funding entity catalog? Existing records will not be duplicated.')) return;
    try {
      const result = await api('/seed', { method: 'POST' });
      showSuccess(`Seeded ${result.funders_created} funders and ${result.contacts_created} contacts`);
      loadView();
    } catch (err) { showError(err.message); }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupSeedButton();
  window.addEventListener('hashchange', loadView);
  loadView();
});
