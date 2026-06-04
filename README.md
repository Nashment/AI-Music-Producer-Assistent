# AI Music Producer Assistant

Plataforma full-stack para produção musical com IA — backend FastAPI + Celery, frontend React 19 + TypeScript + Vite.

## Visão Geral

- Upload e análise de áudio base (BPM, tonalidade, assinatura temporal, acordes)
- Geração assíncrona via Suno AI (música original e covers)
- Pós-processamento automático do áudio gerado (ajuste de BPM, transposição de tonalidade)
- Conversão para partitura (PDF via Music21) e tablatura (PDF via LilyPond)
- Gestão por projetos e utilizador autenticado (Google OAuth + JWT)
- Interface web completa com tema escuro/claro e i18n PT/EN

## Arquitetura

```
React SPA (Vite)  ←→  API (FastAPI)  →  Services (lógica de negócio)  →  Data (SQLAlchemy)
                                                  ↓
                                         Worker (Celery + Redis)
                                                  ↓
                                         Suno AI + Audio Utils
```

Os serviços comunicam sucesso/falha através de um tipo `Resultado[E, T]` (padrão Either),
nunca lançando exceções para a camada de endpoint. A tradução para HTTP Problem Details
(RFC 7807) é feita exclusivamente nos endpoints.

## Estado do Projeto

| Componente               | Estado                                                  |
|--------------------------|---------------------------------------------------------|
| Backend API              | Funcional                                               |
| Autenticação             | Google OAuth + JWT (funcional)                          |
| Worker Celery (geração)  | Funcional — fila `celery` (Suno + pós-processamento)    |
| Worker Celery (notação)  | Funcional — fila `notation` (tablatura + partitura)     |
| Frontend SPA             | Funcional — React 19 + TS, tema escuro/claro, i18n PT/EN |
| Testes                   | Estrutura criada, maioritariamente `pass`               |

## Estrutura

