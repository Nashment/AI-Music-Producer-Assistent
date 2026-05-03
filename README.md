# AI Music Producer Assistant

Backend funcional com FastAPI + Celery. Frontend em scaffolding.

## Visão Geral

Plataforma para apoio à produção musical com IA:
- Upload e análise de áudio base (BPM, tonalidade, assinatura temporal, acordes)
- Geração assíncrona via Suno AI (música original e covers)
- Pós-processamento automático do áudio gerado (ajuste de BPM, transposição de tonalidade)
- Conversão para partitura (PDF via Music21) e tablatura (PDF via LilyPond)
- Operações de áudio: ajuste de BPM, corte, separação de faixas por instrumento
- Gestão por projetos e utilizador autenticado (Google OAuth + JWT)

## Arquitetura

```
API (FastAPI)  →  Services (lógica de negócio)  →  Data (queries SQLAlchemy)
                        ↓
               Worker (Celery + Redis)
                        ↓
               Suno AI + Audio Utils
```

Os serviços comunicam sucesso/falha através de um tipo `Resultado[E, T]` (padrão Either),
nunca lançando exceções para a camada de endpoint. A tradução para HTTP Problem Details
(RFC 7807) é feita exclusivamente nos endpoints.

## Estado do Projeto

| Componente         | Estado                                    |
|--------------------|-------------------------------------------|
| Backend API        | Funcional                                 |
| Autenticação       | Google OAuth + JWT (funcional)            |
| Worker / Celery    | Funcional (geração + pós-processamento)   |
| Frontend           | Apenas scaffolding (sem código funcional) |
| Testes             | Estrutura criada, maioritariamente `pass` |

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
│   │   │       └── generation.py
│   │   ├── core/
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
│   │   └── services/
│   │       ├── user_service.py
│   │       ├── project_service.py
│   │       ├── audio_service.py
│   │       └── generation_service.py
│   ├── worker/
│   │   ├── celery_app.py
│   │   ├── tasks/
│   │   │   └── generation_tasks.py
│   │   ├── ai_models/
│   │   │   └── suno_audio_generator.py
│   │   └── audio_utils/
│   │       ├── audio_analyzer.py
│   │       ├── ajuste_bpm.py
│   │       ├── corte_audio.py
│   │       ├── separador_faixas.py
│   │       ├── transposicao.py
│   │       ├── audio_to_partitura.py
│   │       └── audio_to_tablature2.py
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

### Docker Compose (recomendado)

```bash
cd docker
docker compose up -d
```

Serviços iniciados:
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- pgAdmin: `http://localhost:5050`

### Backend local (sem container do backend)

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

### Worker Celery local

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

Flower (painel de monitorização):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

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
| POST | `/audio/project/{project_id}/upload` | Upload + análise |
| GET | `/audio/analysis/{audio_id}` | Metadados de análise |
| GET | `/audio/{audio_id}` | Download do ficheiro |
| DELETE | `/audio/{audio_id}` | Elimina áudio |
| POST | `/audio/{audio_id}/adjust-bpm` | Ajusta BPM |
| POST | `/audio/{audio_id}/cut` | Corta intervalo de tempo |
| POST | `/audio/{audio_id}/separate-tracks` | Separa faixa de instrumento |

### Generation (`/generation`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/generation` | Submete geração de música original |
| POST | `/generation/cover` | Submete geração de cover |
| POST | `/generation/tablature/{audio_id}` | Gera tablatura PDF |
| POST | `/generation/partitura/{audio_id}` | Gera partitura PDF |
| GET | `/generation/{generation_id}/status` | Estado da geração |
| GET | `/generation/{generation_id}` | Resultado completo |
| DELETE | `/generation/{generation_id}` | Elimina geração |

## Autenticação

Todas as rotas exceto `/users/auth/google/login` e `/users/auth/google/callback` requerem:

```
Authorization: Bearer <jwt>
```

O JWT é obtido no callback do Google OAuth.

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

## Documentação Detalhada

- `PROJECT_STATUS.md` — estado atual por área
- `QUICK_START.md` — guia de arranque com troubleshooting
- `POSTMAN_QUERIES.md` — exemplos de pedidos prontos a usar
- `docs/ESTRUTURA_CRIADA.md` — estrutura de ficheiros detalhada
- `docs/INTEGRACAO_WORKER.md` — pipeline Celery/Suno
- `docs/OAUTH_SETUP.md` — configuração do Google OAuth
