# Integração do Worker (Celery)

## Visão Geral

Dois workers com filas separadas para evitar que tarefas rápidas fiquem bloqueadas
atrás de tarefas longas:

| Fila       | Worker                   | Tarefas                                   | Duração típica |
|------------|--------------------------|-------------------------------------------|----------------|
| `celery`   | `celery_worker`          | Geração Suno (original + cover), pós-proc | 86–200 s       |
| `notation` | `celery_worker_notation` | Tablatura (LilyPond), partitura (Music21)  | 4–9 s          |

## Ficheiros relevantes

- `backend/worker/celery_app.py` — configuração Celery
- `backend/worker/tasks/generation_tasks.py` — todas as tasks
- `backend/app/services/generation_service.py` — submissão e orquestração

## Pipeline de geração (`process_generation_task` — fila `celery`)

Acionado por `POST /api/v1/generation` ou `POST /api/v1/generation/cover`:

1. Cria registo `pending` em `generations`
2. Enfileira task → devolve `202 Accepted` imediatamente
3. Worker muda estado para `processing`
4. Envia pedido à Suno AI
5. Polling de estado até completar
6. Descarrega áudio para diretório de output
7. **Pós-processamento automático:**
   - Analisa BPM e tonalidade do áudio gerado
   - Ajusta BPM se diferença > 5 BPM face ao projeto
   - Transpõe tonalidade se não coincidir com o áudio original
8. Atualiza estado para `completed` ou `failed`

## Notação — dois fluxos distintos

Há **dois pares de endpoints** de notação com comportamentos diferentes — é
fácil confundi-los porque produzem o mesmo tipo de PDF, mas o contrato HTTP
não é o mesmo.

### 1. A partir de um upload cru — síncrono

`POST /generation/tablature/{audio_id}` e `POST /generation/partitura/{audio_id}`.
O pedido bloqueia até o PDF estar pronto e a resposta já é o próprio ficheiro
(`FileResponse`). Sem polling, sem estado persistido.

**Tablatura:**
1. Extrai MIDI do áudio (via `audio_to_tablature2`)
2. Converte MIDI para LilyPond (`.ly`)
3. Aplica estilo de tablatura (dedilhado inteligente ou standard)
4. Compila para PDF via LilyPond (com fallback se compilação falhar)
5. Devolve o PDF ao endpoint, que o serve como `FileResponse` e apaga o
   ficheiro do disco a seguir (background task)

**Partitura:**
1. Exporta PDF via Music21 (`audio_to_partitura`)
2. Devolve o PDF ao endpoint, que o serve como `FileResponse`

### 2. A partir de uma geração/corte já existente — assíncrono (fire-and-forget)

`POST /generation/{id}/tablature` e `POST /generation/{id}/partitura`. Estes
NÃO devolvem o PDF diretamente:

1. O POST enfileira a task em background e devolve **202 Accepted** de
   imediato, com o `GenerationResult` já com `..._status='pending'`
2. O worker processa (mesmos passos do fluxo síncrono acima) e faz upload do
   PDF resultante para o R2, guardando a `..._storage_key` e mudando
   `..._status` para `completed` (ou `failed`)
3. O cliente faz polling de `GET /generation/{id}/cuts` (ou `/status`) até
   ver `..._status='completed'`
4. Só então chama `GET /generation/{id}/partitura` ou
   `GET /generation/{id}/tablature`, que devolve a presigned URL R2 do PDF
   (`409` se o estado ainda não for `completed`)
5. O mesmo endpoint POST serve para **regenerar** — é idempotente, chamar de
   novo relança o processamento e volta a `pending`

Isto é o que o frontend usa (`CutActionPanel.tsx` / `generationService.ts`) —
ver aí os comentários de código para o fluxo completo do lado do cliente,
incluindo o polling em `useAudioGenerations.ts`.

## Comandos

### Docker (tudo junto)

```bash
cd docker
docker compose up -d
```

### Workers locais

```bash
# Janela 1 — fila de geração
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=celery --loglevel=info

# Janela 2 — fila de notação
cd backend
celery -A worker.celery_app:celery_app worker --pool=solo --queues=notation --loglevel=info
```

### Flower (monitorização)

```bash
celery -A worker.celery_app:celery_app flower
# http://localhost:5555
```

## Endpoints relacionados

### Geração assíncrona (fila `celery`)
- `POST /api/v1/generation` — geração original
- `POST /api/v1/generation/cover` — cover
- `GET /api/v1/generation/{id}/status` — polling de estado
- `GET /api/v1/generation/{id}` — resultado completo
- `GET /api/v1/generation/{id}/audio` — presigned URL R2 do áudio

### Cortes (síncronos, sem fila)
- `POST /api/v1/generation/{id}/cut` — cria corte (início/fim em segundos)
- `GET /api/v1/generation/{id}/cuts` — lista cortes
- `GET /api/v1/generation/by-audio/{audio_id}` — todas as gerações de um áudio

### Notação — upload cru, síncrono (fila `notation`)
- `POST /api/v1/generation/tablature/{audio_id}` — tablatura de upload, devolve o PDF
- `POST /api/v1/generation/partitura/{audio_id}` — partitura de upload, devolve o PDF

### Notação — a partir de geração, assíncrono (fila `notation`)
- `POST /api/v1/generation/{id}/tablature` — enfileira (202), idempotente/regera
- `GET /api/v1/generation/{id}/tablature` — presigned URL R2 (409 se não `completed`)
- `POST /api/v1/generation/{id}/partitura` — enfileira (202), idempotente/regera
- `GET /api/v1/generation/{id}/partitura` — presigned URL R2 (409 se não `completed`)

## Diretórios de output

Por omissão (relativos ao backend):
- Áudio gerado: `backend/worker/generations/audio/`
- Partituras:   `backend/worker/generations/partitura/`
- Tablaturas:   `backend/worker/generations/tablatura/`

Sobrepostos pelas variáveis de ambiente:
- `GENERATIONS_AUDIO_DIR`
- `GENERATIONS_PARTITURA_DIR`
- `GENERATIONS_TABLATURA_DIR`

## Notas de operação

- Broker e backend de resultados: Redis
- Pool do worker configurado para `solo` (evita conflitos com stack async)
- App path Celery: `worker.celery_app:celery_app`
- Os PDFs do fluxo síncrono (upload cru) são servidos e depois apagados
  automaticamente do disco local (background task); os do fluxo assíncrono
  (a partir de uma geração) ficam persistidos no R2
