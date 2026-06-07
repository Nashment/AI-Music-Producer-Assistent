import tempfile
from pathlib import Path

import librosa
import soundfile as sf
from basic_pitch.inference import predict

def _normalizar_para_wav(ficheiro_audio: str) -> tuple[str, bool]:
    """Converte qualquer formato para WAV mono 22050 Hz.
    Devolve (caminho_wav, e_temporario).
    """
    if Path(ficheiro_audio).suffix.lower() == ".wav":
        return ficheiro_audio, False

    y, sr = librosa.load(ficheiro_audio, sr=22050, mono=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    sf.write(tmp.name, y, sr)
    return tmp.name, True


def extrair_midi_do_audio(ficheiro_audio: str, ficheiro_midi: str):
    """Extrai MIDI do áudio e escreve-o em ficheiro_midi.

    Devolve o objeto midi_data em caso de sucesso.
    Levanta RuntimeError em caso de falha.
    """
    wav_path, e_temporario = _normalizar_para_wav(ficheiro_audio)
    try:
        _, midi_data, _ = predict(
            wav_path,
            onset_threshold=0.6,
            frame_threshold=0.4,
            minimum_note_length=58,
        )
        midi_data.write(ficheiro_midi)
        return midi_data
    except Exception as e:
        raise RuntimeError(f"Falha na extracção MIDI: {e}") from e
    finally:
        if e_temporario:
            Path(wav_path).unlink(missing_ok=True)
