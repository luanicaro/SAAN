// Modo: avaliador vê tarefas atribuídas; outros perfis visualizam formulários
document.addEventListener('DOMContentLoaded', async () => {
    lucide.createIcons();
    const meRes = await fetch('/api/auth/me');
    if (meRes.status === 401) { window.location.href = '/login'; return; }
    const me = await meRes.json().catch(()=>({}));
    const role = me?.user?.role;
    if (role === 'avaliador') {
        loadAssignments();
    } else {
        fetchForms();
    }
});

async function loadAssignments() {
    const contentArea = document.getElementById('content-area');
    try {
        const res = await fetch('/api/my-assignments');
        if (res.status === 401) { window.location.href = '/login'; return; }
        if (!res.ok) throw new Error('Erro ao buscar atribuições');
        const tasks = await res.json();
        renderAssignments(tasks);
    } catch (e) {
        contentArea.innerHTML = errorBlock('Erro ao carregar atribuições', 'loadAssignments()');
        lucide.createIcons();
    }
}

function renderAssignments(tasks) {
    const contentArea = document.getElementById('content-area');
    if (!tasks.length) {
        contentArea.innerHTML = `
            <div class="empty-state">
                <i data-lucide="inbox" style="width:48px;height:48px;margin-bottom:16px"></i>
                <h3>Nenhuma avaliação atribuída</h3>
                <p>Aguarde o Engenheiro atribuir um formulário a você.</p>
            </div>`;
        lucide.createIcons();
        return;
    }
    // Cabeçalho com seletor
    const selector = document.createElement('div');
    selector.style.marginBottom = '16px';
    selector.innerHTML = `
        <div class="form-header">
            <span class="badge">Minhas Avaliações</span>
            <div style="margin-top:8px; display:flex; gap:12px; align-items:center; flex-wrap: wrap;">
                <label class="desc" for="task-select">Selecionar avaliação:</label>
                <select id="task-select" style="padding:8px; background:#0f172a; color:white; border:1px solid var(--border); border-radius:8px;"></select>
                <span id="task-status" class="desc"></span>
            </div>
        </div>`;
    contentArea.innerHTML = '';
    contentArea.appendChild(selector);
    const select = selector.querySelector('#task-select');
    select.innerHTML = tasks.map((t, i) => {
        const label = `${t.applicationName} • ${t.form?.title || 'Formulário'} ${t.completed ? '(Concluído)' : ''}`;
        return `<option value="${i}">${escapeHtml(label)}</option>`;
    }).join('');

    const initialIndex = tasks.findIndex(t => !t.completed);
    select.selectedIndex = initialIndex >= 0 ? initialIndex : 0;
    renderSelectedTask(tasks[select.value | 0]);
    select.addEventListener('change', () => {
        renderSelectedTask(tasks[select.value | 0]);
    });
}

function renderSelectedTask(task) {
    const contentArea = document.getElementById('content-area');
    // Remove qualquer formulário renderizado anteriormente (mantém o primeiro filho = seletor)
    while (contentArea.children.length > 1) contentArea.removeChild(contentArea.lastChild);
    const status = document.getElementById('task-status');
    status.textContent = task.completed ? 'Status: Concluído' : 'Status: Pendente';

    const form = task.form;
    const wrapper = document.createElement('div');
    wrapper.className = 'form-wrapper';
    let html = `
        <div class="form-header">
            <span class="badge">Aplicação: ${escapeHtml(task.applicationName)}</span>
            <h2>${escapeHtml(form.title || 'Formulário')}</h2>
            <p class="desc">${escapeHtml(form.description || 'Sem descrição definida.')}</p>
        </div>`;
    if (form.questions && form.questions.length) {
        form.questions.forEach((q, qIndex) => {
            html += `
                <div class="question-card" data-question-id="${q.id}">
                    <div class="q-title">${qIndex + 1}. ${escapeHtml(q.text)}</div>
                    ${q.example ? `<span class="q-example"><i data-lucide="info" style="width:12px;display:inline"></i> Exemplo: ${escapeHtml(q.example)}</span>` : ''}
                    <div class="options-grid">
                        ${[1,2,3,4,5].map(v => optionButtonHtml(v)).join('')}
                    </div>
                </div>`;
        });
        html += `<button class="refresh-btn" id="submit-btn" style="margin-top:12px" onclick='submitAnswers(${task.applicationId}, ${task.formId}, this)'><i data-lucide="send"></i> Enviar Respostas</button>`;
    } else {
        html += `<div style="padding: 20px; border: 1px dashed var(--border); border-radius: 8px; color: var(--text-sec); text-align: center;">Este formulário não possui perguntas.</div>`;
    }
    wrapper.innerHTML = html;
    contentArea.appendChild(wrapper);
    if (task.completed) {
        const btn = document.getElementById('submit-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Já enviado'; }
    }
    lucide.createIcons();
}

