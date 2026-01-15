function showTab(name) {
  const loginBtn = document.getElementById('tab-login');
  const regBtn = document.getElementById('tab-register');
  const loginPane = document.getElementById('login-pane');
  const regPane = document.getElementById('register-pane');

  if (name === 'login') {
    loginBtn.classList.add('active');
    regBtn.classList.remove('active');
    loginPane.classList.remove('hidden');
    regPane.classList.add('hidden');
  } else {
    regBtn.classList.add('active');
    loginBtn.classList.remove('active');
    regPane.classList.remove('hidden');
    loginPane.classList.add('hidden');
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

// Login
const loginForm = document.getElementById('login-form');
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearMsg();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data?.detail || 'Falha no login');
    }
    // Cookie HTTPOnly é salvo automaticamente
    window.location.href = '/';
  } catch (err) {
    setMsg(err.message || 'Erro ao autenticar', true);
  }
});

// Register
const regForm = document.getElementById('register-form');
regForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearMsg();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const role = document.getElementById('reg-role').value;
  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role })
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data?.detail || 'Falha no cadastro');
    }
    setMsg('Conta criada! Agora faça login.');
    showTab('login');
  } catch (err) {
    setMsg(err.message || 'Erro ao cadastrar', true);
  }
});
