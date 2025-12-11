const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path'); // [NOVO] Importante para lidar com caminhos de arquivos

const app = express();
const PORT = 3000;
const PYTHON_BACKEND_URL = 'http://localhost:8000';

// 1. Configuração de CORS
app.use(cors());

// 2. Logging
app.use((req, res, next) => {
    console.log(`[Proxy Node] Recebida requisição: ${req.method} ${req.url}`);
    next();
});

// 3. Servir Arquivos Estáticos (HTML, CSS, JS) [NOVO]
// Isso faz com que o Node sirva qualquer arquivo na pasta atual
// Servir arquivos estáticos (CSS, JS, imagens) da pasta `static` sob o prefixo '/static'
app.use('/static', express.static(path.join(__dirname, 'static')));

// Helper simples para ler cookies sem dependências externas
function getCookies(req) {
    const header = req.headers['cookie'];
    const list = {};
    if (!header) return list;
    header.split(';').forEach(cookie => {
        const parts = cookie.split('=');
        const key = decodeURIComponent(parts[0].trim());
        const val = decodeURIComponent((parts[1] || '').trim());
        list[key] = val;
    });
    return list;
}

function requireAuth(req, res, next) {
    const cookies = getCookies(req);
    if (!cookies['access_token']) {
        return res.redirect('/login');
    }
    next();
}

// 4. Configuração do Proxy para a API
// Chamadas para /api/... vão para o Python
app.use('/api', createProxyMiddleware({
    target: PYTHON_BACKEND_URL,
    changeOrigin: true,
    pathRewrite: {
        '^/api': '', 
    },
    onError: (err, req, res) => {
        console.error('[Proxy Error] Não foi possível conectar ao Python:', err.message);
        res.status(500).send('Erro no Proxy: O backend Python parece estar desligado.');
    }
}));

// Rotas para templates HTML (agora em templates/)
app.get('/', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});
app.get('/cadastro.html', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'cadastro.html'));
});
app.get('/visualizar.html', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'visualizar.html'));
});

// Login e Logout
app.get('/login', (req, res) => {
    const cookies = getCookies(req);
    if (cookies['access_token']) {
        return res.redirect('/');
    }
    res.sendFile(path.join(__dirname, 'templates', 'login.html'));
});

app.get('/aplicacoes.html', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'aplicacoes.html'));
});

app.get('/cliente.html', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'cliente.html'));
});


app.listen(PORT, () => {
    console.log(`\n🚀 Servidor Node (Proxy + Site) rodando em: http://localhost:${PORT}`);
    console.log(`🌐 Acesse o sistema em: http://localhost:${PORT}`);
});