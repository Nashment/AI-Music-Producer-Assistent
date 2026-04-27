# Project Status

Última atualização: 2026-04-27

## Resumo Executivo

- Backend: funcional e com rotas principais implementadas
- Worker/Celery: funcional para pipeline de geração
- Frontend: apenas estrutura inicial de pastas
- Testes: estrutura criada, implementação incompleta

## Estado por Área

### Backend API
Status: implementado

Implementado no código:
- FastAPI em `backend/main.py`
- Router principal em `backend/app/api/router.py`
- Endpoints:
	- users (`backend/app/api/endpoints/user.py`)
	- projects (`backend/app/api/endpoints/projects.py`)
	- audio (`backend/app/api/endpoints/audio.py`)
	- generation (`backend/app/api/endpoints/generation.py`)

### Autenticação
Status: parcialmente implementada

Implementado no código:
- OAuth Google login + callback
- JWT para rotas protegidas

Não implementado como endpoint:
- GitHub callback/login
- Microsoft callback/login

### Worker e Geração Assíncrona
Status: implementado

Implementado no código:
- Celery app em `backend/worker/celery_app.py`
- Tasks em `backend/worker/tasks/generation_tasks.py`
- Orquestração de submissão em `backend/app/services/generation_service.py`

### Dados e Persistência
Status: implementado

Implementado no código:
- SQLAlchemy models em `backend/app/data/models.py`
- Sessão async e health check em `backend/app/data/database.py`
- Scripts SQL em `docker/SQL/`

### Frontend
Status: não implementado

Situação atual no repositório:
- Pastas existentes em `frontend/src/`
- `frontend/src/main.tsx` vazio
- Sem componentes, páginas ou integração API funcional

### Testes
Status: incompleto

Situação atual no repositório:
- Ficheiros de teste existem em `backend/tests/`
- Grande parte com `TODO` e `pass`
- Não representam cobertura real da aplicação

## Endpoints Disponíveis Hoje

Base: `/api/v1`

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

## Infraestrutura Docker

`docker/docker-compose.yml` define:
- `postgres`
- `redis`
- `backend`
- `celery_worker`
- `pgadmin`

## Próximo Trabalho Recomendado

1. Implementar frontend real (React/Vite + integração API)
2. Completar testes de services/endpoints
3. Consolidar documentação OAuth para não sugerir providers sem endpoint