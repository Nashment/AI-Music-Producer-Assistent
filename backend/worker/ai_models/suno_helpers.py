"""Helpers auxiliares para construir prompts e interpretar respostas da API Suno.

Extraido de worker.tasks.generation_tasks para reduzir o tamanho desse
modulo e isolar logica que nao depende do Celery / SQLAlchemy.
"""

from typing import Optional


def build_suno_prompt(prompt: str, instrument: str, genre: Optional[str], audio, tempo_override: Optional[int]) -> str:
    """Constroi o campo de estilo para a API Suno.

    Ordem de prioridade:
      instrumento + genero (identidade sonora) -> contexto musical (BPM, tom) ->
      descricao do utilizador (contexto criativo).
    """
    bpm = tempo_override or getattr(audio, "bpm", None)
    key = getattr(audio, "key", None)
    time_sig = getattr(audio, "time_signature", None)

    parts = [f"{instrument} solo"]
    if genre:
        parts.append(genre)
    if bpm:
        parts.append(f"{bpm} BPM")
    if key:
        parts.append(f"Key of {key}")
    if time_sig:
        parts.append(f"{time_sig} time signature")
    parts.append("professional quality")
    if prompt:
        parts.append(prompt)

    return ", ".join(parts)


def extract_suno_audio_url(payload: dict) -> Optional[str]:
    """Extrai o URL de audio da resposta da API Suno.

    Estrutura documentada: payload["data"]["response"]["sunoData"][n]["audioUrl"]
    Fallback para streamAudioUrl se audioUrl estiver ausente.
    """
    try:
        suno_data = payload["data"]["response"]["sunoData"]
        for item in suno_data:
            url = item.get("audioUrl") or item.get("streamAudioUrl")
            if isinstance(url, str) and url.strip().startswith(("http://", "https://")):
                return url.strip()
    except (KeyError, TypeError):
        return None
    return None


def extract_suno_task_status(payload: dict) -> Optional[str]:
    try:
        return payload["data"]["status"].strip().lower()
    except (KeyError, AttributeError):
        return None
