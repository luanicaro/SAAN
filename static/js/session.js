async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (_) {}
  window.location.href = '/login';
}

window.logout = logout;
