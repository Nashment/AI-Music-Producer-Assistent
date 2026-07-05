# Project Status

Última atualização: 2026-07-05

## Resumo Executivo

| Área | Estado |
|------|--------|
| Backend API | Funcional |
| Autenticação | Google OAuth + JWT (funcional) |
| Worker Celery — geração | Funcional (fila `celery`) |
| Worker Celery — notação | Funcional (fila `notation`) |
| Domínio / Erros | Implementado (padrão Either) |
| Frontend SPA | Funcional — React 19 + TS, i18n PT/EN, tema escuro/claro |
| Testes | Backend: 152 passed / 3 skipped. Frontend: 155 unitários + 13 e2e, todos a passar. |

## Estado por Área

### Backend API

Implementado:
- FastAPI em `backend/main.py`
- Router principal em `backend/app/api/router.py` com prefixo `/api/v1`
- 4 grupos de endpoints: `users`, `projects`, `audio`, `generation`
- Respostas de erro em RFC 7807 Problem Details (`application/problem+json`)
- Health check: `GET /health`

### Domínio e Erros

Implementado em `backend/app/domain/`:
- `result.py` — tipo `Resultado = Union[Sucesso[T], Falha[E]]` (padrão Either)
- `errors/user_errors.py` — `UtilizadorErro` e subtipos
- `errors/project_errors.py` — `ProjetoErro` e subtipos
- `errors/audio_errors.py` — `AudioErro` e subtipos
- `errors/generation_errors.py` — `GeneracaoErro` e subtipos

Todos os serviços devolvem `Resultado` em vez de lançar exceções. A tradução para
HTTP fica exclusivamente nos endpoints.

### Autenticação

Implementado:
- Google OAuth login + callback em `backend/app/api/endpoints/user.py`
- JWT para rotas protegidas via `get_current_user_id` em `dependencies.py`
- Frontend guarda o JWT em contexto React + `localStorage`

Não implementado como endpoint:
- GitHub OAuth
- Microsoft OAuth

### Serviços

Todos os métodos devolvem `Resultado[XErro, T]`:
- `user_service.py` — gestão de utilizadores + OAuth Google
- `project_service.py` — CRUD de projetos com validação de dono
- `audio_service.py` — upload, análise, ajuste de BPM, corte, separação de faixas
- `generation_service.py` — submissão de gerações, cortes, tablatura, partitura, áudio R2

### Worker e Geração Assíncrona

Implementado em `backend/worker/`:
- `celery_app.py` — configuração Celery com Redis como broker e backend
- `tasks/generation_tasks.py` — pipeline de geração e notação

**Fila `celery` — pipeline de geração (`process_generation_task`):**
1. Muda estado para `processing`
2. Envia pedido à Suno AI
3. Polling de estado até completar
4. Descarrega áudio para `worker/generations/audio/`
5. **Pós-processamento automático:**
   - Analisa BPM e tonalidade do áudio gerado
   - Ajusta BPM se a diferença face ao projeto for > 5 BPM
   - Transpõe tonalidade se não coincidir com o áudio original
6. Atualiza estado para `completed` ou `failed`

**Fila `notation` — tablatura/partitura a partir de upload cru (síncrono):**

`POST /generation/tablature/{audio_id}` e `POST /generation/partitura/{audio_id}`
processam e devolvem o PDF diretamente na resposta (`FileResponse`).

**Fila `notation` — tablatura/partitura a partir de uma geração (assíncrono):**

`POST /generation/{id}/tablature` e `POST /generation/{id}/partitura` são
fire-and-forget: devolvem `202 Accepted` de imediato com `..._status='pending'`,
processam em background, e o cliente obtém o PDF via
`GET /generation/{id}/tablature` / `GET /generation/{id}/partitura` (presigned
URL R2) assim que `..._status='completed'`. O mesmo endpoint POST serve também
para regenerar (idempotente).

### Dados e Persistência

Implementado:
- SQLAlchemy async em `backend/app/data/`
- Modelos: `User`, `Project`, `AudioFile`, `Generation`
- Enums: `OAuthProvider`, `GenerationStatusEnum`
- Tipo `GUID` customizado (`models.py`) — UUID nativo em Postgres, `CHAR(36)`
  nos restantes dialetos (necessário para os testes correrem contra SQLite em
  memória)
- Scripts SQL em `docker/SQL/`
- Gerações e cortes partilham a mesma tabela `generations` — cortes têm `parent_generation_id`

### Audio Utils

Módulos em `backend/worker/audio_utils/`:
- `audio_analyzer.py` — análise completa (BPM, key, duração, sample rate, acordes via Librosa)
- `ajuste_bpm.py` — ajuste de tempo com pyrubberband
- `corte_audio.py` — corte de intervalo em segundos
- `separador_faixas.py` — separação de faixas por instrumento
- `transposicao.py` — transposição de tonalidade
- `audio_to_partitura.py` — exportação de partitura PDF via Music21
- `audio_to_tablature2.py` — pipeline completo MIDI → LilyPond → PDF

### Frontend

Implementado em `frontend/` (React 19 + TypeScript + Vite):

