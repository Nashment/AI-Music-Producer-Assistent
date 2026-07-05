# Backend — AI Music Producer Assistant

FastAPI + Celery + PostgreSQL + Redis.

## Estrutura

```text
backend/
├── main.py
├── app/
│   ├── api/
│   │   ├── dependencies.py       ← get_db, get_current_user_id
│   │   ├── router.py             ← prefixo /api/v1
│   │   └── endpoints/
│   │       ├── user.py
│   │       ├── projects.py
│   │       ├── audio.py
│   │       └── generation.py
│   ├── core/
│   ├── data/
│   │   ├── database.py
│   │   ├── models.py             ← User, Project, AudioFile, Generation
│   │   ├── queries.py
│   │   └── oauth_queries.py
│   ├── domain/
│   │   ├── result.py             ← Sucesso / Falha / Resultado (padrão Either)
│   │   ├── errors/
│   │   └── dtos/endpoints/
│   └── services/
│       ├── user_service.py
│       ├── project_service.py
│       ├── audio_service.py
│       └── generation_service.py
├── worker/
│   ├── celery_app.py
│   ├── tasks/generation_tasks.py
│   ├── ai_models/suno_audio_generator.py
│   └── audio_utils/
│       ├── audio_analyzer.py
│       ├── ajuste_bpm.py
│       ├── corte_audio.py
│       ├── separador_faixas.py
│       ├── transposicao.py
│       ├── audio_to_partitura.py
│       └── audio_to_tablature2.py
├── pytest.ini
└── tests/
```

## Executar localmente

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1          # Windows
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Workers Celery locais

```bash
# Fila de geração (Suno + pós-processamento)
celery -A worker.celery_app:celery_app worker --pool=solo --queues=celery --loglevel=info

# Fila de notação (tablatura + partitura) — janela separada
celery -A worker.celery_app:celery_app worker --pool=solo --queues=notation --loglevel=info
```

Flower (monitorização):

```bash
celery -A worker.celery_app:celery_app flower
```

## Endpoints

Base: `/api/v1`

### Users
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/users/auth/google/login` | URL de autorização Google |
| GET | `/users/auth/google/callback?code=...` | Troca code por JWT |
| GET | `/users/me` | Perfil do utilizador |
| PUT | `/users/me` | Atualiza username |
| DELETE | `/users/me` | Elimina conta |

### Projects
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/projects` | Cria projeto |
| GET | `/projects` | Lista projetos |
| GET | `/projects/{id}` | Detalhe |
| PUT | `/projects/{id}` | Atualiza |
| DELETE | `/projects/{id}` | Elimina |

### Audio
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/audio/project/{project_id}` | Lista áudios do projeto |
| POST | `/audio/project/{project_id}/upload` | Upload + análise |
| GET | `/audio/analysis/{audio_id}` | Metadados de análise |
| GET | `/audio/{audio_id}` | Download do ficheiro |
| DELETE | `/audio/{audio_id}` | Elimina |
| POST | `/audio/{audio_id}/adjust-bpm` | Ajusta BPM |
| POST | `/audio/{audio_id}/cut` | Corta intervalo |
| POST | `/audio/{audio_id}/separate-tracks` | Separa instrumento |

### Generation
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/generation` | Geração original (202) |
| POST | `/generation/cover` | Cover (202) |
| POST | `/generation/tablature/{audio_id}` | Tablatura PDF de upload — síncrono, devolve o PDF |
| POST | `/generation/partitura/{audio_id}` | Partitura PDF de upload — síncrono, devolve o PDF |
| GET | `/generation/by-audio/{audio_id}` | Gerações de um áudio |
| GET | `/generation/{id}/status` | Estado da geração |
| GET | `/generation/{id}` | Resultado completo |
| GET | `/generation/{id}/audio` | Presigned URL R2 |
| GET | `/generation/{id}/cuts` | Cortes de uma geração |
| POST | `/generation/{id}/cut` | Criar corte (201) |
| POST | `/generation/{id}/partitura` | Enfileira partitura em background (202, idempotente/regera) |
| GET | `/generation/{id}/partitura` | Presigned URL R2 da partitura (409 se não `completed`) |
| POST | `/generation/{id}/tablature` | Enfileira tablatura em background (202, idempotente/regera) |
| GET | `/generation/{id}/tablature` | Presigned URL R2 da tablatura (409 se não `completed`) |
| DELETE | `/generation/{id}` | Elimina (204) |

## Autenticação

JWT obrigatório em todas as rotas exceto login/callback:

```
Authorization: Bearer <token>
```

## Padrão de erros

RFC 7807 — `Content-Type: application/problem+json`:

```json
{
  "type": "/errors/recurso-nao-encontrado",
  "title": "Recurso Nao Encontrado",
  "status": 404,
  "detail": "O projeto pedido nao foi encontrado.",
  "instance": "/api/v1/projects/abc-123"
}
```

## Testes

```bash
cd backend
pytest -v                       # suite completa
pytest -v -m "not integration"  # sem os 2 testes que precisam de LilyPond real
```

Estado: **152 passed, 3 skipped, 0 warnings** (os skips são testes marcados
`@pytest.mark.integration` que dependem de recursos externos — binário do
LilyPond instalado e um ficheiro de áudio real — não presentes num ambiente
de teste limpo).

Cobertura: os 4 serviços (`user_service`, `project_service`, `audio_service`,
`generation_service`) e a camada de notação (`test_notation_service.py`,
`test_notation_queries.py`). Ainda não há testes para os endpoints FastAPI em
si (`app/api/endpoints/`) nem para as tasks Celery (`worker/tasks/`).

Não é preciso `.env`/credenciais reais (R2, Suno, etc.) para correr a suite —
os testes usam SQLite em memória e mocks para os serviços externos.

## Referências

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Celery](https://docs.celeryq.dev/)
- [Librosa](https://librosa.org/)
- [Music21](https://mit.edu/music21/)
