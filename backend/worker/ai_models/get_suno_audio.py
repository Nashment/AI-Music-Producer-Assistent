import requests
import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env when this script runs directly.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

API_KEY = os.getenv("SUNO_API_KEY")
BASE_URL = "https://api.sunoapi.org"
TASK_ID = "f46e6b34d0939a057aeb379afa2cac6c"

headers = {"Content-Type": "application/json"}


def consultar_detalhes_oficiais(task_id):
    if not API_KEY:
        raise RuntimeError("SUNO_API_KEY não está definida. Configure no backend/.env")

    url = f"{BASE_URL}/api/v1/generate/record-info?taskId={task_id}"
    request_headers = {**headers, "Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(url, headers=request_headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Erro de ligacao: {e}")
    return None


def descarregar_audio(url, nome_ficheiro):
    print(f"A descarregar: {nome_ficheiro}...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            caminho_completo = os.path.join(os.getcwd(), nome_ficheiro)
            with open(caminho_completo, 'wb') as f:
                f.write(r.content)
            print(f"Guardado em: {caminho_completo}")
        else:
            print(f"Erro HTTP: {r.status_code}")
    except Exception as e:
        print(f"Erro ao guardar ficheiro: {e}")


def extrair_e_guardar_musicas():
    print(f"A consultar estado da tarefa {TASK_ID}...")

    dados = consultar_detalhes_oficiais(TASK_ID)

    if dados and dados.get("code") == 200:
        info_tarefa = dados.get("data", {})
        estado_tarefa = info_tarefa.get("status")

        print(f"Estado: {estado_tarefa}")

        if estado_tarefa == "SUCCESS":
            suno_data = info_tarefa.get("response", {}).get("sunoData", [])

            if len(suno_data) > 0:
                print(f"Encontrados {len(suno_data)} ficheiros. A descarregar...")

                for i, musica in enumerate(suno_data):
                    url_mp3 = musica.get("audioUrl")

                    if url_mp3:
                        nome_arquivo = f"solo_blues_finalizado_{TASK_ID[-5:]}_{i + 1}.mp3"
                        descarregar_audio(url_mp3, nome_arquivo)
                    else:
                        print(f"Aviso: A musica {i + 1} nao contem um 'audioUrl' valido.")
            else:
                print("A tarefa diz estar concluida, mas a lista de musicas (sunoData) esta vazia.")
        else:
            print(f"A tarefa ainda nao esta no estado 'SUCCESS'.")
    else:
        print("Nao foi possivel obter os detalhes da API.")


if __name__ == "__main__":
    extrair_e_guardar_musicas()