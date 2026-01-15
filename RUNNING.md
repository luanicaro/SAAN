# Como rodar o Projeto SAAN

Este projeto agora utiliza um frontend em Next.js (`front-saan`) integrado a um backend Python (FastAPI).

## Pré-requisitos

1.  **Python 3.8+**
2.  **Node.js 18+**

## Passo 1: Rodar o Backend (Python)

Abra um terminal na raiz do projeto (`/home/luan/SAAN`) e execute:

```bash
# Ativar ambiente virtual (se houver, ex: venv)
# source venv/bin/activate

# Instalar dependências (caso não tenha feito)
pip install -r requirements.txt

# Rodar o servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O backend estará rodando em `http://127.0.0.1:8000`.

## Passo 2: Rodar o Frontend (Next.js)

Abra **outro** terminal, entre na pasta `front-saan` e execute:

```bash
cd front-saan

# Instalar dependências (apenas na primeira vez)
npm install

# Rodar em modo de desenvolvimento
npm run dev
```

O frontend estará rodando em `http://localhost:3000`.

## Passo 3: Acessar a Aplicação

Abra o navegador e acesse: **[http://localhost:3000](http://localhost:3000)**

Qualquer requisição que o frontend fizer para `/api/*` será automaticamente redirecionada para o backend Python na porta 8000.
