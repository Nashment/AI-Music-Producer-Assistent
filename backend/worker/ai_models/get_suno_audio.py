import requests
import os

# ================= CONFIGURACAO =================
API_KEY = "fbcf463a0aa472ce3f6e11c45a5434c1"  # Coloca aqui a tua chave
BASE_URL = "https://api.sunoapi.org"
TASK_ID = "f46e6b34d0939a057aeb379afa2cac6c"
# ================================================

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def consultar_detalhes_oficiais(task_id):
    # Endpoint correto baseado na documentacao partilhada
    url = f"{BASE_URL}/api/v1/generate/record-info?taskId={task_id}"
    try:
        response = requests.get(url, headers=headers)
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
            print(f"Guardado com sucesso em: {caminho_completo}")
        else:
            print(f"Falha ao aceder ao ficheiro de audio. Codigo HTTP: {r.status_code}")
    except Exception as e:
        print(f"Erro ao guardar o ficheiro MP3 no disco: {e}")


def extrair_e_guardar_musicas():
    print(f"A consultar o estado oficial da tarefa {TASK_ID}...")

    dados = consultar_detalhes_oficiais(TASK_ID)

    # Verifica se a API respondeu corretamente
    if dados and dados.get("code") == 200:
        info_tarefa = dados.get("data", {})
        estado_tarefa = info_tarefa.get("status")

        print(f"Estado atual da tarefa na API: {estado_tarefa}")

        # De acordo com a documentacao, "SUCCESS" significa que gerou tudo
        if estado_tarefa == "SUCCESS":
            # Navega ate a lista de musicas seguindo a arvore do JSON da OpenAPI
            suno_data = info_tarefa.get("response", {}).get("sunoData", [])

            if len(suno_data) > 0:
                print(f"Encontrados {len(suno_data)} ficheiros de audio. A iniciar downloads...")

                for i, musica in enumerate(suno_data):
                    # O campo correto no novo schema e camelCase: audioUrl (nao audio_url)
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