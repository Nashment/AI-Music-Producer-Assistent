import subprocess
import os
import shutil
import sys


def extrair_instrumento(caminho_audio, instrumento_desejado):
    """
    Processa o áudio com o Demucs, guarda apenas o instrumento desejado
    na pasta atual e limpa os restantes ficheiros.
    """
    # Dicionário para traduzir o que pedes para os nomes de ficheiro do Demucs
    mapa_instrumentos = {
        "bateria": "drums.wav",
        "baixo": "bass.wav",
        "piano": "piano.wav",
        "guitarra": "guitar.wav",
        "voz": "vocals.wav",
        "outros": "other.wav"
    }

    instrumento_formatado = instrumento_desejado.lower().strip()

    # Verifica se o instrumento pedido existe no nosso mapa
    if instrumento_formatado not in mapa_instrumentos:
        print(f"Erro: Instrumento '{instrumento_desejado}' não suportado.")
        print(f"Escolhe um destes: {', '.join(mapa_instrumentos.keys())}")
        return

    if not os.path.exists(caminho_audio):
        print(f"Erro: O ficheiro '{caminho_audio}' não foi encontrado.")
        return

    nome_ficheiro_demucs = mapa_instrumentos[instrumento_formatado]

    # Extrai o nome da música original (sem a extensão .mp3 ou .wav)
    nome_base_musica = os.path.splitext(os.path.basename(caminho_audio))[0]

    print(f"A processar '{nome_base_musica}'... A isolar a {instrumento_formatado}!")

    # Comando do Demucs (usamos o htdemucs_6s para garantir a guitarra e piano)
    comando = [sys.executable, "-m", "demucs", "-n", "htdemucs_6s", caminho_audio]

    try:
        # Executa o Demucs (o output vai ficar em silêncio no terminal para não sujar muito)
        subprocess.run(comando, check=True, capture_output=True)

        # O Demucs cria sempre esta estrutura de pastas por defeito:
        # separated/htdemucs_6s/nome_da_musica/
        pasta_output_demucs = os.path.join("separated", "htdemucs_6s", nome_base_musica)
        caminho_ficheiro_isolado = os.path.join(pasta_output_demucs, nome_ficheiro_demucs)

        # Onde vamos guardar o ficheiro final (na pasta onde está este script)
        novo_nome_ficheiro = f"{nome_base_musica}_{instrumento_formatado}.wav"

        if os.path.exists(caminho_ficheiro_isolado):
            # Move o ficheiro desejado para a pasta do script
            shutil.move(caminho_ficheiro_isolado, novo_nome_ficheiro)
            print(f"Sucesso! O ficheiro foi guardado como: {novo_nome_ficheiro}")

            # Limpeza: Apagar a pasta 'separated' e todo o lixo lá dentro
            if os.path.exists("separated"):
                shutil.rmtree("separated")
                print("Limpeza concluída. Ficheiros extra apagados.")
        else:
            print("Erro: O Demucs não conseguiu gerar o ficheiro.")

    except subprocess.CalledProcessError as e:
        print(f"Ocorreu um erro ao correr o Demucs: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")


# --- Testar o Script ---
# Substitui 'teste_suno.mp3' pelo nome do ficheiro que geraste no Suno
# e escolhe o instrumento (ex: "guitarra", "bateria", "piano")

ficheiro_musica = "solo_blues_finalizado_cac6c_1.mp3"
instrumento_escolhido = "guitarra"

extrair_instrumento(ficheiro_musica, instrumento_escolhido)