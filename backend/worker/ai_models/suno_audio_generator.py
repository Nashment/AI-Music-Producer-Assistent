import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load backend/.env when this module is used standalone.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

API_KEY = os.getenv("SUNO_API_KEY")
BASE_URL = "https://api.sunoapi.org"

headers = {"Content-Type": "application/json"}


def iniciar_geracao(style_prompt: str, title: str = "Generated Music", instrumental: bool = True, model: str = "V5_5") -> str | None:
    """Submete um pedido de geração ao Suno e devolve o taskId, ou None em caso de erro."""
    if not API_KEY:
        raise RuntimeError("SUNO_API_KEY não está definida. Configure no backend/.env")

    url = f"{BASE_URL}/api/v1/generate"
    request_headers = {**headers, "Authorization": f"Bearer {API_KEY}"}
    payload = {
        "customMode": True,
        "instrumental": instrumental,
        "model": model,
        "style": style_prompt,
        "title": title,
        "callBackUrl": "https://webhook.site/vazio"
    }

    try:
        response = requests.post(url, headers=request_headers, json=payload, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if res.get("code") == 200:
                return res["data"]["taskId"]
        print("Erro ao iniciar geração:", response.text)
    except Exception as e:
        print(f"Erro de rede ao iniciar geração: {e}")
    return None


def iniciar_cover(
    upload_url: str,
    style_prompt: str,
    title: str = "Generated Cover",
    instrumental: bool = True,
    model: str = "V5_5",
    audio_weight: float = 0.7,
) -> str | None:
    """Submete um pedido de cover ao Suno e devolve o taskId, ou None em caso de erro."""
    if not API_KEY:
        raise RuntimeError("SUNO_API_KEY não está definida. Configure no backend/.env")

    if not upload_url or not upload_url.startswith(("http://", "https://")):
        raise ValueError("upload_url inválido. Deve ser uma URL pública http(s).")

    url = f"{BASE_URL}/api/v1/generate/upload-cover"
    request_headers = {**headers, "Authorization": f"Bearer {API_KEY}"}
    payload = {
        "customMode": True,
        "instrumental": instrumental,
        "model": model,
        "style": style_prompt,
        "title": title,
        "uploadUrl": upload_url,
        "audioWeight": audio_weight,
        "callBackUrl": "https://webhook.site/vazio",
    }

    try:
        response = requests.post(url, headers=request_headers, json=payload, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if res.get("code") == 200:
                return res["data"]["taskId"]
        print("Erro ao iniciar cover:", response.text)
    except Exception as e:
        print(f"Erro de rede ao iniciar cover: {e}")
    return None


def verificar_estado(task_id: str) -> dict | None:
    if not API_KEY:
        raise RuntimeError("SUNO_API_KEY não está definida. Configure no backend/.env")

    url = f"{BASE_URL}/api/v1/generate/record-info?taskId={task_id}"
    request_headers = {**headers, "Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(url, headers=request_headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Erro de rede ao verificar estado: {e}")
    return None


def guardar_ficheiro(url: str, caminho: str) -> bool:
    """Descarrega um ficheiro de uma URL e guarda-o no caminho indicado. Devolve True em sucesso."""
    print(f"A descarregar: {caminho}...")
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200:
            with open(caminho, 'wb') as f:
                f.write(r.content)
            print(f"Guardado em: {caminho}")
            return True
        print(f"Falha ao descarregar. Código HTTP: {r.status_code}")
    except Exception as e:
        print(f"Erro ao guardar o ficheiro: {e}")
    return False
