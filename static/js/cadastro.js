let questions = [{ id: 1, text: '', example: '', scaleType: '5-point' }];

document.addEventListener('DOMContentLoaded', () => {
    ensureAdmin();
    renderQuestions();
    setupFileUpload();
});

async function ensureAdmin() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 401) { window.location.href = '/login'; return; }
        const data = await res.json();
        if (!data?.user || data.user.role !== 'admin') {
            window.location.href = '/';
        }
    } catch (_) {
        window.location.href = '/login';
    }
}

function renderQuestions() {
    const container = document.getElementById('questions-container');
    container.innerHTML = '';

    questions.forEach((q, index) => {
        const card = document.createElement('div');
        card.className = 'question-card';
        card.innerHTML = `
                    <div class="question-number">#${index + 1}</div>
                    
                    <div style="margin-bottom: 16px;">
                        <label>Pergunta</label>
                        <input type="text" value="${q.text}" 
                            placeholder="Digite a pergunta aqui..." 
                            oninput="updateQuestion(${q.id}, 'text', this.value)">
                    </div>

                    <div class="example-box">
                        <span class="example-label"><i data-lucide="help-circle" style="width:12px; display:inline"></i> Exemplo de Apoio (Contexto)</span>
                        <input type="text" class="input-example" 
                            value="${q.example}" 
                            placeholder="Ajude o avaliador a entender..."
                            oninput="updateQuestion(${q.id}, 'example', this.value)">
                    </div>

                    <button type="button" class="btn-delete" onclick="removeQuestion(${q.id})" ${questions.length === 1 ? 'disabled' : ''}>
                        <i data-lucide="trash-2" style="width: 14px;"></i> Remover Pergunta
                    </button>
                `;
        container.appendChild(card);
    });
    lucide.createIcons();
}

function addQuestion() {
    const maxId = questions.length > 0 ? Math.max(...questions.map(q => q.id)) : 0;
    questions.push({ id: maxId + 1, text: '', example: '', scaleType: '5-point' });
    renderQuestions();
}

function removeQuestion(id) {
    if (questions.length <= 1) return;
    questions = questions.filter(q => q.id !== id);
    renderQuestions();
}

function updateQuestion(id, field, value) {
    const q = questions.find(item => item.id === id);
    if (q) q[field] = value;
}

function setupFileUpload() {
    const fileInput = document.getElementById('file-input');
    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const lines = e.target.result.split(/\r?\n/).filter(line => line.trim() !== '');
            if (lines.length === 0) { showFeedback('feedback-file-empty'); return; }
                    
            if (questions.length === 1 && questions[0].text.trim() === '') questions = [];
                    
            const maxId = questions.length > 0 ? Math.max(...questions.map(q => q.id)) : 0;
            
            // --- INÍCIO DA ALTERAÇÃO ---
            const newQs = lines.map((line, idx) => {
                let qText = line;
                let qExample = '';

                // Procura por "exemplo:" ignorando maiúsculas/minúsculas (flag 'i')
                const regex = /exemplo:/i;
                
                // Se encontrar o separador
                if (regex.test(line)) {
                    const parts = line.split(regex);
                    qText = parts[0].trim();
                    // Pega o restante como exemplo (caso haja algo depois)
                    qExample = parts.slice(1).join('exemplo:').trim(); 
                } else {
                    qText = line.trim();
                }

                return { 
                    id: maxId + idx + 1, 
                    text: qText, 
                    example: qExample, 
                    scaleType: '5-point' 
                };
            });
            // --- FIM DA ALTERAÇÃO ---

            questions = [...questions, ...newQs];
            renderQuestions();
            showFeedback('feedback-import');
            fileInput.value = '';
        };
        reader.onerror = () => showFeedback('feedback-error');
        reader.readAsText(file);
    });
}

function resetForm() {
    document.getElementById('form-title').value = '';
    document.getElementById('form-desc').value = '';
    questions = [{ id: 1, text: '', example: '', scaleType: '5-point' }];
    renderQuestions();
    document.getElementById('feedback-success').classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function handleSave() {
    const title = document.getElementById('form-title').value;
    if (!title.trim()) { showFeedback('feedback-validation'); return; }

    const payload = { title, description: document.getElementById('form-desc').value, questions };

    try {
        const res = await fetch('/api/forms', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        });
        if (res.status === 401) { window.location.href = '/login'; return; }
        if (res.ok) {
            document.getElementById('feedback-error').classList.add('hidden');
            document.getElementById('feedback-validation').classList.add('hidden');
            const success = document.getElementById('feedback-success');
            success.classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
            success.focus();
        } else { showFeedback('feedback-error'); }
    } catch (e) { showFeedback('feedback-error'); }
}

function showFeedback(id) {
    ['feedback-success', 'feedback-error', 'feedback-import', 'feedback-file-empty', 'feedback-validation'].forEach(eid => document.getElementById(eid).classList.add('hidden'));
    const el = document.getElementById(id);
    if(el) { el.classList.remove('hidden'); if(id !== 'feedback-success') setTimeout(() => el.classList.add('hidden'), 4000); }
}
