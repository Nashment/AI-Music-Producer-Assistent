import os
import subprocess
import re
import math
import sys

from app.core.config import settings

CAMINHO_MIDI2LY  = settings.MIDI2LY_PATH
CAMINHO_LILYPOND = settings.LILYPOND_PATH

AFINACAO_GUITARRA = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
MAX_TRASTES = 22

# Padrão para notas geradas pelo midi2ly (ex: c4*198/220, fis'8).
# Lookbehind (?<![a-zA-Z]) evita matches dentro de palavras (trackA, channel…).
# Inclui o multiplicador *n/m para que as anotações fiquem DEPOIS dele.
_REGEX_NOTA = r'(?<![a-zA-Z])[a-g](?:is|es)?[\',]*\d+\.*(?:\*\d+/\d+)?'


# ---------------------------------------------------------------------------
# Algoritmo de otimização
# ---------------------------------------------------------------------------

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

    distancia_trastes = traste2 - traste1
    distancia_cordas  = abs(corda2 - corda1)

    custo_total = distancia_cordas * 2.0

    if traste1 == 0 or traste2 == 0:
        custo_total += 2.0 + abs(distancia_trastes) * 1.5
        return custo_total

    if distancia_trastes > 0:
        custo_total += 50.0 if dedo1 == 4 else (1.0 if dedo1 in [1, 2] else 0.0)
    elif distancia_trastes < 0:
        custo_total += 50.0 if dedo1 == 1 else (1.0 if dedo1 in [3, 4] else 0.0)

    penalizacao_abertura = abs(distancia_trastes - (dedo2 - dedo1))
    custo_total += penalizacao_abertura * 5.0

    return custo_total


def otimizar_tablatura(sequencia_notas_midi):
    if not sequencia_notas_midi:
        return []

    caminhos = {
        estado: (0.0, [estado])
        for estado in obter_posicoes_possiveis(sequencia_notas_midi[0])
    }

    for nota_midi in sequencia_notas_midi[1:]:
        estados_possiveis = obter_posicoes_possiveis(nota_midi)

        if not estados_possiveis:
            return None

        novos_caminhos = {}
        for estado_atual in estados_possiveis:
            melhor_custo   = math.inf
            melhor_caminho = []

            for estado_anterior, (custo_acumulado, caminho_anterior) in caminhos.items():
                custo = custo_acumulado + calcular_custo_biomecanico(estado_anterior, estado_atual)
                if custo < melhor_custo:
                    melhor_custo   = custo
                    melhor_caminho = caminho_anterior + [estado_atual]

            novos_caminhos[estado_atual] = (melhor_custo, melhor_caminho)

        caminhos = novos_caminhos

    melhor_estado = min(caminhos, key=lambda k: caminhos[k][0])
    return caminhos[melhor_estado][1]


# ---------------------------------------------------------------------------
# Pipeline de áudio → MIDI
# ---------------------------------------------------------------------------

def extrair_lista_notas(midi_data):
    notas = []
    for instrument in midi_data.instruments:
        for nota in sorted(instrument.notes, key=lambda n: n.start):
            notas.append(nota.pitch)
    return notas


# ---------------------------------------------------------------------------
# Pipeline MIDI → LilyPond → PDF
# ---------------------------------------------------------------------------

def converter_midi_para_ly(caminho_midi, caminho_ly):
    comando = [sys.executable, CAMINHO_MIDI2LY, "-o", caminho_ly, caminho_midi]
    subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return True


def _transformar_ly_para_tabstaff(conteudo: str, com_fingering: bool) -> str:
    """Aplica as substituições regex comuns a ambos os pipelines."""
    conteudo = re.sub(r'\\clef\s+"?[a-zA-Z_]+"?', '', conteudo)
    conteudo = re.sub(r'\\new\s+Staff', r'\\new TabStaff \\with { \\clef "moderntab" }', conteudo)
    conteudo = re.sub(r'\\context\s+Staff', r'\\context TabStaff', conteudo)

    if com_fingering:
        # midi2ly gera "\context Voice = voiceA", o = nome tem de ficar
        # entre \context TabVoice e o \with { }.
        conteudo = re.sub(
            r'(\\context\s+Voice)(\s*=\s*\w+)?',
            lambda m: r'\context TabVoice' + (m.group(2) or '') + r' \with { \consists "Fingering_engraver" }',
            conteudo,
        )
    else:
        conteudo = re.sub(r'\\context\s+Voice(\s*=\s*\w+)?', r'\\context TabVoice\1', conteudo)

    return conteudo


def injetar_inteligencia_no_ly(caminho_ly, dedilhado_otimizado):
    if dedilhado_otimizado is None:
        dedilhado_otimizado = []

    with open(caminho_ly, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    conteudo = _transformar_ly_para_tabstaff(conteudo, com_fingering=True)

    notas_lilypond = re.findall(_REGEX_NOTA, conteudo)

    if len(notas_lilypond) == len(dedilhado_otimizado):
        idx = [0]

        def _substituir(m):
            i = idx[0]
            idx[0] += 1
            token = m.group(0)
            corda = dedilhado_otimizado[i][0]
            dedo  = dedilhado_otimizado[i][2]
            return f"{token}\\{corda}-{dedo}" if dedo != 0 else f"{token}\\{corda}"

        conteudo = re.sub(_REGEX_NOTA, _substituir, conteudo)

    with open(caminho_ly, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return True


def forcar_tablatura_no_ly(caminho_ly):
    """Converte o .ly para TabStaff sem dedilhado otimizado."""
    with open(caminho_ly, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    conteudo = _transformar_ly_para_tabstaff(conteudo, com_fingering=False)

    with open(caminho_ly, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return True


def compilar_pdf_lilypond(caminho_ly):
    output_prefix = str(os.path.splitext(caminho_ly)[0])
    comando = [CAMINHO_LILYPOND, "--output", output_prefix, caminho_ly]
    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except subprocess.CalledProcessError as e:
        raise RuntimeError((e.stderr or str(e)).strip()) from e


if __name__ == "__main__":
    audio     = "c-major-scale.wav"
    midi_temp = "temp.mid"
    ly_temp   = "temp.ly"

    sucesso, dados_midi = extrair_midi_do_audio(audio, midi_temp)
    if sucesso:
        notas      = extrair_lista_notas(dados_midi)
        dedilhado  = otimizar_tablatura(notas)
        converter_midi_para_ly(midi_temp, ly_temp)
        injetar_inteligencia_no_ly(ly_temp, dedilhado)
        compilar_pdf_lilypond(ly_temp)
