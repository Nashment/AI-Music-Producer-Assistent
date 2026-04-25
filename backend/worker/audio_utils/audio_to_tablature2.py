import os
import subprocess
import re
import math
import sys
import importlib

if os.name == "nt":
    _DEFAULT_MIDI2LY = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\midi2ly.py"
    _DEFAULT_LILYPOND = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\lilypond.exe"
else:
    _DEFAULT_MIDI2LY = "/usr/bin/midi2ly"
    _DEFAULT_LILYPOND = "/usr/bin/lilypond"

CAMINHO_MIDI2LY = os.getenv("MIDI2LY_PATH", _DEFAULT_MIDI2LY)
CAMINHO_LILYPOND = os.getenv("LILYPOND_PATH", _DEFAULT_LILYPOND)
ULTIMO_ERRO_EXTRACAO = None
ULTIMO_ERRO_COMPILACAO = None

AFINACAO_GUITARRA = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
MAX_TRASTES = 22


def obter_posicoes_possiveis(nota_midi):
    posicoes = []
    for corda, base_midi in AFINACAO_GUITARRA.items():
        traste = nota_midi - base_midi
        if 0 <= traste <= MAX_TRASTES:
            if traste == 0:
                posicoes.append((corda, traste, 0))
            else:
                for dedo in [1, 2, 3, 4]:
                    posicoes.append((corda, traste, dedo))
    return posicoes


def calcular_custo_biomecanico(estado_anterior, estado_atual):
    corda1, traste1, dedo1 = estado_anterior
    corda2, traste2, dedo2 = estado_atual

    custo_total = 0.0

    # Distâncias físicas
    distancia_trastes = traste2 - traste1
    distancia_cordas = abs(corda2 - corda1)

    # CUSTO 1: Mudança de corda tem penalização para evitar saltos desnecessários
    custo_total += distancia_cordas * 2.0

    # Lidar com cordas soltas
    if traste1 == 0 or traste2 == 0:
        custo_total += 2.0
        custo_total += abs(distancia_trastes) * 1.5
        return custo_total

    # CUSTO 3: A LÓGICA DOS DEDOS (Apenas quando não há cordas soltas)
    if distancia_trastes > 0:
        if dedo1 == 4:
            custo_total += 50.0
        elif dedo1 in [1, 2]:
            custo_total += 1.0
    elif distancia_trastes < 0:
        if dedo1 == 1:
            custo_total += 50.0
        elif dedo1 in [3, 4]:
            custo_total += 1.0

    # CUSTO 4: Ergonomia da Abertura da Mão (Stretch)
    distancia_dedos = dedo2 - dedo1
    penalizacao_abertura = abs(distancia_trastes - distancia_dedos)
    custo_total += (penalizacao_abertura * 5.0)

    return custo_total


def otimizar_tablatura(sequencia_notas_midi):
    if not sequencia_notas_midi: return []

    caminhos = {}
    for estado in obter_posicoes_possiveis(sequencia_notas_midi[0]):
        caminhos[estado] = (0.0, [estado])

    for nota_midi in sequencia_notas_midi[1:]:
        novos_caminhos = {}
        estados_possiveis_atual = obter_posicoes_possiveis(nota_midi)

        if not estados_possiveis_atual:
            print(f"ERRO: A nota MIDI {nota_midi} não existe na guitarra!")
            return None

        for estado_atual in estados_possiveis_atual:
            melhor_custo = math.inf
            melhor_caminho = []

            for estado_anterior, (custo_acumulado, caminho_anterior) in caminhos.items():
                custo_total = custo_acumulado + calcular_custo_biomecanico(estado_anterior, estado_atual)
                if custo_total < melhor_custo:
                    melhor_custo = custo_total
                    melhor_caminho = caminho_anterior + [estado_atual]

            novos_caminhos[estado_atual] = (melhor_custo, melhor_caminho)
        caminhos = novos_caminhos

    melhor_estado = min(caminhos, key=lambda k: caminhos[k][0])
    return caminhos[melhor_estado][1]


