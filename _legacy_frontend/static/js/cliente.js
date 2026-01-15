async function ensureStakeholder() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.status === 401) { window.location.href = '/login'; return false; }
    const data = await res.json();
    const role = data?.user?.role;
    if (!['stakeholder', 'admin', 'engenheiro'].includes(role)) { window.location.href = '/'; return false; }
    return true;
  } catch { window.location.href = '/login'; return false; }
}

function setMsg(text, isError=false) {
  const el = document.getElementById('msg');
  el.classList.remove('hidden');
  el.classList.toggle('error', !!isError);
  el.textContent = text;
}
function clearMsg(){ const el = document.getElementById('msg'); el.classList.add('hidden'); el.classList.remove('error'); el.textContent=''; }

async function loadApps() {
  const sel = document.getElementById('app-select');
  sel.innerHTML = '<option>Carregando...</option>';
  const res = await fetch('/api/applications');
  if (!res.ok) { setMsg('Falha ao carregar aplicações', true); return; }
  const apps = await res.json();
  if (!apps.length) { sel.innerHTML = '<option value="">Nenhuma aplicação encontrada</option>'; return; }
  sel.innerHTML = apps.map(a => `<option value="${a.id}">${escapeHtml(a.name)} (ID ${a.id})</option>`).join('');
}

function renderScore(data) {
  const result = document.getElementById('result');
  const valueEl = document.getElementById('score-value');
  const bar = document.getElementById('progress-bar');
  const metaResp = document.getElementById('meta-respostas');
  const metaItens = document.getElementById('meta-itens');
  if (!data || data.score === null || data.score === undefined) {
    valueEl.textContent = '--';
    bar.style.width = '0%';
    metaResp.textContent = '0 avaliações';
    metaItens.textContent = '0 respostas';
    result.classList.remove('hidden');
    return;
  }
  const score = Number(data.score);
  valueEl.textContent = score.toFixed(2);
  bar.style.width = `${Math.max(0, Math.min(10, score)) * 10}%`;
  metaResp.textContent = `${data.countResponses} avaliação(ões)`;
  metaItens.textContent = `${data.countAnswers} resposta(s)`;
  result.classList.remove('hidden');
}

function escapeHtml(t){ return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function onView() {
  clearMsg();
  const sel = document.getElementById('app-select');
  const id = parseInt(sel.value, 10);
  if (Number.isNaN(id)) { setMsg('Selecione uma aplicação', true); return; }
  try {
    const res = await fetch(`/api/reports/application-score?applicationId=${id}`);
    if (res.status === 401) { window.location.href = '/login'; return; }
    if (!res.ok) throw new Error('Falha ao consultar relatório');
    const data = await res.json();
    renderScore(data);
  } catch (e) { setMsg(e.message || 'Erro ao consultar relatório', true); }
}

async function init(){
  const ok = await ensureStakeholder();
  if (!ok) return;
  await loadApps();
  document.getElementById('btn-ver').addEventListener('click', onView);
}

document.addEventListener('DOMContentLoaded', init);
