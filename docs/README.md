# Documentação do Projeto

Este diretório contém documentação alinhada com o estado real do código no repositório.

## Estado Atual (Código)

- Backend FastAPI: funcional
- Worker Celery: funcional
- Frontend: apenas scaffolding
- Testes: maioritariamente placeholders

## Endpoints Reais

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

## Ficheiros desta pasta

- `ESTRUTURA_CRIADA.md`: estrutura de diretórios e componentes reais
- `INTEGRACAO_WORKER.md`: fluxo Celery/Suno implementado
- `OAUTH_IMPLEMENTATION.md`: estado da autenticação no código
- `OAUTH_SETUP.md`: configuração prática para Google OAuth
- `FRONTEND_STATUS.md`: estado real do frontend