def extrair_midi_do_audio(ficheiro_audio, ficheiro_midi):
    global ULTIMO_ERRO_EXTRACAO
    ULTIMO_ERRO_EXTRACAO = None
    print("Passo 1: A extrair MIDI do Áudio...")
    try:
        inference_module = importlib.import_module("basic_pitch.inference")
        predict = getattr(inference_module, "predict")
        model_output, midi_data, note_events = predict(
            ficheiro_audio, onset_threshold=0.6, frame_threshold=0.4, minimum_note_length=58
        )
        midi_data.write(ficheiro_midi)
        return True, midi_data  # Devolvemos o midi_data para o algoritmo ler!
    except ModuleNotFoundError:
        ULTIMO_ERRO_EXTRACAO = "Dependência 'basic_pitch' não instalada no ambiente Python."
        print(f"ERRO: {ULTIMO_ERRO_EXTRACAO}")
        return False, None, ULTIMO_ERRO_EXTRACAO
    except Exception as e:
        ULTIMO_ERRO_EXTRACAO = str(e)
        print(f"ERRO: {ULTIMO_ERRO_EXTRACAO}")
        return False, None, ULTIMO_ERRO_EXTRACAO


def obter_ultimo_erro_extracao():
    return ULTIMO_ERRO_EXTRACAO


def obter_ultimo_erro_compilacao():
    return ULTIMO_ERRO_COMPILACAO


def extrair_lista_notas(midi_data):
    """Lê o objeto MIDI e cria a lista de notas [64, 65...] para o teu algoritmo"""
    notas_lista = []
    # Pega no primeiro instrumento (a guitarra)
    for instrument in midi_data.instruments:
        # Ordena as notas pelo tempo em que são tocadas
        notas_ordenadas = sorted(instrument.notes, key=lambda nota: nota.start)
        for nota in notas_ordenadas:
            notas_lista.append(nota.pitch)
    return notas_lista


def converter_midi_para_ly(caminho_midi, caminho_ly):
    print("Passo 2: Converter MIDI para LilyPond...")
    if not os.path.exists(CAMINHO_MIDI2LY):
        print(f"ERRO: midi2ly não encontrado em: {CAMINHO_MIDI2LY}")
        return False

    comando = [sys.executable, CAMINHO_MIDI2LY, "-o", caminho_ly, caminho_midi]
    subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return True


