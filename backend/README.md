# Backend - AI Music Producer Assistant

## Estado

Backend funcional com FastAPI, PostgreSQL e Celery.

## Estrutura principal

```text
backend/
├── main.py
├── app/
│   ├── api/
│   │   ├── router.py
│   │   └── endpoints/
│   ├── core/
│   ├── data/
│   ├── domain/dtos/endpoints/
│   └── services/
├── worker/
│   ├── celery_app.py
│   └── tasks/
└── tests/
```

## Executar localmente

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\Activate.ps1
pip install -r ..\docker\requirements.txt
uvicorn main:app --reload
```

API:
- `http://localhost:8000`
- `http://localhost:8000/docs`

## Executar worker localmente

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

Flower (opcional):

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

## Endpoints reais

Base prefix: `/api/v1`

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

## Autenticação

- OAuth implementado com Google no router atual.
- JWT obrigatório nas rotas protegidas via header:

```text
Authorization: Bearer <token>
```

## Testes

```bash
cd backend
pytest -v
```

Nota: os testes em `backend/tests/` estão incompletos (há vários `TODO`/`pass`).
# The health check endpoint: GET /health
```

## Contributing

1. Create feature branch
2. Follow PEP 8 style guide
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Librosa Audio Analysis](https://librosa.org/)
- [Music21 MIDI](https://mit.edu/music21/)
