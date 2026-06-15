"""Extração de MIDI a partir de áudio (Basic Pitch).

Melhorias face à versão anterior:
- O tempo real (BPM) é detetado e passado a `predict(midi_tempo=...)`.
  Sem isto o MIDI saía sempre a 120 BPM e toda a quantização rítmica da
  partitura/tablatura ficava errada.
- Thresholds repostos nos defaults do modelo (0.5/0.3) — os valores
  anteriores (0.6/0.4) descartavam notas reais.
- `minimum_note_length` passa a escalar com o BPM (≈ uma semicolcheia)
  em vez de ser fixo em 58 ms.
"""

import tempfile
from pathlib import Path

import librosa
import soundfile as sf
from basic_pitch.inference import predict

from worker.audio_utils.audio_analyzer import detetar_bpm_robusto

_SR = 22050


def _normalizar_para_wav(ficheiro_audio: str) -> tuple[str, bool]:
    """Converte qualquer formato para WAV mono 22050 Hz.
    Devolve (caminho_wav, e_temporario).
    """
    if Path(ficheiro_audio).suffix.lower() == ".wav":
        return ficheiro_audio, False

    y, sr = librosa.load(ficheiro_audio, sr=_SR, mono=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    sf.write(tmp.name, y, sr)
    return tmp.name, True


def _comprimento_minimo_nota_ms(bpm: float) -> float:
    """≈ 90% de uma semicolcheia ao BPM dado, limitado a [30, 80] ms."""
    semicolcheia_ms = (60.0 / bpm / 4.0) * 1000.0
    return float(min(80.0, max(30.0, semicolcheia_ms * 0.9)))


def extrair_midi_do_audio(ficheiro_audio: str, ficheiro_midi: str, bpm: float | None = None):
    """Extrai MIDI do áudio e escreve-o em `ficheiro_midi`.

    Se `bpm` não for fornecido, é detetado a partir do próprio áudio.
    Devolve o objeto midi_data (pretty_midi) em caso de sucesso.
    Levanta RuntimeError em caso de falha.
    """
    wav_path, e_temporario = _normalizar_para_wav(ficheiro_audio)
    try:
        if bpm is None or bpm <= 0:
            y, sr = librosa.load(wav_path, sr=_SR, mono=True)
            bpm, _ = detetar_bpm_robusto(y, sr)

        _, midi_data, _ = predict(
            wav_path,
            onset_threshold=0.5,
            frame_threshold=0.3,
            minimum_note_length=_comprimento_minimo_nota_ms(bpm),
            midi_tempo=float(bpm),
        )
        midi_data.write(ficheiro_midi)
        return midi_data
    except Exception as e:
        raise RuntimeError(f"Falha na extracção MIDI: {e}") from e
    finally:
        if e_temporario:
            Path(wav_path).unlink(missing_ok=True)
