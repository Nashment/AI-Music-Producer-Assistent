"""Geração de tablatura de guitarra a partir de MIDI.

Pipeline novo (substitui midi2ly + regex):
    midi_data (pretty_midi) → eventos (notas/acordes) → quantização à
    grelha de semicolcheias → otimização de dedilhado (Viterbi com
    backpointers) → ficheiro .ly gerado por template → LilyPond → PDF.

Vantagens face à versão anterior:
- As anotações de corda/dedo são anexadas diretamente aos eventos, por
  construção — desaparece o alinhamento por regex que falhava em silêncio.
- Notas simultâneas são tratadas como acordes (estados conjuntos no
  otimizador), não como sequências impossíveis de tocar.
- A quantização usa o BPM real do MIDI (escrito pelo audio_extractor),
  pelo que as figuras rítmicas correspondem ao áudio.
- Viterbi com backpointers: O(n·S) de memória em vez de O(n²·S).
"""

import math
import os
import subprocess
from itertools import product

from app.core.config import settings

CAMINHO_LILYPOND = settings.LILYPOND_PATH

AFINACAO_GUITARRA = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
MAX_TRASTES = 22

# Notas simultâneas se os onsets distarem menos do que isto (segundos)
_EPSILON_ACORDE = 0.05

# Grelha de quantização: semicolcheia (em quarterLengths)
_GRID_QL = 0.25

_MAX_COMBOS_ACORDE = 32

_NOMES_LY = ['c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b']
_NOTAS_PT = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Durações LilyPond suportadas, da maior para a menor (quarterLength, token)
_DURACOES_LY = [
    (4.0, "1"), (3.0, "2."), (2.0, "2"),
    (1.5, "4."), (1.0, "4"),
    (0.75, "8."), (0.5, "8"),
    (0.25, "16"),
]


# ---------------------------------------------------------------------------
# Posições e custos (algoritmo de otimização)
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


def _posicoes_para_acorde(pitches):
    """Combinações viáveis de posições para um conjunto de notas simultâneas.

    Regras: cordas distintas, abertura entre trastes pisados ≤ 4. Os dedos
    são atribuídos pela distância à posição-âncora (traste mínimo pisado).
    Limita-se o número de combinações às mais compactas.
    """
    listas = []
    for p in pitches:
        # Para acordes, enumerar só (corda, traste); o dedo é derivado.
        base = {(c, t) for c, t, _ in obter_posicoes_possiveis(p)}
        if not base:
            return []
        listas.append(sorted(base))

    combos = []
    for combo in product(*listas):
        cordas = [c for c, _ in combo]
        if len(set(cordas)) != len(cordas):
            continue
        pisados = [t for _, t in combo if t > 0]
        if pisados and (max(pisados) - min(pisados)) > 4:
            continue

        ancora = min(pisados) if pisados else 0
        estado = tuple(
            (c, t, 0 if t == 0 else min(4, t - ancora + 1))
            for c, t in combo
        )
        span = (max(pisados) - min(pisados)) if pisados else 0
        combos.append((span, sum(t for _, t in combo), estado))

    combos.sort(key=lambda x: (x[0], x[1]))
    return [estado for _, _, estado in combos[:_MAX_COMBOS_ACORDE]]


def _estados_para_evento(pitches):
    """Estados possíveis para um evento (nota única ou acorde).

    Cada estado é um tuplo de posições (corda, traste, dedo) — com um
    elemento para notas únicas.
    """
    if len(pitches) == 1:
        return [(pos,) for pos in obter_posicoes_possiveis(pitches[0])]
    return _posicoes_para_acorde(pitches)


def _custo_transicao(estado_anterior, estado_atual):
    """Custo médio entre todas as posições dos dois estados."""
    total, n = 0.0, 0
    for pa in estado_anterior:
        for pb in estado_atual:
            total += calcular_custo_biomecanico(pa, pb)
            n += 1
    return total / n if n else 0.0


