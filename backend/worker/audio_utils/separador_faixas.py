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
        raise ValueError(
            f"Instrumento '{instrumento_desejado}' não suportado. "
            f"Escolhe um destes: {', '.join(mapa_instrumentos.keys())}"
        )

    if not os.path.exists(caminho_audio):
        raise FileNotFoundError(f"Ficheiro '{caminho_audio}' não encontrado.")

    nome_ficheiro_demucs = mapa_instrumentos[instrumento_formatado]
    nome_base_musica = os.path.splitext(os.path.basename(caminho_audio))[0]
    destino_dir = output_dir if output_dir else os.getcwd()

    print(f"A processar '{nome_base_musica}'... A isolar a {instrumento_formatado}!")

    comando = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "--device", "cpu", caminho_audio]

    try:
        result = subprocess.run(comando, check=True, capture_output=True, text=True)

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
            raise RuntimeError(
                f"O Demucs não gerou o ficheiro esperado '{nome_ficheiro_demucs}'. "
                f"Stderr: {result.stderr[:500] if result.stderr else 'sem output'}"
            )

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao correr o Demucs: {e.stderr if e.stderr else str(e)}")


if __name__ == "__main__":
    ficheiro_musica = "solo_blues_finalizado_cac6c_1.mp3"
    instrumento_escolhido = "guitarra"
    extrair_instrumento(ficheiro_musica, instrumento_escolhido)