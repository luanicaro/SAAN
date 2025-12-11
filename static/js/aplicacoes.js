async function ensureEngineer() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.status === 401) { window.location.href = '/login'; return false; }
    const data = await res.json();
    if (!data?.user || !['engenheiro', 'admin'].includes(data.user.role)) {
      window.location.href = '/';
      return false;
    }
    return true;
  } catch {
    window.location.href = '/login';
    return false;
  }
}

function setMsg(text, isError=false) {
  const el = document.getElementById('msg');
  el.classList.remove('hidden');
  el.classList.toggle('error', !!isError);
  el.textContent = text;
}

function clearMsg() {
  const el = document.getElementById('msg');
  el.classList.add('hidden');
  el.classList.remove('error');
  el.textContent = '';
}

async function loadForms() {
  const sel = document.getElementById('form-select');
  sel.innerHTML = '<option value="">Carregando...</option>';
  const res = await fetch('/api/forms');
  if (!res.ok) throw new Error('Falha ao carregar formulários');
  const forms = await res.json();
  if (!forms.length) {
    sel.innerHTML = '<option value="">Nenhum formulário cadastrado</option>';
  } else {
    sel.innerHTML = forms.map((f) => `<option value="${f.id}">${escapeHtml(f.title || 'Sem título')} (ID ${f.id})</option>`).join('');
  }
}

async function loadEvaluators() {
  const box = document.getElementById('evaluators-select');
  box.innerHTML = '<option>Carregando avaliadores...</option>';
  const res = await fetch('/api/users?role=avaliador');
  if (!res.ok) throw new Error('Falha ao carregar avaliadores');
  const users = await res.json();
  if (!users.length) { box.innerHTML = ''; return; }
  box.innerHTML = users.map(u => `<option value="${u.username}">${escapeHtml(u.username)} (ID ${u.id})</option>`).join('');
}

async function loadApps() {
  const list = document.getElementById('apps-list');
  list.innerHTML = '';
  const res = await fetch('/api/applications');
  if (!res.ok) return;
  const apps = await res.json();
  if (!apps.length) { list.innerHTML = '<div class="app-sub">Nenhuma aplicação cadastrada.</div>'; return; }
  list.innerHTML = apps.map(a => `
    <div class="app-card">
      <div><strong>${escapeHtml(a.name)}</strong></div>
      <div class="app-sub">Tipo: ${escapeHtml(a.type)} | Formulário: #${a.formId} | Avaliadores: ${a.evaluators.map(escapeHtml).join(', ')}</div>
      ${a.url ? `<div class="app-sub">URL/Pacote: ${escapeHtml(a.url)}</div>` : ''}
    </div>
  `).join('');
}

function getSelectedEvaluators() {
  const sel = document.getElementById('evaluators-select');
  return Array.from(sel.selectedOptions).map(o => o.value);
}

function escapeHtml(t){ return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function onSave() {
  clearMsg();
  const name = document.getElementById('app-name').value.trim();
  const appType = document.getElementById('app-type').value;
  const formId = parseInt(document.getElementById('form-select').value, 10);
  const url = document.getElementById('app-url').value.trim();
  const evaluators = getSelectedEvaluators();
  if (!name) { setMsg('Informe o nome da aplicação', true); return; }
  if (Number.isNaN(formId)) { setMsg('Selecione um formulário', true); return; }
  if (!evaluators.length) { setMsg('Selecione pelo menos um avaliador', true); return; }

  const res = await fetch('/api/applications', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, appType, url, formId, evaluators })
  });
  if (!res.ok) {
    const data = await res.json().catch(()=>({}));
    setMsg(data?.detail || 'Falha ao salvar', true);
    return;
  }
  setMsg('Aplicação cadastrada com sucesso!');
  document.getElementById('app-name').value = '';
  document.getElementById('app-url').value = '';
  const sel = document.getElementById('evaluators-select');
  Array.from(sel.options).forEach(o => o.selected = false);
  await loadApps();
}

async function init() {
  const ok = await ensureEngineer();
  if (!ok) return;
  try {
    await Promise.all([loadForms(), loadEvaluators(), loadApps()]);
  } catch (e) { setMsg(e.message || 'Erro ao carregar dados', true); }
  document.getElementById('btn-save').addEventListener('click', onSave);
}

document.addEventListener('DOMContentLoaded', init);