def otimizar_tablatura(sequencia):
    """Otimiza o dedilhado de uma sequência de eventos.

    `sequencia`: lista de pitches MIDI (int) e/ou listas de pitches
    (acordes). Devolve uma lista alinhada com a entrada onde cada item é
    (corda, traste, dedo) para notas únicas, ou um tuplo dessas posições
    para acordes. Devolve None se algum evento não tiver posição viável.
    """
    if not sequencia:
        return []

    eventos = []
    for item in sequencia:
        if isinstance(item, int):
            eventos.append([item])
        else:
            pitches = sorted(set(int(p) for p in item))
            if not pitches:
                return None
            eventos.append(pitches)

    estados_iniciais = _estados_para_evento(eventos[0])
    if not estados_iniciais:
        return None

    # Viterbi com backpointers: por passo guardamos só (custo, ptr anterior)
    custos = {s: 0.0 for s in estados_iniciais}
    backptrs = []          # backptrs[t][estado] = estado anterior ótimo
    estados_por_passo = [estados_iniciais]

    for evento in eventos[1:]:
        estados = _estados_para_evento(evento)
        if not estados:
            return None

        novos_custos = {}
        bp = {}
        for estado in estados:
            melhor_custo, melhor_anterior = math.inf, None
            for anterior, custo_acumulado in custos.items():
                custo = custo_acumulado + _custo_transicao(anterior, estado)
                if custo < melhor_custo:
                    melhor_custo, melhor_anterior = custo, anterior
            novos_custos[estado] = melhor_custo
            bp[estado] = melhor_anterior

        custos = novos_custos
        backptrs.append(bp)
        estados_por_passo.append(estados)

    # Reconstrução do caminho ótimo
    estado = min(custos, key=custos.get)
    caminho = [estado]
    for bp in reversed(backptrs):
        estado = bp[estado]
        caminho.append(estado)
    caminho.reverse()

    # Notas únicas devolvem a posição "nua" (compatibilidade com a API antiga)
    return [c[0] if len(c) == 1 else c for c in caminho]


# ---------------------------------------------------------------------------
# Eventos a partir do MIDI
# ---------------------------------------------------------------------------

def extrair_eventos(midi_data, epsilon=_EPSILON_ACORDE):
    """Agrupa as notas do MIDI em eventos (start, end, [pitches]).

    Notas cujo onset dista menos de `epsilon` segundos são agrupadas num
    acorde. Devolve a lista ordenada por início.
    """
    notas = [
        n
        for inst in midi_data.instruments
        if not getattr(inst, "is_drum", False)
        for n in inst.notes
    ]
    notas.sort(key=lambda n: (n.start, n.pitch))

    eventos = []
    for n in notas:
        if eventos and (n.start - eventos[-1][0]) <= epsilon:
            start, end, pitches = eventos[-1]
            if n.pitch not in pitches:
                pitches.append(n.pitch)
            eventos[-1] = (start, max(end, n.end), pitches)
        else:
            eventos.append((n.start, n.end, [n.pitch]))

    return [(s, e, sorted(p)) for s, e, p in eventos]


def extrair_lista_notas(midi_data):
    """Lista achatada de pitches por ordem temporal (API antiga)."""
    return [p for _, _, pitches in extrair_eventos(midi_data) for p in pitches]


# ---------------------------------------------------------------------------
# Quantização
# ---------------------------------------------------------------------------

def _obter_bpm_do_midi(midi_data, predefinido=120.0):
    try:
        _, tempi = midi_data.get_tempo_changes()
        if len(tempi) > 0 and tempi[0] > 0:
            return float(tempi[0])
    except Exception:
        pass
    return predefinido


