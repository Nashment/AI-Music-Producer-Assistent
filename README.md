# AI Music Producer Assistant

Status atual: backend funcional com FastAPI + Celery, frontend ainda em scaffolding.

## Visão Geral

Plataforma para apoio a produção musical com IA:
- Upload e análise de áudio base (BPM, key, assinatura temporal)
- Geração assíncrona com Suno
- Conversão opcional para partitura e tablatura
- Gestão por projetos e utilizador autenticado

## Estado Real do Projeto

### Backend
- Implementado e executável com FastAPI
- Rotas de users, projects, audio e generation
- Autenticação JWT com login OAuth Google
- Persistência com PostgreSQL

### Worker
- Celery com Redis
- Task principal de geração em `worker.tasks.generation_tasks`
- Pipeline de polling Suno e atualização de status na base de dados

### Frontend
- Existe estrutura de pastas em `frontend/src/`
- `frontend/src/main.tsx` está vazio
- Não existe aplicação React funcional ainda

### Testes
- Pasta `backend/tests/` existe
- Ficheiros de testes são maioritariamente placeholders (`TODO`/`pass`)

## Estrutura (Resumo)

```text
projeto/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/
│   │   ├── core/
│   │   ├── data/
│   │   ├── domain/dtos/endpoints/
│   │   └── services/
│   ├── worker/
│   │   ├── ai_models/
│   │   ├── audio_utils/
│   │   ├── tasks/
│   │   └── celery_app.py
│   ├── tests/
│   └── main.py
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── SQL/
├── docs/
├── frontend/
└── README.md
```

## Arranque Rápido

### Opção 1: Docker Compose (recomendado)

```bash
cd docker
docker compose up -d
```

Serviços iniciados:
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- pgAdmin: `http://localhost:5050`

### Opção 2: Backend local (sem container do backend)

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

### Worker Celery (local)

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

Opcional (Flower):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

## Endpoints Reais da API

Prefixo base: `/api/v1`

### Users
- `GET /users/auth/google/login`
- `GET /users/auth/google/callback?code=...`
- `GET /users/me`
- `PUT /users/me`
- `DELETE /users/me`

### Projects
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PUT /projects/{project_id}`
- `DELETE /projects/{project_id}`

### Audio
- `GET /audio/project/{project_id}`
- `POST /audio/project/{project_id}/upload`
- `GET /audio/analysis/{audio_id}`
- `GET /audio/{audio_id}`
- `DELETE /audio/{audio_id}`
- `POST /audio/{audio_id}/adjust-bpm`
- `POST /audio/{audio_id}/cut`
- `POST /audio/{audio_id}/separate-tracks`

### Generation
- `POST /generation`
- `POST /generation/cover`
- `POST /generation/tablature/{audio_id}`
- `POST /generation/partitura/{audio_id}`
- `GET /generation/{generation_id}/status`
- `GET /generation/{generation_id}`
- `DELETE /generation/{generation_id}`

## Notas Importantes

- A autenticação implementada no código é Google OAuth.
- Existem variáveis para outros providers no `.env`, mas os endpoints não estão implementados.
- O fluxo de geração foi movido para Celery (não usa `BackgroundTasks` da API para o pipeline principal).

## Documentação Detalhada

Consultar:
- `PROJECT_STATUS.md`
- `QUICK_START.md`
- `POSTMAN_QUERIES.md`
- `docs/README.md`