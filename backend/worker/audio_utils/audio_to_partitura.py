import os
import subprocess

CAMINHO_MUSESCORE = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"


def exportar_pdf_automatico(caminho_midi, caminho_pdf="solo_partitura.pdf"):
    print(f"A gerar PDF a partir de: {caminho_midi}")

    if not os.path.exists(caminho_midi):
        print("Erro: Ficheiro MIDI não encontrado!")
        return None

    comando = [
        CAMINHO_MUSESCORE,
        "-o", caminho_pdf,
        caminho_midi
    ]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return caminho_pdf
    except subprocess.CalledProcessError as e:
        print(f"Erro ao gerar PDF: {e.stderr.decode()}")
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None


if __name__ == "__main__":
    ficheiro_midi = "teste_rapido.mid"
    nome_do_pdf = "Partitura_Solo_Guitarra.pdf"
    resultado = exportar_pdf_automatico(ficheiro_midi, nome_do_pdf)
    if resultado:
        print("Partitura gerada com sucesso!")
        print(f"A sua partitura foi guardada automaticamente em: {resultado}")
        print("Verifique a pasta do seu projeto!")
        print("=" * 50)