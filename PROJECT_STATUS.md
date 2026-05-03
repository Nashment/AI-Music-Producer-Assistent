# Project Status

Última atualização: 2026-05-01

## Resumo Executivo

| Área | Estado |
|------|--------|
| Backend API | Funcional |
| Autenticação | Google OAuth + JWT (funcional) |
| Worker / Celery | Funcional |
| Domínio / Erros | Implementado (padrão Either) |
| Frontend | Apenas scaffolding |
| Testes | Estrutura criada, sem cobertura real |

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

Não implementado como endpoint (apenas variáveis de ambiente referenciadas):
- GitHub OAuth
- Microsoft OAuth

### Serviços

Todos os métodos devolvem `Resultado[XErro, T]`:
- `user_service.py` — gestão de utilizadores + OAuth Google
- `project_service.py` — CRUD de projetos com validação de dono
- `audio_service.py` — upload, análise, ajuste de BPM, corte, separação de faixas
- `generation_service.py` — submissão de gerações + tablatura/partitura

### Worker e Geração Assíncrona

Implementado em `backend/worker/`:
- `celery_app.py` — configuração Celery com Redis como broker e backend
- `tasks/generation_tasks.py` — pipeline principal

Pipeline de geração (`process_generation_task`):
1. Muda estado para `processing`
2. Envia pedido à Suno AI
3. Polling de estado até completar
4. Descarrega áudio para `worker/generations/audio/`
5. **Pós-processamento automático:**
   - Analisa BPM e tonalidade do áudio gerado
   - Ajusta BPM se a diferença face ao projeto for > 5 BPM
   - Transpõe tonalidade se não coincidir com o áudio original
6. Atualiza estado para `completed` ou `failed`

Pipeline de tablatura (`process_tablature_task`):
1. Extrai MIDI do áudio (via `audio_to_tablature2`)
2. Converte MIDI para LilyPond (`.ly`)
3. Aplica estilo de tablatura (dedilhado inteligente ou standard)
4. Compila para PDF via LilyPond (com fallback se compilação falhar)
5. Guarda em `worker/generations/tablatura/`

Pipeline de partitura (`process_partitura_task`):
1. Exporta PDF via Music21 (`audio_to_partitura`)
2. Guarda em `worker/generations/partitura/`

### Dados e Persistência

Implementado:
- SQLAlchemy async em `backend/app/data/`
- Modelos: `User`, `Project`, `AudioFile`, `Generation`
- Enums: `OAuthProvider`, `GenerationStatusEnum`
- Scripts SQL em `docker/SQL/`

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

Situação atual:
- Pastas existentes em `frontend/src/`
- `frontend/src/main.tsx` vazio
- Sem componentes, páginas ou integração API funcional

### Testes

Situação atual:
- Ficheiros de teste existem em `backend/tests/`
- A maioria dos testes são `pass` (placeholders)
- `conftest.py` tem imports que requerem execução a partir da raiz do projeto
- Sem cobertura real da lógica de serviços ou endpoints

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
- `POST /generation/tablature/{audio_id}` *(autenticado)*
- `POST /generation/partitura/{audio_id}` *(autenticado)*
- `GET /generation/{generation_id}/status` *(autenticado)*
- `GET /generation/{generation_id}` *(autenticado)*
- `DELETE /generation/{generation_id}` *(autenticado)*

## Infraestrutura Docker

`docker/docker-compose.yml` define:
- `postgres` — base de dados principal
- `redis` — broker e backend Celery
- `backend` — API FastAPI
- `celery_worker` — worker de geração
- `pgadmin` — interface de administração PostgreSQL

## Próximo Trabalho Recomendado

1. Implementar testes reais para serviços e endpoints
2. Implementar frontend (React/Vite + integração API)
3. Adicionar refresh token no fluxo OAuth
4. Documentar variáveis de ambiente necessárias num `.env.example`
