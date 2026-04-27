# Estrutura Atual do Projeto

Documento descritivo da estrutura real existente no repositório.

## Backend

```text
backend/
├── main.py
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── user.py
│   │       ├── projects.py
│   │       ├── audio.py
│   │       └── generation.py
│   ├── core/
│   ├── data/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── queries.py
│   │   └── oauth_queries.py
│   ├── domain/dtos/endpoints/
│   └── services/
├── worker/
│   ├── celery_app.py
│   ├── tasks/generation_tasks.py
│   ├── ai_models/
│   ├── audio_utils/
│   └── generations/
└── tests/
```

## Docker

```text
docker/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── SQL/
│   ├── 01_init_schema.sql
│   └── 02_create_tables.sql
└── scripts/
```

## Frontend

```text
frontend/
├── src/
│   ├── main.tsx        (vazio)
│   ├── components/     (vazio)
│   ├── hooks/          (vazio)
│   ├── pages/          (vazio)
│   ├── services/       (vazio)
│   └── utils/          (vazio)
├── style/              (vazio)
└── tests/              (vazio)
```

## Dados (modelos ORM)

Modelos definidos em `backend/app/data/models.py`:
- `User`
- `Project`
- `AudioFile`
- `Generation`

Enums relevantes:
- `OAuthProvider`
- `GenerationStatusEnum`

## Observações

- A estrutura de testes existe, mas os testes de serviços ainda estão em grande parte por implementar.
- O fluxo principal de geração está desacoplado da API via Celery.
