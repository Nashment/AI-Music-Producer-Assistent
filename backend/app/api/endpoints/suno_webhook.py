"""
Suno Webhook endpoint — recebe callbacks do Suno quando uma task termina.

O Suno chama este endpoint automaticamente se SUNO_CALLBACK_URL estiver
configurado. O worker usa polling de qualquer forma, por isso este
endpoint serve principalmente para logs e debug.
"""

import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook")
async def suno_webhook(request: Request):
    """Recebe notificacoes de tasks concluidas do Suno API."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    task_id   = payload.get("taskId") or payload.get("data", {}).get("taskId")
    status    = payload.get("status") or payload.get("data", {}).get("status")
    success   = payload.get("successFlag")

    logger.info(
        "[suno-webhook] task_id=%s status=%s successFlag=%s",
        task_id, status, success,
    )
    # O worker Celery ja usa polling para actualizar o estado na BD.
    # Este endpoint existe para satisfazer o campo obrigatorio callBackUrl
    # da API Suno e para registo de eventos.
    return {"received": True}
