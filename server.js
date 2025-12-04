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
app.use(express.static(__dirname));

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

// Rota padrão: Se acessar a raiz, entrega o index.html (Opcional, pois o static já faz isso, mas garante)
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
    console.log(`\n🚀 Servidor Node (Proxy + Site) rodando em: http://localhost:${PORT}`);
    console.log(`🌐 Acesse o sistema em: http://localhost:${PORT}`);
});