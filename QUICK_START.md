# 🚀 Quick Start - Comandos de Inicialização

## Resumo Rápido

Todos os comandos necessários para iniciar o projeto localmente.

---

## ⚡ Quick Fix: Se recebeste erro "uvicorn is not recognized"

O problema é que as dependências não estão instaladas. Executa isto:

```powershell
# Windows PowerShell
cd backend/
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

```bash
# Linux/Mac
cd backend/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 1️⃣ Iniciar Docker Compose (Banco de Dados + Redis)

### Terminal 1: Docker
```bash
cd docker/
docker-compose up -d
```

**Verifica se está a funcionar:**
```bash
docker-compose ps
```

**Serviços iniciados:**
- PostgreSQL (porta 5432)
- Redis (porta 6379)
- pgAdmin (porta 5050)

---

## 2️⃣ Iniciar FastAPI Backend (Uvicorn)

### Terminal 2: Backend API

#### Windows (PowerShell):
```bash
cd backend/

# 1. Criar ambiente virtual (se for primeira vez)
python -m venv venv

# 2. Ativar ambiente virtual
venv\Scripts\Activate.ps1
# Se tiver erro de permissões, executa isto antes:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Inicia o servidor
uvicorn main:app --reload
```

#### Linux/Mac:
```bash
cd backend/

# 1. Criar ambiente virtual (se for primeira vez)
python -m venv venv

# 2. Ativar ambiente virtual
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Inicia o servidor
uvicorn main:app --reload
```

**Acesso:**
- API: `http://localhost:8000`
- Documentação (Swagger): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3️⃣ Iniciar Celery Worker (Opcional - para tarefas assíncronas)

### Terminal 3: Celery Worker
```bash
cd backend/

# Inicia o worker
celery -A app.worker worker --loglevel=info
```

---

## 4️⃣ Monitoring Celery Tasks (Opcional)

### Terminal 4: Flower Dashboard
```bash
cd backend/

# Inicia o Flower
celery -A app.worker flower
```

**Acesso:**
- Flower Dashboard: `http://localhost:5555`

---

## 📊 pgAdmin (Database Management)

Já está disponível quando iniciares Docker:
- **URL:** `http://localhost:5050`
- **Email:** `admin@example.com`
- **Password:** `admin`

---

## 🔧 Setup Inicial (Primeira Vez)

### Windows (PowerShell):
```bash
# 1. Clonar repositório
git clone <repository-url>
cd AI-Music-Producer-Assistent

# 2. Copiar arquivo de ambiente
cp backend/.env.example backend/.env
# Edita o .env com as tuas credenciais OAuth

# 3. Iniciar Docker
cd docker/
docker-compose up -d

# 4. Verificar que tudo está pronto
docker-compose ps

# 5. Voltar para o backend e setup Python
cd ../backend

# 6. Criar ambiente virtual
python -m venv venv

# 7. Ativar ambiente virtual
venv\Scripts\Activate.ps1
# Se tiver erro, executa isto primeiro:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 8. Instalar dependências
pip install -r requirements.txt

# 9. Iniciar Uvicorn
uvicorn main:app --reload
```

### Linux/Mac:
```bash
# 1. Clonar repositório
git clone <repository-url>
cd AI-Music-Producer-Assistent

# 2. Copiar arquivo de ambiente
cp backend/.env.example backend/.env
# Edita o .env com as tuas credenciais OAuth

# 3. Iniciar Docker
cd docker/
docker-compose up -d

# 4. Verificar que tudo está pronto
docker-compose ps

# 5. Voltar para o backend e setup Python
cd ../backend

# 6. Criar ambiente virtual
python -m venv venv

# 7. Ativar ambiente virtual
source venv/bin/activate

# 8. Instalar dependências
pip install -r requirements.txt

# 9. Iniciar Uvicorn
uvicorn main:app --reload
```

---

## 🛑 Parar Serviços

### Parar Docker
```bash
cd docker/
docker-compose down
```

### Parar Uvicorn
- Pressiona `Ctrl+C` no terminal onde estar a correr

### Parar Celery
- Pressiona `Ctrl+C` no terminal onde estar a correr

---

## 📋 Checklist de Verificação

Depois de iniciar tudo, verifica:

- [ ] Docker services: `docker-compose ps` (todos com status "Up")
- [ ] API Response: `curl http://localhost:8000/health`
- [ ] Swagger Docs: Acede a `http://localhost:8000/docs`
- [ ] pgAdmin: Acede a `http://localhost:5050`
- [ ] Celery (se iniciado): Acede a `http://localhost:5555`

---

## 🔑 Configuração OAuth (Necessário para funcionar)

Antes de testar OAuth, edita o arquivo `backend/.env` com:

```env
# Google OAuth
GOOGLE_CLIENT_ID=<teu_client_id>
GOOGLE_CLIENT_SECRET=<teu_secret>
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

# GitHub OAuth
GITHUB_CLIENT_ID=<teu_client_id>
GITHUB_CLIENT_SECRET=<teu_secret>
GITHUB_REDIRECT_URI=http://localhost:3000/auth/github/callback

# Microsoft OAuth
MICROSOFT_CLIENT_ID=<teu_client_id>
MICROSOFT_CLIENT_SECRET=<teu_secret>
MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback
```

Ver `docs/OAUTH_SETUP.md` para instruções detalhadas.

---

## 🧪 Testar API

### Test Health Check
```bash
curl http://localhost:8000/health
```

### Test OAuth Endpoint
```bash
curl http://localhost:8000/api/v1/users/auth/google/login
```

### Test com dados (Project)
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <seu_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Meu Projeto", "description": "Teste"}'
```

---

## 📝 Estrutura de Sessões (Múltiplos Terminais)

Para desenvolvimento eficiente, usa múltiplos terminais:

```
Terminal 1: docker-compose up -d
Terminal 2: uvicorn main:app --reload
Terminal 3: celery -A app.worker worker --loglevel=info
Terminal 4: celery -A app.worker flower (opcional)
```

---

## 🐛 Troubleshooting

### ❌ "uvicorn is not recognized" (Windows PowerShell)
**Solução:** Precisa ativar o ambiente virtual e instalar dependências:
```powershell
cd backend/
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

**Nota:** Após ativar o venv, deves ver `(venv)` no início da linha de comando.

### ❌ "cannot be loaded because running scripts is disabled" (PowerShell)
**Solução:** Executa isto uma vez:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Depois tenta novamente: `venv\Scripts\Activate.ps1`

### Porta 8000 já em uso
```bash
# Encontra o processo
lsof -i :8000

# Mata o processo (Linux/Mac)
kill -9 <PID>

# ou usa outra porta
uvicorn main:app --reload --port 8001
```

### PostgreSQL não conecta
```bash
# Verifica status
docker-compose ps postgres

# Vê os logs
docker-compose logs postgres

# Reinicia
docker-compose restart postgres
```

### Redis não conecta
```bash
# Verifica status
docker-compose ps redis

# Vê os logs
docker-compose logs redis
```

---

## 📚 Referências

- [README Principal](README.md)
- [Backend Documentation](backend/README.md)
- [Docker Configuration](docker/docker-compose.yml)
- [OAuth Setup](docs/OAUTH_SETUP.md)
- [Worker Integration](docs/INTEGRACAO_WORKER.md)