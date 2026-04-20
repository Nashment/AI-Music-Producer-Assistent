import librosa
import soundfile as sf
import warnings

warnings.filterwarnings("ignore")


def cortar_audio(ficheiro_entrada, ficheiro_saida, inicio_segundos=0, fim_segundos=30):
    print(f"A carregar o audio para corte: {ficheiro_entrada}")

    try:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
        inicio_samples = int(inicio_segundos * sr)
        fim_samples = int(fim_segundos * sr)
        y_cortado = y[inicio_samples:fim_samples]
        sf.write(ficheiro_saida, y_cortado, sr)
        print(f"Audio cortado com sucesso de {inicio_segundos}s a {fim_segundos}s: {ficheiro_saida}")

    except Exception as e:
        print(f"Erro ao cortar o audio: {e}")


if __name__ == "__main__":
    ficheiro_original = "solo_blues_finalizado_2cac6c_1.mp3"
    ficheiro_cortado = "solo_blues_corte.wav"
    cortar_audio(ficheiro_original, ficheiro_cortado, inicio_segundos=10, fim_segundos=40)