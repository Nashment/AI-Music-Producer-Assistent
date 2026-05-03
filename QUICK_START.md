# Quick Start

Comandos reais para levantar o projeto no estado atual do código.

## 1. Pré-requisitos

- Docker + Docker Compose
- Python 3.11+ (para execução local)
- Ficheiro `.env` configurado (ver secção Variáveis de Ambiente)

## 2. Levantar stack completa com Docker

```bash
cd docker
docker compose up -d
docker compose ps
```

Serviços esperados em estado `Up`:
- `postgres`
- `redis`
- `backend`
- `celery_worker`
- `pgadmin`

Verificar:
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- pgAdmin: `http://localhost:5050`

## 3. Backend local (sem container do backend)

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

> O servidor fica disponível em `http://localhost:8000`.

## 4. Worker Celery local

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

Flower (painel de monitorização, opcional):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

> O Flower fica disponível em `http://localhost:5555`.

## 5. Parar serviços

```bash
cd docker
docker compose down
```

## 6. Variáveis de Ambiente

O backend requer as seguintes variáveis (normalmente em `.env` na raiz do projeto
ou injetadas pelo docker-compose):

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `JWT_SECRET_KEY` | Sim | Chave secreta para assinar JWTs |
| `JWT_ALGORITHM` | Não (default: `HS256`) | Algoritmo JWT |
| `JWT_EXPIRATION_HOURS` | Não (default: `24`) | Validade do token em horas |
| `GOOGLE_CLIENT_ID` | Sim (para OAuth) | Client ID do Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Sim (para OAuth) | Client Secret do Google OAuth |
| `GOOGLE_REDIRECT_URI` | Sim (para OAuth) | URI de callback registada no Google |
| `DATABASE_URL` | Sim | URL PostgreSQL async (postgresql+asyncpg://...) |
| `REDIS_URL` | Não (default: `redis://localhost:6379/0`) | URL do Redis |
| `AUDIO_UPLOAD_DIR` | Não | Diretório de uploads de áudio |
| `GENERATIONS_AUDIO_DIR` | Não | Diretório de output de áudio gerado |
| `GENERATIONS_PARTITURA_DIR` | Não | Diretório de output de partituras |
| `GENERATIONS_TABLATURA_DIR` | Não | Diretório de output de tablaturas |

## 7. Fluxo de teste rápido

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

## 8. OAuth Google — configuração necessária

1. Criar projeto em [Google Cloud Console](https://console.cloud.google.com/)
2. Ativar "Google OAuth2 API"
3. Criar credenciais OAuth 2.0 (tipo: Web Application)
4. Adicionar URI autorizado: `http://localhost:8000/api/v1/users/auth/google/callback`
5. Copiar Client ID e Client Secret para o `.env`

Ver `docs/OAUTH_SETUP.md` para instruções detalhadas.

## 9. Troubleshooting

### "uvicorn is not recognized" (Windows PowerShell)

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

Confirma que vês `(venv)` no início da linha.

### "cannot be loaded because running scripts is disabled" (PowerShell)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Porta 8000 já em uso

```bash
# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Ou muda a porta
uvicorn main:app --reload --port 8001
```

### PostgreSQL não conecta

```bash
docker compose ps postgres
docker compose logs postgres
docker compose restart postgres
```

### Redis não conecta

```bash
docker compose ps redis
docker compose logs redis
```

### Worker não processa tasks

```bash
# Verificar se o worker está a correr
docker compose logs celery_worker

# Verificar fila Redis
docker compose exec redis redis-cli llen celery
```

## Referências

- [README Principal](README.md)
- [Backend Documentation](backend/README.md)
- [Project Status](PROJECT_STATUS.md)
- [OAuth Setup](docs/OAUTH_SETUP.md)
- [Worker Integration](docs/INTEGRACAO_WORKER.md)
- [Postman Queries](POSTMAN_QUERIES.md)
