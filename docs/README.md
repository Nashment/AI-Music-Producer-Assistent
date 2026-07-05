# Documentação do Projeto

Este diretório contém documentação técnica detalhada sobre áreas específicas do projeto.

## Estado Atual

- Backend FastAPI: funcional
- Workers Celery: funcionais (filas `celery` e `notation`)
- Frontend React 19 + TS: funcional (tema escuro/claro, i18n PT/EN)
- Testes: backend 152 passed / 3 skipped (pytest); frontend 155 unitários + 13 e2e (Vitest + Playwright), todos a passar

## Ficheiros

| Ficheiro | Conteúdo |
|----------|----------|
| `INTEGRACAO_WORKER.md` | Filas Celery, pipelines de geração/tablatura/partitura, comandos |
| `OAUTH_IMPLEMENTATION.md` | O que está implementado no código OAuth (fluxo, endpoints, persistência) |
| `OAUTH_SETUP.md` | Configuração prática Google OAuth (variáveis, fluxo de teste manual) |

## Endpoints Reais

Base: `/api/v1`

### Users
- `GET /users/auth/google/login`
- `GET /users/auth/google/callback?code=...`
- `GET /users/me` / `PUT /users/me` / `DELETE /users/me`

### Projects
- `POST /projects` / `GET /projects`
- `GET /projects/{id}` / `PUT /projects/{id}` / `DELETE /projects/{id}`

### Audio
- `GET /audio/project/{project_id}`
- `POST /audio/project/{project_id}/upload`
- `GET /audio/analysis/{audio_id}` / `GET /audio/{audio_id}` / `DELETE /audio/{audio_id}`
- `POST /audio/{audio_id}/adjust-bpm` / `cut` / `separate-tracks`

### Generation
- `POST /generation` / `POST /generation/cover`
- `POST /generation/tablature/{audio_id}` / `POST /generation/partitura/{audio_id}` — síncronos, devolvem o PDF
- `GET /generation/by-audio/{audio_id}`
- `GET /generation/{id}` / `GET /generation/{id}/status` / `GET /generation/{id}/audio`
- `GET /generation/{id}/cuts` / `POST /generation/{id}/cut`
- `POST /generation/{id}/partitura` / `POST /generation/{id}/tablature` — assíncronos (202), regeneração idempotente
- `GET /generation/{id}/partitura` / `GET /generation/{id}/tablature` — presigned URL R2 do resultado
- `DELETE /generation/{id}`

## Outros documentos do projeto

- [README principal](../README.md) — visão geral, estrutura completa, todas as dependências
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) — estado detalhado por área
- [QUICK_START.md](../QUICK_START.md) — comandos de arranque e troubleshooting
- [backend/README.md](../backend/README.md) — guia do backend (endpoints, testes)
- [frontend/README.md](../frontend/README.md) — guia completo do frontend (arranque, estrutura, testes)
