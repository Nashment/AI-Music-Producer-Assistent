import os
import warnings

import librosa
import mido
import soundfile as sf

warnings.filterwarnings("ignore")

NOTAS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

BEMOIS_PARA_SUSTENIDOS = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
    'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B',
}


def extrair_nota_raiz(tom: str | None) -> str | None:
    """Extrai e normaliza (sustenidos) a nota raiz de uma string de tom.

    Ex: 'Bb Maior' -> 'A#', 'D Maior' -> 'D'.
    """
    if not tom:
        return None
    nota = tom.strip().split()[0]
    nota = BEMOIS_PARA_SUSTENIDOS.get(nota, nota)
    return nota if nota in NOTAS else None


def extrair_modo(tom: str | None) -> str | None:
    """Extrai o modo ('Maior' ou 'Menor') de uma string de tom, ex: 'D Maior' -> 'Maior'."""
    if not tom:
        return None
    partes = tom.strip().split()
    if len(partes) < 2:
        return None
    modo = partes[1].strip().lower()
    if modo.startswith("mai"):
        return "Maior"
    if modo.startswith("men") or modo.startswith("min"):
        return "Menor"
    return None


def normalizar_para_raiz_maior_equivalente(tom: str | None) -> str | None:
    """Devolve a nota raiz da tonalidade maior equivalente (relativa) de um tom.

    Tons relativos partilham a mesma armadura/notas: a relativa maior de um
    tom menor fica 3 semitons acima da sua raiz (ex: 'B Menor' -> 'D').
    Para um tom maior, devolve a propria raiz (ex: 'D Maior' -> 'D').
    """
    nota = extrair_nota_raiz(tom)
    if not nota:
        return None
    if extrair_modo(tom) == "Menor":
        return NOTAS[(NOTAS.index(nota) + 3) % 12]
    return nota


def calcular_semitons_entre_tons(tom_original: str | None, tom_gerado: str | None) -> int:
    """Calcula quantos semitons transpor `tom_gerado` para igualar `tom_original`.

    Tons iguais ou relativos (mesma armadura/notas) devolvem 0 -- nao e
    necessaria nenhuma transposicao.
    """
    raiz_orig_maior = normalizar_para_raiz_maior_equivalente(tom_original)
    raiz_ger_maior = normalizar_para_raiz_maior_equivalente(tom_gerado)
    if not raiz_orig_maior or not raiz_ger_maior:
        return 0
    if raiz_orig_maior == raiz_ger_maior:
        return 0

    diff = (NOTAS.index(raiz_orig_maior) - NOTAS.index(raiz_ger_maior)) % 12
    if diff > 6:
        diff -= 12
    return diff


def _nota_apos_transposicao(tom_original: str, semitons: int) -> str:
    partes = tom_original.strip().split()
    nome_nota = partes[0]
    sufixo = " " + " ".join(partes[1:]) if len(partes) > 1 else ""

    nome_nota = BEMOIS_PARA_SUSTENIDOS.get(nome_nota, nome_nota)

    if nome_nota not in NOTAS:
        return tom_original

    idx = NOTAS.index(nome_nota)
    nova_nota = NOTAS[(idx + semitons) % 12]
    return nova_nota + sufixo


def _transpor_midi(ficheiro_entrada: str, ficheiro_saida: str, semitons: int) -> None:
    midi = mido.MidiFile(ficheiro_entrada)
    for track in midi.tracks:
        for msg in track:
            if msg.type in ('note_on', 'note_off'):
                msg.note = max(0, min(127, msg.note + semitons))
    midi.save(ficheiro_saida)


def transpor_musica(
    ficheiro_entrada: str,
    ficheiro_saida: str,
    semitons: int,
    tom_original: str | None = None,
) -> dict:
    """Transpoe uma musica por um numero de semitons.

    Suporta ficheiros de audio (WAV, MP3, FLAC, OGG, etc.) e ficheiros MIDI.
    Para audio usa librosa.effects.pitch_shift (fase-vocoder).
    Para MIDI desloca diretamente os valores de nota.
    """
    if semitons == 0:
        return {
            "semitons": 0,
            "tom_original": tom_original,
            "tom_resultante": tom_original,
            "ficheiro_saida": ficheiro_saida,
        }

    extensao = os.path.splitext(ficheiro_entrada)[1].lower()

    if extensao in ('.mid', '.midi'):
        _transpor_midi(ficheiro_entrada, ficheiro_saida, semitons)
    else:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
        y_transposto = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitons)
        sf.write(ficheiro_saida, y_transposto, sr)

    tom_resultante = _nota_apos_transposicao(tom_original, semitons) if tom_original else None

    return {
        "semitons": semitons,
        "tom_original": tom_original,
        "tom_resultante": tom_resultante,
        "ficheiro_saida": ficheiro_saida,
    }
