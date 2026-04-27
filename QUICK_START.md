# Quick Start

Comandos reais para levantar o projeto no estado atual do código.

## 1. Levantar stack completa com Docker

```bash
cd docker
docker compose up -d
docker compose ps
```

Serviços esperados:
- postgres
- redis
- backend
- celery_worker
- pgadmin

## 2. Verificar endpoints principais

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- pgAdmin: `http://localhost:5050`

## 3. Rodar backend localmente (opcional)

Usa isto se não quiseres usar o container `backend`.

### Windows PowerShell

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

## 4. Rodar worker localmente (opcional)

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

Flower (opcional):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

## 5. Parar serviços

```bash
cd docker
docker compose down
```

## 6. OAuth no estado atual

Implementado no código:
- Google login

Endpoints:
- `GET /api/v1/users/auth/google/login`
- `GET /api/v1/users/auth/google/callback?code=...`

As rotas de GitHub/Microsoft não estão implementadas em `backend/app/api/endpoints/user.py`.

## 7. Checklist rápido

- [ ] `docker compose ps` mostra serviços `Up`
- [ ] `GET /health` responde
- [ ] `/docs` abre
- [ ] Worker consome tasks quando fazes `POST /api/v1/generation`

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