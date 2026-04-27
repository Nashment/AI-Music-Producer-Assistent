# Integração do Worker (Celery)

## Estado Atual no Código

Integração assíncrona implementada com:
- Celery app: `backend/worker/celery_app.py`
- Tasks: `backend/worker/tasks/generation_tasks.py`
- Submissão de tasks: `backend/app/services/generation_service.py`

## Task principal

Quando é feito `POST /api/v1/generation`, o backend:
1. cria registo `pending` em `generations`
2. enfileira task `process_generation_task`
3. devolve `202 Accepted`

Worker executa:
1. muda estado para `processing`
2. envia pedido à Suno
3. faz polling de estado
4. descarrega áudio para pasta de saída
5. atualiza estado final `completed` ou `failed`

## Comandos reais

### Docker (tudo junto)

```bash
cd docker
docker compose up -d
```

### Worker local

```bash
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --loglevel=info
```

### Flower (opcional)

```bash
cd backend
celery -A worker.celery_app:celery_app flower
```

## Endpoints relacionados

- `POST /api/v1/generation`
- `POST /api/v1/generation/cover`
- `GET /api/v1/generation/{generation_id}/status`
- `GET /api/v1/generation/{generation_id}`
- `DELETE /api/v1/generation/{generation_id}`

## Diretórios de output

No código, por omissão:
- áudio: `backend/worker/generations/audio`
- partitura: `backend/worker/generations/partitura`
- tablatura: `backend/worker/generations/tablatura`

Podem ser sobrepostos por variáveis de ambiente:
- `GENERATIONS_AUDIO_DIR`
- `GENERATIONS_PARTITURA_DIR`
- `GENERATIONS_TABLATURA_DIR`

## Notas de operação

- Broker e backend de resultados: Redis
- Pool do worker configurado para `solo` para evitar conflitos com stack async
- App path preferido para Celery: `worker.celery_app:celery_app`
- Alias legado ainda existe em `app.worker:app`