**Páginas:**
- `/` — Home (dashboard)
- `/projects` — listagem, criação e eliminação de projetos
- `/projects/:id` — detalhe do projeto, upload de áudio, painel de geração
- `/projects/:id/audio/:audioId` — player, análise, waveform, árvore de gerações, notação
- `/profile` — perfil, edição de username, eliminação de conta
- `/auth` + `/auth/callback` — login Google OAuth

**Funcionalidades transversais:**
- Tema escuro/claro (toggle no header, persiste em `localStorage`)
- Interface bilingue PT/EN (toggle PT/EN no header, persiste em `localStorage`)
- i18n centralizado em `src/i18n/translations.ts` (sem biblioteca externa)
- Editor de waveform (wavesurfer.js) para corte de áudio gerado
- Player com lazy-load de blob
- Árvore de gerações (geração raiz → cortes filhos)
- Toast de notificações

### Infraestrutura Docker

`docker/docker-compose.yml` define 7 serviços:
- `postgres` — base de dados principal
- `redis` — broker e backend Celery
- `backend` — API FastAPI (porta 8000)
- `celery_worker` — worker fila `celery` (geração Suno)
- `celery_worker_notation` — worker fila `notation` (tablatura + partitura)
- `frontend` — SPA Vite + Nginx (porta 5173)
- `pgadmin` — interface de administração PostgreSQL (porta 5050)

### Testes

**Backend (pytest):** 152 passed, 3 skipped, 0 warnings. Cobertura: os 4
serviços (`user_service`, `project_service`, `audio_service`,
`generation_service`), notação (`test_notation_service.py`,
`test_notation_queries.py`), e 2 testes de integração marcados `@pytest.mark.integration`
que dependem de recursos externos (LilyPond instalado, ficheiro de áudio real)
e que ficam skip por omissão (`pytest -m "not integration"`).

**Frontend:**
- Vitest + Testing Library: 155 testes unitários em 14 ficheiros — reducers
  puros (`audioReducer`, `generationReducer`, `projectReducer`), utils
  (`common.ts`, `auth.ts`), o hook de polling `useAudioGenerations`, a camada
  de serviços de API (`request.ts` + 4 services), `ProtectedRoute` e
  `AuthContext`, e o componente `CutActionPanel`.
- Playwright: 13 testes e2e em 2 specs (eliminação de gerações/cortes, fluxo
  assíncrono de notação) usando *route mocking* — não precisam do backend
  real a correr.

**Não coberto ainda:** endpoints FastAPI (`app/api/endpoints/*.py`), as tasks
Celery em si (`worker/tasks/generation_tasks.py`), a integração Suno, e a
maior parte dos componentes/páginas React fora dos já listados acima
(`WaveformCutter`, `GenerationTree`, páginas de projeto/áudio/perfil, etc.).

## Endpoints Disponíveis

Base: `/api/v1`

### Users
- `GET /users/auth/google/login`
- `GET /users/auth/google/callback?code=...`
- `GET /users/me` *(autenticado)*
- `PUT /users/me` *(autenticado)*
- `DELETE /users/me` *(autenticado)*

### Projects
- `POST /projects` *(autenticado)*
- `GET /projects` *(autenticado)*
- `GET /projects/{project_id}` *(autenticado)*
- `PUT /projects/{project_id}` *(autenticado)*
- `DELETE /projects/{project_id}` *(autenticado)*

### Audio
- `GET /audio/project/{project_id}` *(autenticado)*
- `POST /audio/project/{project_id}/upload` *(autenticado)*
- `GET /audio/analysis/{audio_id}` *(autenticado)*
- `GET /audio/{audio_id}` *(autenticado)*
- `DELETE /audio/{audio_id}` *(autenticado)*
- `POST /audio/{audio_id}/adjust-bpm` *(autenticado)*
- `POST /audio/{audio_id}/cut` *(autenticado)*
- `POST /audio/{audio_id}/separate-tracks` *(autenticado)*

### Generation
- `POST /generation` *(autenticado)*
- `POST /generation/cover` *(autenticado)*
- `POST /generation/tablature/{audio_id}` *(autenticado)* — síncrono
- `POST /generation/partitura/{audio_id}` *(autenticado)* — síncrono
- `GET /generation/by-audio/{audio_id}` *(autenticado)*
- `GET /generation/{id}/status` *(autenticado)*
- `GET /generation/{id}` *(autenticado)*
- `GET /generation/{id}/audio` *(autenticado)* — presigned URL R2
- `GET /generation/{id}/cuts` *(autenticado)*
- `POST /generation/{id}/cut` *(autenticado)*
- `POST /generation/{id}/partitura` *(autenticado)* — assíncrono (202)
- `GET /generation/{id}/partitura` *(autenticado)* — presigned URL R2
- `POST /generation/{id}/tablature` *(autenticado)* — assíncrono (202)
- `GET /generation/{id}/tablature` *(autenticado)* — presigned URL R2
- `DELETE /generation/{id}` *(autenticado)*

## Próximo Trabalho Recomendado

1. Cobrir a camada de endpoints FastAPI e as tasks Celery com testes (hoje só
   os serviços e a lógica de frontend estão cobertos)
2. Adicionar refresh token no fluxo OAuth
3. Documentar variáveis de ambiente necessárias num `.env.example`
4. Adicionar CI/CD (GitHub Actions) a correr as duas suites de testes
