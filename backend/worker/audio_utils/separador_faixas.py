import subprocess
import os
import shutil
import sys


def extrair_instrumento(caminho_audio, instrumento_desejado, output_dir=None):
    mapa_instrumentos = {
        "bateria": "drums.wav",
        "baixo": "bass.wav",
        "piano": "piano.wav",
        "guitarra": "guitar.wav",
        "voz": "vocals.wav",
        "outros": "other.wav"
    }

    instrumento_formatado = instrumento_desejado.lower().strip()

    if instrumento_formatado not in mapa_instrumentos:
        print(f"Erro: Instrumento '{instrumento_desejado}' não suportado.")
        print(f"Escolhe um destes: {', '.join(mapa_instrumentos.keys())}")
        return

    if not os.path.exists(caminho_audio):
        print(f"Erro: Ficheiro '{caminho_audio}' não encontrado.")
        return

    nome_ficheiro_demucs = mapa_instrumentos[instrumento_formatado]
    nome_base_musica = os.path.splitext(os.path.basename(caminho_audio))[0]
    destino_dir = output_dir if output_dir else os.getcwd()

    print(f"A processar '{nome_base_musica}'... A isolar a {instrumento_formatado}!")

    comando = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", caminho_audio]

    try:
        subprocess.run(comando, check=True, capture_output=True)

        pasta_output_demucs = os.path.join("separated", "htdemucs_6s", nome_base_musica)
        caminho_ficheiro_isolado = os.path.join(pasta_output_demucs, nome_ficheiro_demucs)
        novo_nome_ficheiro = os.path.join(destino_dir, f"{nome_base_musica}_{instrumento_formatado}.wav")

        if os.path.exists(caminho_ficheiro_isolado):
            shutil.move(caminho_ficheiro_isolado, novo_nome_ficheiro)
            print(f"Guardado: {novo_nome_ficheiro}")

            if os.path.exists("separated"):
                shutil.rmtree("separated")
                print("Limpeza concluída.")
        else:
            print("Erro: O Demucs não conseguiu gerar o ficheiro.")

    except subprocess.CalledProcessError as e:
        print(f"Ocorreu um erro ao correr o Demucs: {e}")
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    ficheiro_musica = "solo_blues_finalizado_cac6c_1.mp3"
    instrumento_escolhido = "guitarra"
    extrair_instrumento(ficheiro_musica, instrumento_escolhido)