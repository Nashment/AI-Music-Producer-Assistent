import os
import warnings

import librosa
import mido
import soundfile as sf

warnings.filterwarnings("ignore")

NOTAS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def _nota_apos_transposicao(tom_original: str, semitons: int) -> str:
    partes = tom_original.strip().split()
    nome_nota = partes[0]
    sufixo = " " + " ".join(partes[1:]) if len(partes) > 1 else ""

    bemois = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'}
    nome_nota = bemois.get(nome_nota, nome_nota)

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