function optionButtonHtml(value) {
    const labels = {1:'Discordo<br>Fortemente',2:'Discordo',3:'Neutro',4:'Concordo',5:'Concordo<br>Fortemente'};
    return `<button class="option-btn" data-value="${value}" onclick="selectOption(this)">${labels[value]}</button>`;
}

async function submitAnswers(applicationId, formId, btn) {
    const wrapper = btn.closest('.form-wrapper');
    const questions = Array.from(wrapper.querySelectorAll('.question-card'));
    const answers = [];
    for (const q of questions) {
        const qid = parseInt(q.getAttribute('data-question-id'), 10);
        const active = q.querySelector('.option-btn.active-blue');
        if (!active) { alert('Responda todas as perguntas.'); return; }
        const value = parseInt(active.getAttribute('data-value'), 10);
        answers.push({ questionId: qid, value });
    }
    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
        const res = await fetch('/api/responses', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ applicationId, formId, answers })
        });
        if (res.status === 401) { window.location.href = '/login'; return; }
        if (!res.ok) { const d = await res.json().catch(()=>({})); throw new Error(d?.detail || 'Falha ao enviar'); }
        btn.textContent = 'Enviado!';
    } catch (e) {
        alert(e.message || 'Erro ao enviar respostas');
        btn.disabled = false; btn.textContent = 'Enviar Respostas';
    }
}

// Visualização de formulários (para outros perfis)
async function fetchForms() {
    const contentArea = document.getElementById('content-area');
    try {
        const res = await fetch('/api/forms');
        if (res.status === 401) { window.location.href = '/login'; return; }
        if (!res.ok) throw new Error('Erro na conexão');
        const forms = await res.json();
        renderForms(forms);
    } catch (err) {
        contentArea.innerHTML = errorBlock('Erro de Conexão', 'fetchForms()');
        lucide.createIcons();
    }
}

function renderForms(forms) {
    const contentArea = document.getElementById('content-area');
    if (forms.length === 0) {
        contentArea.innerHTML = `
            <div class="empty-state">
                <i data-lucide="folder-open" style="width: 48px; height: 48px; margin-bottom: 16px;"></i>
                <h3>Nenhum formulário disponível</h3>
                <p>Aguarde o administrador cadastrar novas avaliações.</p>
                <a href="cadastro.html" class="refresh-btn" style="text-decoration:none;">Criar Formulário</a>
            </div>`;
        lucide.createIcons();
        return;
    }
    contentArea.innerHTML = '';
    [...forms].reverse().forEach((form, index) => {
        const formWrapper = document.createElement('div');
        formWrapper.className = 'form-wrapper';
        let html = `
            <div class="form-header">
                <span class="badge">Formulário #${forms.length - index}</span>
                <h2>${escapeHtml(form.title)}</h2>
                <p class="desc">${escapeHtml(form.description || 'Sem descrição definida.')}</p>
            </div>`;
        if (form.questions && form.questions.length > 0) {
            form.questions.forEach((q, qIndex) => {
                html += `
                    <div class="question-card">
                        <div class="q-title">${qIndex + 1}. ${escapeHtml(q.text)}</div>
                        ${q.example ? `<span class="q-example"><i data-lucide="info" style="width:12px; display:inline"></i> Exemplo: ${escapeHtml(q.example)}</span>` : ''}
                        <div class="options-grid">
                            <button class="option-btn" onclick="selectOption(this)">Discordo<br>Fortemente</button>
                            <button class="option-btn" onclick="selectOption(this)">Discordo</button>
                            <button class="option-btn" onclick="selectOption(this)">Neutro</button>
                            <button class="option-btn" onclick="selectOption(this)">Concordo</button>
                            <button class="option-btn" onclick="selectOption(this)">Concordo<br>Fortemente</button>
                        </div>
                    </div>`;
            });
        } else {
            html += `<div style="padding: 20px; border: 1px dashed var(--border); border-radius: 8px; color: var(--text-sec); text-align: center;">Este formulário não possui perguntas.</div>`;
        }
        formWrapper.innerHTML = html;
        contentArea.appendChild(formWrapper);
    });
    lucide.createIcons();
}

// Função visual de seleção
window.selectOption = function(btn) {
    const siblings = btn.parentElement.children;
    for (let sibling of siblings) sibling.classList.remove('active-blue');
    btn.classList.add('active-blue');
}

function errorBlock(title, retryFn){
    return `<div class="empty-state">
        <i data-lucide="wifi-off" style="width:48px;height:48px;margin-bottom:16px"></i>
        <h3>${title}</h3>
        <button class="refresh-btn" onclick="${retryFn}">Tentar Novamente</button>
    </div>`;
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
