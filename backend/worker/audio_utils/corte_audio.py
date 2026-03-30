import librosa
import soundfile as sf
import warnings

warnings.filterwarnings("ignore")


def cortar_audio_para_30_segundos(ficheiro_entrada, ficheiro_saida, duracao_segundos=30):
    print(f"A carregar o audio para corte: {ficheiro_entrada}")

    try:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
        limite_samples = duracao_segundos * sr
        y_cortado = y[:limite_samples]
        sf.write(ficheiro_saida, y_cortado, sr)
        print(f"Audio cortado com sucesso para {duracao_segundos} segundos: {ficheiro_saida}")

    except Exception as e:
        print(f"Erro ao cortar o audio: {e}")


if __name__ == "__main__":
    ficheiro_original = "solo_blues_finalizado_2cac6c_1.mp3"
    ficheiro_cortado = "solo_blues_30s.wav"
    cortar_audio_para_30_segundos(ficheiro_original, ficheiro_cortado, 30)