def injetar_inteligencia_no_ly(caminho_ly, dedilhado_otimizado):
    print("Passo 3/4 - A injetar a inteligência do dedilhado na Tablatura...")
    if dedilhado_otimizado is None:
        dedilhado_otimizado = []

    try:
        with open(caminho_ly, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # 1. Limpar claves normais (Sol/Fá)
        conteudo = re.sub(r'\\clef\s+"?[a-zA-Z_]+"?', '', conteudo)

        # 2. Forçar a pauta para Tablatura Moderna de 6 linhas
        conteudo = re.sub(r'\\new\s+Staff', r'\\new TabStaff \\with { \\clef "moderntab" }', conteudo)
        conteudo = re.sub(r'\\context\s+Staff', r'\\context TabStaff', conteudo)

        # 3. Mudar para TabVoice e ATIVAR O DESENHO DOS DEDOS (Fingering_engraver)
        conteudo = re.sub(r'\\context\s+Voice', r'\\context TabVoice \\consists "Fingering_engraver"', conteudo)

        # 4. Encontrar todas as notas puras geradas pelo midi2ly (ex: c4, d8, fis16)
        notas_lilypond = re.findall(r'[a-g](?:is|es)?[\',]*\d*\.*', conteudo)

        # 5. Injetar a corda e o dedo em cada nota
        if len(notas_lilypond) == len(dedilhado_otimizado):
            for i, nota_original in enumerate(notas_lilypond):
                corda = dedilhado_otimizado[i][0]  # Índice 0 é a corda
                dedo = dedilhado_otimizado[i][2]  # Índice 2 é o dedo

                # Só escrevemos o dedo se não for corda solta (0)
                if dedo != 0:
                    nota_com_corda = f"{nota_original}\\{corda}-{dedo}"
                else:
                    nota_com_corda = f"{nota_original}\\{corda}"

                # Substitui a primeira ocorrência da nota exata encontrada (para manter a ordem correta)
                conteudo = conteudo.replace(nota_original, nota_com_corda, 1)
        else:
            print(
                f"AVISO: O número de notas no ficheiro ({len(notas_lilypond)}) não coincide com o algoritmo ({len(dedilhado_otimizado)}).")
            print("A tablatura será desenhada de forma padrão, sem o dedilhado otimizado.")

        # 6. Guardar as alterações e reescrever o ficheiro .ly
        with open(caminho_ly, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        print("SUCESSO: Dedilhados e cordas injetados perfeitamente no código LilyPond.")
        return True

    except Exception as e:
        print(f"ERRO ao editar o ficheiro .ly: {e}")
        return False


def forcar_tablatura_no_ly(caminho_ly):
    """Converte o .ly para TabStaff sem dedilhado otimizado."""
    print("Passo 3/4 - A converter para tablatura padrão...")

    try:
        with open(caminho_ly, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        conteudo = re.sub(r'\\clef\s+"?[a-zA-Z_]+"?', '', conteudo)
        conteudo = re.sub(r'\\new\s+Staff', r'\\new TabStaff \\with { \\clef "moderntab" }', conteudo)
        conteudo = re.sub(r'\\context\s+Staff', r'\\context TabStaff', conteudo)
        conteudo = re.sub(r'\\context\s+Voice', r'\\context TabVoice', conteudo)

        with open(caminho_ly, 'w', encoding='utf-8') as f:
            f.write(conteudo)

        return True
    except Exception as e:
        print(f"ERRO ao converter .ly para tablatura padrão: {e}")
        return False


def compilar_pdf_lilypond(caminho_ly):
    global ULTIMO_ERRO_COMPILACAO
    ULTIMO_ERRO_COMPILACAO = None
    print("Passo 4: A desenhar o PDF final...")
    if not os.path.exists(CAMINHO_LILYPOND):
        ULTIMO_ERRO_COMPILACAO = f"LilyPond não encontrado em: {CAMINHO_LILYPOND}"
        print(f"ERRO: {ULTIMO_ERRO_COMPILACAO}")
        return False

    output_prefix = str(os.path.splitext(caminho_ly)[0])
    comando = [CAMINHO_LILYPOND, "--output", output_prefix, caminho_ly]
    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except subprocess.CalledProcessError as e:
        ULTIMO_ERRO_COMPILACAO = (e.stderr or str(e)).strip()
        print(f"ERRO LilyPond: {ULTIMO_ERRO_COMPILACAO}")
        return False
    except Exception as e:
        ULTIMO_ERRO_COMPILACAO = str(e)
        print(f"ERRO LilyPond: {ULTIMO_ERRO_COMPILACAO}")
        return False


if __name__ == "__main__":
    audio = "c-major-scale.wav"
    midi_temp = "temp.mid"
    ly_temp = "temp.ly"

    sucesso_audio, dados_midi = extrair_midi_do_audio(audio, midi_temp)

    if sucesso_audio:
        lista_notas_midi = extrair_lista_notas(dados_midi)

        print(f"Notas extraídas do áudio: {len(lista_notas_midi)} notas encontradas.")

        dedilhado_calculado = otimizar_tablatura(lista_notas_midi)

        if converter_midi_para_ly(midi_temp, ly_temp):
            if injetar_inteligencia_no_ly(ly_temp, dedilhado_calculado):
                if compilar_pdf_lilypond(ly_temp):
                    print("Processo concluído com sucesso!")