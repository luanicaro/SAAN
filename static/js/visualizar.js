// URL da API (Via Proxy)
const API_URL = '/api/forms'; 

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    fetchForms();
});

async function fetchForms() {
    const contentArea = document.getElementById('content-area');
    
    try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error('Erro na conexão');
        
        const forms = await res.json();
        renderForms(forms);

    } catch (err) {
        console.error(err);
        contentArea.innerHTML = `
            <div class="empty-state">
                <i data-lucide="wifi-off" style="width: 48px; height: 48px; margin-bottom: 16px;"></i>
                <h3>Erro de Conexão</h3>
                <p>Verifique se o backend Python está rodando.</p>
                <button class="refresh-btn" onclick="fetchForms()">Tentar Novamente</button>
            </div>`;
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

    // Limpa o loader
    contentArea.innerHTML = '';

    // Itera sobre TODOS os formulários (Inverso para o mais recente aparecer primeiro)
    [...forms].reverse().forEach((form, index) => {
        const formWrapper = document.createElement('div');
        formWrapper.className = 'form-wrapper';

        let html = `
            <div class="form-header">
                <span class="badge">Formulário #${forms.length - index}</span>
                <h2>${escapeHtml(form.title)}</h2>
                <p class="desc">${escapeHtml(form.description || 'Sem descrição definida.')}</p>
            </div>
        `;

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
                    </div>
                `;
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
    for (let sibling of siblings) {
        sibling.classList.remove('active-blue');
    }
    btn.classList.add('active-blue');
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