```text
projeto/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   ├── router.py
│   │   │   └── endpoints/
│   │   │       ├── user.py
│   │   │       ├── projects.py
│   │   │       ├── audio.py
│   │   │       ├── generation.py
│   │   │       └── suno_webhook.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── error_handlers.py
│   │   │   └── exceptions.py
│   │   ├── data/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── queries.py
│   │   │   └── oauth_queries.py
│   │   ├── domain/
│   │   │   ├── result.py              ← Sucesso / Falha / Resultado
│   │   │   ├── errors/
│   │   │   │   ├── user_errors.py
│   │   │   │   ├── project_errors.py
│   │   │   │   ├── audio_errors.py
│   │   │   │   └── generation_errors.py
│   │   │   └── dtos/endpoints/
│   │   │       ├── audio.py
│   │   │       ├── generation.py
│   │   │       ├── projects.py
│   │   │       └── user.py
│   │   └── services/
│   │       ├── user_service.py
│   │       ├── project_service.py
│   │       ├── audio_service.py
│   │       ├── generation_service.py
│   │       └── storage_service.py
│   ├── worker/
│   │   ├── celery_app.py
│   │   ├── tasks/
│   │   │   └── generation_tasks.py
│   │   ├── ai_models/
│   │   │   ├── suno_audio_generator.py
│   │   │   └── get_suno_audio.py
│   │   └── audio_utils/
│   │       ├── audio_analyzer.py
│   │       ├── ajuste_bpm.py
│   │       ├── corte_audio.py
│   │       ├── separador_faixas.py
│   │       ├── transposicao.py
│   │       ├── audio_to_partitura.py
│   │       ├── audio_to_tablature.py
│   │       └── audio_to_tablature2.py
│   ├── tests/
│   └── main.py
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile              ← imagem leve (API, sem ML)
│   ├── Dockerfile.worker       ← imagem pesada (ML/audio)
│   ├── requirements.txt
│   ├── requirements-api.txt
│   ├── requirements-worker.txt
│   └── SQL/
├── frontend/
│   ├── Dockerfile              ← build Vite → Nginx
│   ├── package.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── context/
│   │   │   ├── AuthContext.tsx
│   │   │   ├── ThemeContext.tsx
│   │   │   └── LanguageContext.tsx
│   │   ├── hooks/
│   │   │   ├── audio/
│   │   │   │   ├── audioReducer.ts
│   │   │   │   ├── useAudioActions.ts
│   │   │   │   └── useAudios.ts
│   │   │   ├── auth/
│   │   │   │   └── useAuth.ts
│   │   │   ├── generation/
│   │   │   │   ├── generationReducer.ts
│   │   │   │   ├── useAudioGenerations.ts
│   │   │   │   ├── useGeneration.ts
│   │   │   │   ├── useGenerationActions.ts
│   │   │   │   └── useGenerationSubscription.ts
│   │   │   ├── language/
│   │   │   │   └── useLanguage.ts
│   │   │   ├── project/
│   │   │   │   ├── projectReducer.ts
│   │   │   │   ├── useProject.ts
│   │   │   │   ├── useProjectActions.ts
│   │   │   │   └── useProjects.ts
│   │   │   └── theme/
│   │   │       └── useTheme.ts
│   │   ├── i18n/
│   │   │   └── translations.ts   ← strings PT + EN por secção
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── authentication.tsx
│   │   │   ├── oauthCallback.tsx
│   │   │   ├── logout.tsx
│   │   │   ├── projects.tsx
│   │   │   ├── projectCreation.tsx
│   │   │   ├── projectDetail.tsx
│   │   │   ├── audioDetail.tsx
│   │   │   ├── generationCreation.tsx
│   │   │   └── profile.tsx
│   │   ├── components/
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── Layout/
│   │   │   │   ├── AppHeader.tsx
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── ConfirmDialog.tsx
│   │   │   │   ├── EmptyState.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── PageHeader.tsx
│   │   │   │   ├── Spinner.tsx
│   │   │   │   └── Toast.tsx
│   │   │   ├── Audio/
│   │   │   │   ├── AudioCard.tsx
│   │   │   │   ├── AudioDetails.tsx
│   │   │   │   ├── AudioList.tsx
│   │   │   │   ├── AudioPlayer.tsx
│   │   │   │   ├── AudioToolsPanel.tsx
│   │   │   │   └── AudioUpload.tsx
│   │   │   ├── Generation/
│   │   │   │   ├── CutActionPanel.tsx
│   │   │   │   ├── GenerateMusicPanel.tsx
│   │   │   │   ├── GenerationCard.tsx
│   │   │   │   ├── GenerationForm.tsx
│   │   │   │   ├── GenerationList.tsx
│   │   │   │   ├── GenerationTree.tsx
│   │   │   │   └── WaveformCutter.tsx
│   │   │   ├── Home/
│   │   │   │   └── HomeElements.tsx
│   │   │   └── Project/
│   │   │       ├── ProjectCard.tsx
│   │   │       ├── ProjectError.tsx
│   │   │       ├── ProjectForm.tsx
│   │   │       ├── ProjectList.tsx
│   │   │       └── ProjectLoading.tsx
│   │   ├── services/
│   │   │   ├── request.ts
│   │   │   ├── audio/
│   │   │   │   ├── audioService.ts
│   │   │   │   └── audioResponseTypes.ts
│   │   │   ├── generation/
│   │   │   │   ├── generationService.ts
│   │   │   │   └── generationResponseTypes.ts
│   │   │   ├── project/
│   │   │   │   ├── projectService.ts
│   │   │   │   └── projectResponseTypes.ts
│   │   │   └── user/
│   │   │       ├── userService.ts
│   │   │       └── userResponseTypes.ts
│   │   └── utils/
│   │       ├── auth.ts
│   │       └── common.ts
│   └── style/
│       ├── style.css            ← design tokens (cores, spacing, tipografia)
│       ├── layout.css
│       ├── authentication.css
│       ├── audio.css
│       ├── generation.css
│       ├── profile.css
│       ├── projectDetail.css
│       ├── projects.css
│       └── HomePage.css
├── docs/
└── README.md
```

