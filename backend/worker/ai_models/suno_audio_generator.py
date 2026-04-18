import os
import requests

API_KEY = os.getenv("SUNO_API_KEY", "fbcf463a0aa472ce3f6e11c45a5434c1")
BASE_URL = "https://api.sunoapi.org"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def iniciar_geracao(style_prompt: str, title: str = "Generated Music", instrumental: bool = True, model: str = "V5") -> str | None:
    """Submete um pedido de geração ao Suno e devolve o taskId, ou None em caso de erro."""
    url = f"{BASE_URL}/api/v1/generate"
    payload = {
        "customMode": True,
        "instrumental": instrumental,
        "model": model,
        "style": style_prompt,
        "title": title,
        "callBackUrl": "https://webhook.site/vazio"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if res.get("code") == 200:
                return res["data"]["taskId"]
        print("Erro ao iniciar geração:", response.text)
    except Exception as e:
        print(f"Erro de rede ao iniciar geração: {e}")
    return None


def verificar_estado(task_id: str) -> dict | None:
    """Consulta o estado de uma tarefa Suno. Devolve o JSON da resposta ou None."""
    url = f"{BASE_URL}/api/v1/get_music_details?taskId={task_id}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
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
