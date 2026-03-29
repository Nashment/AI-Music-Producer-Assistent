import os
import subprocess

# =====================================================================
# CONFIGURACAO DO CAMINHO DO MUSESCORE
# Confirme se este e o caminho correto no seu computador
# =====================================================================
CAMINHO_MUSESCORE = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"


def exportar_pdf_automatico(caminho_midi, caminho_pdf="solo_partitura.pdf"):
    print(f"A iniciar a maquina de escrever pautas para: {caminho_midi}")

    if not os.path.exists(caminho_midi):
        print("ERRO: O ficheiro MIDI nao foi encontrado!")
        return None

    print("A pedir ao MuseScore para desenhar o PDF em modo invisivel...")

    # O comando: "-o" diz ao MuseScore para exportar o ficheiro diretamente
    comando = [
        CAMINHO_MUSESCORE,
        "-o", caminho_pdf,  # O ficheiro de saida (PDF)
        caminho_midi  # O ficheiro de entrada (MIDI)
    ]

    try:
        # Executa o comando silenciosamente
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return caminho_pdf

    except subprocess.CalledProcessError as e:
        print("\nERRO AO GERAR PDF:")
        print(e.stderr.decode())
        return None
    except Exception as e:
        print(f"\nERRO DESCONHECIDO: {e}")
        return None


if __name__ == "__main__":
    # O ficheiro MIDI que queremos converter
    ficheiro_midi = "teste_rapido.mid"
    nome_do_pdf = "Partitura_Solo_Guitarra.pdf"

    resultado = exportar_pdf_automatico(ficheiro_midi, nome_do_pdf)

    if resultado:
        print("\n" + "=" * 50)
        print("SUCESSO ABSOLUTO!")
        print(f"A sua partitura foi guardada automaticamente em: {resultado}")
        print("Verifique a pasta do seu projeto!")
        print("=" * 50)