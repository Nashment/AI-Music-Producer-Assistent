import os
import subprocess
from basic_pitch.inference import predict
import sys
import re

# =====================================================================
# CONFIGURACOES DE CAMINHOS
# Atualiza estes caminhos para onde o LilyPond ficou instalado no teu PC
# =====================================================================
CAMINHO_MIDI2LY = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\midi2ly.py"
CAMINHO_LILYPOND = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\lilypond.exe"


def extrair_midi_do_audio(ficheiro_audio, ficheiro_midi):
    print(f"Passo 1/4 - A extrair notas de '{ficheiro_audio}'...")

    if not os.path.exists(ficheiro_audio):
        print("ERRO: Ficheiro de audio nao encontrado!")
        return False

    try:
        model_output, midi_data, note_events = predict(
            ficheiro_audio,
            onset_threshold=0.6,
            frame_threshold=0.4,
            minimum_note_length=58
        )
        midi_data.write(ficheiro_midi)
        print(f"SUCESSO: MIDI gerado: {ficheiro_midi}")
        return True
    except Exception as e:
        print(f"ERRO ao processar audio: {e}")
        return False


def converter_midi_para_ly(caminho_midi, caminho_ly):
    print("Passo 2/4 - A converter MIDI para codigo LilyPond...")

    # O sys.executable garante que usamos o caminho absoluto do teu Python atual
    comando = [sys.executable, CAMINHO_MIDI2LY, "-o", caminho_ly, caminho_midi]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"SUCESSO: Ficheiro .ly criado: {caminho_ly}")
        return True
    except subprocess.CalledProcessError as e:
        print("ERRO no midi2ly:")
        print(e.stderr.decode())
        return False


def forcar_tablatura_no_ly(caminho_ly):
    print("Passo 3/4 - A transformar a pauta numa Tablatura (Baseado no teu codigo)...")

    try:
        with open(caminho_ly, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # 1. Eliminar claves de Sol ou Fa que o midi2ly possa ter posto
        conteudo = re.sub(r'\\clef\s+"?[a-zA-Z_]+"?', '', conteudo)

        # 2. Substituir qualquer instáncia de Staff por TabStaff com a clave de Tablatura Moderna
        # Inspirado no teu: \context TabVoice = "upper tab" { \clef "moderntab" ... }
        conteudo = re.sub(r'\\new\s+Staff', r'\\new TabStaff \\with { \\clef "moderntab" }', conteudo)
        conteudo = re.sub(r'\\context\s+Staff', r'\\context TabStaff', conteudo)
        conteudo = re.sub(r'\\context\s+Voice', r'\\context TabVoice', conteudo)

        with open(caminho_ly, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        print("SUCESSO: Codigo LilyPond forcado para Tablatura com sucesso.")
        return True
    except Exception as e:
        print(f"ERRO ao editar o ficheiro .ly: {e}")
        return False


def compilar_pdf_lilypond(caminho_ly):
    print("Passo 4/4 - A compilar o PDF final com o LilyPond...")

    # O LilyPond gera o PDF na mesma pasta e com o mesmo nome base do .ly
    comando = [CAMINHO_LILYPOND, caminho_ly]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("SUCESSO: PDF desenhado perfeitamente.")
        return True
    except subprocess.CalledProcessError as e:
        print("ERRO no lilypond:")
        print(e.stderr.decode())
        return False


if __name__ == "__main__":
    audio = "c-major-scale.wav"
    midi_temp = "escala.mid"
    ly_temp = "escala.ly"
    # O LilyPond vai criar o ficheiro escala.pdf automaticamente

    print("=" * 50)
    print("A INICIAR O GERADOR LILYPOND")
    print("=" * 50)

    if extrair_midi_do_audio(audio, midi_temp):
        if converter_midi_para_ly(midi_temp, ly_temp):
            if forcar_tablatura_no_ly(ly_temp):
                if compilar_pdf_lilypond(ly_temp):
                    print("\n" + "=" * 50)
                    print("PROCESSO CONCLUIDO!")
                    print("Verificar a pasta, procurar PDF.")
                    print("=" * 50)