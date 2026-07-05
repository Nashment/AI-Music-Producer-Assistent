# Quick Start

Comandos reais para levantar o projeto no estado atual do código.

## 1. Pré-requisitos

- Docker + Docker Compose (≥ 24)
- Python 3.11+ (para execução local do backend)
- Node.js ≥ 20 + npm ≥ 10 (para desenvolvimento nativo do frontend)
- Ficheiro `docker/.env` configurado (ver secção Variáveis de Ambiente)

## 2. Levantar stack completa com Docker

```bash
cd docker
docker compose up -d
docker compose ps
```

Serviços esperados em estado `Up`:

| Serviço                   | URL / Porta              |
|---------------------------|--------------------------|
| Frontend (Vite + Nginx)   | http://localhost:5173    |
| Backend API               | http://localhost:8000    |
| Swagger UI                | http://localhost:8000/docs |
| ReDoc                     | http://localhost:8000/redoc |
| pgAdmin                   | http://localhost:5050    |
| PostgreSQL                | localhost:5432           |
| Redis                     | localhost:6379           |

> A porta do frontend pode ser alterada com a variável `FRONTEND_PORT` no `docker/.env`.

## 3. Backend local (sem container do backend)

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

> O servidor fica disponível em `http://localhost:8000`.

## 4. Workers Celery locais

Existem duas filas — recomenda-se correr cada worker numa janela separada:

```bash
# Fila de geração Suno + pós-processamento
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=celery --loglevel=info
```

```bash
# Fila de notação (tablatura + partitura)
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=notation --loglevel=info
```

Flower (painel de monitorização, opcional):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

> O Flower fica disponível em `http://localhost:5555`.

## 5. Frontend local (dev nativo com HMR)

Para iterar no frontend com hot-module reload:

```bash
cd frontend
npm install
npm run dev
```

> A aplicação abre em `http://localhost:5173`. O Vite faz proxy de `/api/*` para
> `http://localhost:8000/api/v1/*`. O backend tem de estar a correr (Docker ou local).

```bash
# Levantar só os serviços de backend (mantendo HMR no frontend)
cd docker
docker compose up postgres redis backend celery_worker celery_worker_notation -d
```

> Se o container `frontend` também estiver a correr na porta 5173, pára-o primeiro
> para evitar conflito: `docker compose stop frontend`.

## 6. Parar serviços

```bash
cd docker
docker compose down
```

## 7. Variáveis de Ambiente

Ficheiro: `docker/.env`

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `JWT_SECRET_KEY` | Sim | Chave secreta para assinar JWTs |
| `JWT_ALGORITHM` | Não (default: `HS256`) | Algoritmo JWT |
| `JWT_EXPIRATION_HOURS` | Não (default: `24`) | Validade do token em horas |
| `GOOGLE_CLIENT_ID` | Sim | Client ID do Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Sim | Client Secret do Google OAuth |
| `GOOGLE_REDIRECT_URI` | Sim | URI de callback registada no Google |
| `DATABASE_URL` | Sim | URL PostgreSQL async (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Não (default: `redis://localhost:6379/0`) | URL do Redis |
| `FRONTEND_PORT` | Não (default: `5173`) | Porta exposta do container frontend |
| `AUDIO_UPLOAD_DIR` | Não | Diretório de uploads de áudio |
| `GENERATIONS_AUDIO_DIR` | Não | Diretório de output de áudio gerado |
| `GENERATIONS_PARTITURA_DIR` | Não | Diretório de output de partituras |
| `GENERATIONS_TABLATURA_DIR` | Não | Diretório de output de tablaturas |

## 8. Fluxo de teste rápido (API)

```bash
# 1. Verificar que a API está viva
curl http://localhost:8000/health

# 2. Obter URL de login Google
curl http://localhost:8000/api/v1/users/auth/google/login

# 3. Criar projeto (com token JWT obtido no callback)
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Teste", "description": "Projeto de teste", "tempo": 120}'

# 4. Upload de áudio
curl -X POST http://localhost:8000/api/v1/audio/project/<project_id>/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/caminho/para/ficheiro.mp3"

# 5. Submeter geração
curl -X POST http://localhost:8000/api/v1/generation \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<id>", "audio_id": "<id>", "prompt": "melodic guitar solo", "instrument": "guitar", "genre": "rock", "duration": 30}'

# 6. Verificar estado
curl http://localhost:8000/api/v1/generation/<generation_id>/status \
  -H "Authorization: Bearer <token>"
```

## 9. Correr os testes

```bash
# Backend
cd backend
pytest -v -m "not integration"   # 152 passed / 3 skipped se incluíres 'integration'

# Frontend
cd frontend
npm run test:unit                # 155 testes unitários (Vitest)
npx playwright install chromium  # uma única vez por máquina
npm run test:e2e                 # 13 testes end-to-end (Playwright)
```

Ver `frontend/README.md` (secção "Testes") e `backend/README.md` (secção
"Testes") para mais detalhe.

## 10. OAuth Google — configuração necessária

1. Criar projeto em [Google Cloud Console](https://console.cloud.google.com/)
2. Ativar "Google OAuth2 API"
3. Criar credenciais OAuth 2.0 (tipo: Web Application)
4. Adicionar URI autorizado: `http://localhost:8000/api/v1/users/auth/google/callback`
5. Copiar Client ID e Client Secret para `docker/.env`

Ver `docs/OAUTH_SETUP.md` para instruções detalhadas.

## 11. Troubleshooting

### "uvicorn is not recognized" (Windows PowerShell)

Confirma que o ambiente virtual está ativo — deves ver `(venv)` no início da linha.

```powershell
venv\Scripts\Activate.ps1
```

### "cannot be loaded because running scripts is disabled" (PowerShell)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Porta 8000 já em uso

```bash
# Linux/Mac
lsof -i :8000 && kill -9 <PID>

# Ou muda a porta
uvicorn main:app --reload --port 8001
```

### PostgreSQL não conecta

```bash
docker compose ps postgres
docker compose logs postgres
docker compose restart postgres
```

### Worker não processa tasks

```bash
# Fila de geração
docker compose logs celery_worker
docker compose exec redis redis-cli llen celery

# Fila de notação
docker compose logs celery_worker_notation
docker compose exec redis redis-cli llen notation
```

### Frontend abre mas pedidos /api/* dão 502/504 (modo Docker)

O nginx do container `frontend` faz proxy para o hostname `backend`. Confirma que
o backend está saudável e, se necessário, reinicia o nginx:

```bash
docker compose ps backend
docker compose restart frontend
```

### CORS error / pedidos não chegam ao backend (modo dev nativo)

Verifica `frontend/vite.config.ts` — o proxy deve apontar para `http://localhost:8000`.

## Referências

- [README Principal](README.md)
- [Project Status](PROJECT_STATUS.md)
- [Frontend README](frontend/README.md)
- [Backend README](backend/README.md)
- [OAuth Setup](docs/OAUTH_SETUP.md)
- [Worker Integration](docs/INTEGRACAO_WORKER.md)