## Arranque Rápido

### Docker Compose (recomendado)

```bash
cd docker
docker compose up -d
```

Serviços iniciados:

| Serviço                  | URL / Porta            | Descrição                                      |
|--------------------------|------------------------|------------------------------------------------|
| Frontend                 | `http://localhost:5173` | SPA React (build Vite servido por Nginx)       |
| Backend API              | `http://localhost:8000` | FastAPI                                        |
| Swagger UI               | `http://localhost:8000/docs` | Documentação interativa                  |
| ReDoc                    | `http://localhost:8000/redoc` | Documentação alternativa               |
| PostgreSQL               | `localhost:5432`        | Base de dados                                  |
| Redis                    | `localhost:6379`        | Broker + result backend Celery                 |
| pgAdmin                  | `http://localhost:5050` | Gestão da BD (apenas dev)                     |

> A porta do frontend pode ser alterada com `FRONTEND_PORT` no `.env`.

### Backend local (sem container do backend)

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

### Workers Celery locais

```bash
# Fila de geração Suno + pós-processamento
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=celery --loglevel=info

# Fila de notação (tablatura + partitura) — janela separada
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=notation --loglevel=info
```

Flower (painel de monitorização):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

### Frontend local (modo desenvolvimento)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Build de produção:

```bash
npm run build    # output em dist/
```

## Filas Celery

Existem dois workers com filas distintas para evitar que tarefas rápidas fiquem
bloqueadas atrás de tarefas longas:

| Fila        | Worker                    | Tarefas                                             | Duração típica |
|-------------|---------------------------|-----------------------------------------------------|----------------|
| `celery`    | `celery_worker`           | Geração Suno (original + cover), pós-processamento  | 86–200 s       |
| `notation`  | `celery_worker_notation`  | Tablatura (LilyPond), partitura (Music21)            | 4–9 s          |

## Endpoints da API

Prefixo base: `/api/v1`

### Users (`/users`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/users/auth/google/login` | Devolve URL de autorização Google |
| GET | `/users/auth/google/callback?code=...` | Troca code por JWT |
| GET | `/users/me` | Perfil do utilizador autenticado |
| PUT | `/users/me` | Atualiza username |
| DELETE | `/users/me` | Elimina conta |

### Projects (`/projects`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/projects` | Cria projeto |
| GET | `/projects` | Lista projetos do utilizador |
| GET | `/projects/{project_id}` | Detalhe de um projeto |
| PUT | `/projects/{project_id}` | Atualiza projeto |
| DELETE | `/projects/{project_id}` | Elimina projeto |

### Audio (`/audio`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/audio/project/{project_id}` | Lista áudios de um projeto |
| POST | `/audio/project/{project_id}/upload` | Upload + análise automática |
| GET | `/audio/analysis/{audio_id}` | Metadados de análise (BPM, tonalidade, etc.) |
| GET | `/audio/{audio_id}` | Download do ficheiro de áudio |
| DELETE | `/audio/{audio_id}` | Elimina áudio |
| POST | `/audio/{audio_id}/adjust-bpm` | Ajusta BPM |
| POST | `/audio/{audio_id}/cut` | Corta intervalo de tempo |
| POST | `/audio/{audio_id}/separate-tracks` | Separa faixa de instrumento |

