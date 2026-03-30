import requests
import time
import os

API_KEY = "fbcf463a0aa472ce3f6e11c45a5434c1"
BASE_URL = "https://api.sunoapi.org"
STYLE_PROMPT = "Slow emotional electric blues guitar solo, soulful bends, vibrato, 70 BPM, Key of A Minor, Am-F-C-G progression, clean overdriven tone"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def iniciar_geracao():
    url = f"{BASE_URL}/api/v1/generate"
    payload = {
        "customMode": True,
        "instrumental": True,
        "model": "V5",
        "style": STYLE_PROMPT,
        "title": "Solo Blues A Menor 70BPM",
        "callBackUrl": "https://webhook.site/vazio"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            res = response.json()
            if res.get("code") == 200:
                return res["data"]["taskId"]
        print("Erro ao iniciar geracao:", response.text)
    except Exception as e:
        print(f"Ocorreu um erro de rede ao iniciar: {e}")
    return None


def verificar_estado(task_id):
    url = f"{BASE_URL}/api/v1/get_music_details?taskId={task_id}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Erro de rede ao verificar estado: {e}")
    return None


def guardar_ficheiro(url, nome):
    print(f"A descarregar: {nome}...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(nome, 'wb') as f:
                f.write(r.content)
            print(f"Guardado em: {os.path.join(os.getcwd(), nome)}")
        else:
            print(f"Falha ao descarregar. Codigo HTTP: {r.status_code}")
    except Exception as e:
        print(f"Erro ao guardar o ficheiro no disco: {e}")


def executor():
    task_id = iniciar_geracao()
    if not task_id:
        return

    print(f"Tarefa {task_id} iniciada. A aguardar...")

    while True:
        time.sleep(30)
        dados = verificar_estado(task_id)

        if dados and dados.get("code") == 200:
            musicas = dados.get("data", [])

            # Verificamos se o array tem dados e se o primeiro item ja tem o link de audio
            if musicas and musicas[0].get("audio_url"):
                print("\nSolos prontos! A iniciar download...")
                for i, musica in enumerate(musicas):
                    url_mp3 = musica["audio_url"]
                    # Adicionei os ultimos 5 caracteres do task_id ao nome para nao sobrepor ficheiros antigos
                    nome_arquivo = f"solo_blues_{task_id[-5:]}_{i + 1}.mp3"
                    guardar_ficheiro(url_mp3, nome_arquivo)

                print("\nProcesso concluido com sucesso!")
                break  # Sai do loop porque o trabalho terminou
            else:
                print("Ainda a processar... (Aguardando os URLs dos MP3)")
        else:
            print("A verificar estado da tarefa...")


if __name__ == "__main__":
    executor()