def _quantizar_eventos(eventos, bpm):
    """Converte eventos (segundos) para a grelha de semicolcheias.

    Devolve lista de (offset_ql, duracao_ql, pitches, indice_original).
    Eventos que colidem no mesmo slot após arredondar são fundidos num
    acorde (mantém o índice do primeiro, para alinhar com o dedilhado).
    """
    ql_por_segundo = bpm / 60.0
    quantizados = []

    for idx, (start, end, pitches) in enumerate(eventos):
        offset = round((start * ql_por_segundo) / _GRID_QL) * _GRID_QL
        dur = round(((end - start) * ql_por_segundo) / _GRID_QL) * _GRID_QL
        dur = max(dur, _GRID_QL)

        if quantizados and abs(quantizados[-1][0] - offset) < 1e-9:
            o, d, p, i = quantizados[-1]
            quantizados[-1] = (o, max(d, dur), sorted(set(p) | set(pitches)), i)
        else:
            quantizados.append((offset, dur, list(pitches), idx))

    # Linha melódica: cortar durações que invadem o evento seguinte
    for i in range(len(quantizados) - 1):
        o, d, p, idx = quantizados[i]
        proximo = quantizados[i + 1][0]
        if o + d > proximo:
            quantizados[i] = (o, max(_GRID_QL, proximo - o), p, idx)

    return quantizados


def _ql_para_tokens(ql):
    """Decompõe uma duração em tokens LilyPond (ligados se forem vários)."""
    tokens = []
    restante = round(ql / _GRID_QL) * _GRID_QL
    while restante > 1e-9:
        for valor, token in _DURACOES_LY:
            if valor <= restante + 1e-9:
                tokens.append(token)
                restante -= valor
                break
        else:
            break
    return tokens or ["16"]


# ---------------------------------------------------------------------------
# Geração de LilyPond
# ---------------------------------------------------------------------------

def _pitch_para_ly(midi_pitch):
    nome = _NOMES_LY[midi_pitch % 12]
    oitava = midi_pitch // 12 - 1          # C4 (60) → oitava 4
    if oitava >= 4:
        return nome + "'" * (oitava - 3)
    if oitava <= 2:
        return nome + "," * (3 - oitava)
    return nome


def _tom_para_ly(tonalidade):
    """'C# Maior' → ('cis', '\\major'); devolve None se não reconhecido."""
    if not tonalidade or " " not in tonalidade:
        return None
    nota, modo = tonalidade.split(" ", 1)
    if nota not in _NOTAS_PT:
        return None
    nome = _NOMES_LY[_NOTAS_PT.index(nota)]
    modo_ly = "\\major" if modo.strip().lower().startswith("maior") else "\\minor"
    return nome, modo_ly


def _evento_para_ly(pitches, tokens_duracao, posicoes=None):
    """Constrói os tokens LilyPond de um evento (com ties se necessário)."""
    cordas = None
    if posicoes:
        # posicoes: tuplo de (corda, traste, dedo) alinhado com pitches ordenados
        ordenadas = sorted(posicoes, key=lambda p: AFINACAO_GUITARRA[p[0]] + p[1])
        if len(ordenadas) == len(pitches):
            cordas = [c for c, _, _ in ordenadas]

    def render(duracao):
        if len(pitches) == 1:
            base = _pitch_para_ly(pitches[0]) + duracao
            return base + (f"\\{cordas[0]}" if cordas else "")
        partes = []
        for j, p in enumerate(pitches):
            anotacao = f"\\{cordas[j]}" if cordas else ""
            partes.append(_pitch_para_ly(p) + anotacao)
        return "<" + " ".join(partes) + ">" + duracao

    return " ~ ".join(render(t) for t in tokens_duracao)