### Generation (`/generation`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/generation` | Submete geração de música original (202 Accepted) |
| POST | `/generation/cover` | Submete geração de cover (202 Accepted) |
| POST | `/generation/tablature/{audio_id}` | Gera tablatura PDF a partir de upload |
| POST | `/generation/partitura/{audio_id}` | Gera partitura PDF a partir de upload |
| GET | `/generation/by-audio/{audio_id}` | Lista gerações associadas a um áudio |
| GET | `/generation/{id}/status` | Estado da geração (polling) |
| GET | `/generation/{id}` | Resultado completo da geração |
| GET | `/generation/{id}/audio` | Presigned URL R2 para o áudio gerado |
| GET | `/generation/{id}/cuts` | Lista cortes de uma geração |
| POST | `/generation/{id}/cut` | Cria corte (início/fim em segundos) — 201 Created |
| POST | `/generation/{id}/partitura` | Gera partitura PDF a partir de geração |
| POST | `/generation/{id}/tablature` | Gera tablatura PDF a partir de geração |
| DELETE | `/generation/{id}` | Elimina geração — 204 No Content |

## Frontend — Páginas e Funcionalidades

| Página | Rota | Descrição |
|--------|------|-----------|
| Home | `/` | Dashboard de entrada |
| Projetos | `/projects` | Listagem, criação e eliminação de projetos |
| Detalhe do projeto | `/projects/:id` | Áudios do projeto, upload, painel de geração |
| Detalhe do áudio | `/projects/:id/audio/:audioId` | Player, análise, geração de notação, árvore de gerações |
| Perfil | `/profile` | Dados do utilizador, edição de username, eliminação de conta |
| Autenticação | `/auth` | Login Google OAuth |

Funcionalidades transversais:
- Tema escuro/claro (persiste em `localStorage`)
- Interface disponível em Português e Inglês (toggle PT/EN, persiste em `localStorage`)
- Editor de waveform (wavesurfer.js) para corte de áudio gerado
- Player com lazy-load de blob (não descarrega o áudio até o utilizador pedir)
- Árvore de gerações (geração pai → cortes filhos)
- Toaster de notificações

## Autenticação

Todas as rotas exceto `/users/auth/google/login` e `/users/auth/google/callback` requerem:

```
Authorization: Bearer <jwt>
```

O JWT é obtido no callback do Google OAuth e guardado pelo frontend em memória (contexto React).

## Erros HTTP

Os endpoints devolvem erros no formato RFC 7807 (Problem Details):

```json
{
  "type": "/errors/recurso-nao-encontrado",
  "title": "Recurso Nao Encontrado",
  "status": 404,
  "detail": "O projeto pedido nao foi encontrado.",
  "instance": "/api/v1/projects/abc-123"
}
```

`Content-Type: application/problem+json`

## Principais Dependências

### Backend

| Pacote | Uso |
|--------|-----|
| FastAPI + Uvicorn | Framework API + servidor ASGI |
| SQLAlchemy (async) + asyncpg | ORM + driver PostgreSQL |
| Celery + Redis | Fila de tarefas assíncronas |
| Music21 | Geração de partituras (PDF) |
| LilyPond | Geração de tablaturas (PDF) |
| basic-pitch (Spotify) | Transcrição áudio → MIDI |
| pydub / librosa | Processamento de áudio |

### Frontend

| Pacote | Versão | Uso |
|--------|--------|-----|
| React | 19.2 | Framework UI |
| react-router-dom | 7.9.5 | Routing SPA |
| wavesurfer.js | 7.10.1 | Editor de waveform |
| TypeScript | 5.9.3 | Tipagem estática |
| Vite | 7.2.2 | Build tool + dev server |

## Documentação Adicional

- `PROJECT_STATUS.md` — estado atual por área
- `QUICK_START.md` — guia de arranque com troubleshooting
- `POSTMAN_QUERIES.md` — exemplos de pedidos prontos a usar
- `docs/ESTRUTURA_CRIADA.md` — estrutura de ficheiros detalhada
- `docs/INTEGRACAO_WORKER.md` — pipeline Celery/Suno
- `docs/OAUTH_SETUP.md` — configuração do Google OAuth
