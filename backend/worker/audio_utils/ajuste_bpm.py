import librosa
import soundfile as sf
import numpy as np
import warnings

warnings.filterwarnings("ignore")


def ajustar_bpm_automatico(ficheiro_entrada, ficheiro_saida, bpm_alvo=70.0):
    print(f"A carregar o audio original: {ficheiro_entrada}")

    try:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
    except Exception as e:
        print(f"Erro ao carregar o ficheiro: {e}")
        return

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm_atual = tempo[0] if isinstance(tempo, np.ndarray) else tempo
    print(f"BPM detectado: {bpm_atual:.2f} BPM")

    if abs(bpm_atual - bpm_alvo) < 1.0:
        print("BPM já está correto.")
        return

    taxa_ajuste = bpm_alvo / bpm_atual
    print(f"A ajustar para {bpm_alvo} BPM...")

    y_ajustado = librosa.effects.time_stretch(y, rate=taxa_ajuste)

    print(f"A exportar para: {ficheiro_saida}")
    sf.write(ficheiro_saida, y_ajustado, sr)
    print("Concluído.")


if __name__ == "__main__":
    ficheiro_original = "solo_blues_finalizado_2cac6c_1.mp3"
    ficheiro_corrigido = "solo_blues_70BPM_perfeito.wav"
    ajustar_bpm_automatico(ficheiro_original, ficheiro_corrigido, bpm_alvo=70.0)