def _gerar_corpo_ly(midi_data, dedilhado=None, bpm=None, tonalidade=None,
                    compasso="4/4"):
    """Gera (corpo_de_notas, bpm, tom_ly) a partir do MIDI quantizado."""
    bpm = bpm or _obter_bpm_do_midi(midi_data)
    eventos = extrair_eventos(midi_data)
    quantizados = _quantizar_eventos(eventos, bpm)

    alinhado = dedilhado is not None and len(dedilhado) == len(eventos)

    tokens = []
    posicao = 0.0
    for offset, dur, pitches, idx in quantizados:
        # Pausas para preencher intervalos
        gap = offset - posicao
        if gap > 1e-9:
            for t in _ql_para_tokens(gap):
                tokens.append("r" + t)

        posicoes = None
        if alinhado:
            d = dedilhado[idx]
            posicoes = d if isinstance(d[0], tuple) else (d,)
            if len(posicoes) != len(pitches):
                posicoes = None        # evento fundido na quantização

        tokens.append(_evento_para_ly(pitches, _ql_para_tokens(dur), posicoes))
        posicao = offset + dur

    return " ".join(tokens), bpm, _tom_para_ly(tonalidade)


_TEMPLATE_LY = r"""\version "2.24.0"
\header {{ tagline = ##f }}
\score {{
  \new {staff} {{
    \clef "{clef}"
    \time {compasso}
    \tempo 4 = {bpm}
{key}    {{ {notas} }}
  }}
  \layout {{ }}
}}
"""


def _escrever_ly(caminho_ly, staff, clef, notas, bpm, tom_ly, compasso):
    key = f"    \\key {tom_ly[0]} {tom_ly[1]}\n" if tom_ly else ""
    conteudo = _TEMPLATE_LY.format(
        staff=staff, clef=clef, compasso=compasso,
        bpm=int(round(bpm)), key=key, notas=notas,
    )
    with open(caminho_ly, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return True


def gerar_ly_tablatura(midi_data, dedilhado, caminho_ly, bpm=None,
                       tonalidade=None, compasso="4/4"):
    """Gera um .ly de tablatura a partir do MIDI e do dedilhado otimizado.

    `dedilhado` pode ser None — nesse caso o LilyPond escolhe as cordas.
    """
    notas, bpm, tom_ly = _gerar_corpo_ly(midi_data, dedilhado, bpm, tonalidade, compasso)
    if not notas:
        raise RuntimeError("O MIDI não contém notas para gerar tablatura.")
    return _escrever_ly(
        caminho_ly, staff="TabStaff", clef="moderntab",
        notas=notas, bpm=bpm, tom_ly=tom_ly, compasso=compasso,
    )


def gerar_ly_partitura(midi_data, caminho_ly, bpm=None,
                       tonalidade=None, compasso="4/4"):
    """Gera um .ly de partitura convencional (fallback sem MuseScore)."""
    notas, bpm, tom_ly = _gerar_corpo_ly(midi_data, None, bpm, tonalidade, compasso)
    if not notas:
        raise RuntimeError("O MIDI não contém notas para gerar partitura.")
    return _escrever_ly(
        caminho_ly, staff="Staff", clef="treble",
        notas=notas, bpm=bpm, tom_ly=tom_ly, compasso=compasso,
    )


# ---------------------------------------------------------------------------
# Compilação
# ---------------------------------------------------------------------------

def compilar_pdf_lilypond(caminho_ly):
    output_prefix = str(os.path.splitext(caminho_ly)[0])
    comando = [CAMINHO_LILYPOND, "--output", output_prefix, caminho_ly]
    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except subprocess.CalledProcessError as e:
        raise RuntimeError((e.stderr or str(e)).strip()) from e


if __name__ == "__main__":
    import pretty_midi

    from worker.audio_utils.audio_extractor import extrair_midi_do_audio

    audio     = "c-major-scale.wav"
    midi_temp = "temp.mid"
    ly_temp   = "temp.ly"

    dados_midi = extrair_midi_do_audio(audio, midi_temp)
    eventos    = extrair_eventos(dados_midi)
    dedilhado  = otimizar_tablatura([p for _, _, p in eventos])
    gerar_ly_tablatura(dados_midi, dedilhado, ly_temp)
    compilar_pdf_lilypond(ly_temp)
    print("Tablatura gerada.")
