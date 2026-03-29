import librosa
import soundfile as sf
import numpy as np
import warnings

# Ignorar os avisos normais do librosa sobre ficheiros MP3
warnings.filterwarnings("ignore")


def ajustar_bpm_automatico(ficheiro_entrada, ficheiro_saida, bpm_alvo=70.0):
    print(f"A carregar o audio original: {ficheiro_entrada}")

    # 1. Carregar o ficheiro de audio (sr=None mantem a qualidade original)
    try:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
    except Exception as e:
        print(f"Erro ao carregar o ficheiro. Certifica-te que tens o FFmpeg instalado. Detalhe: {e}")
        return

    # 2. Detetar o BPM atual da musica gerada pela IA
    print("A analisar a batida e calcular o BPM atual...")
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    # O librosa pode devolver um array ou um float, garantimos que e um numero
    bpm_atual = tempo[0] if isinstance(tempo, np.ndarray) else tempo
    print(f"BPM real detetado pela IA: {bpm_atual:.2f} BPM")

    # Se a IA por milagre tiver acertado (margem de 1 BPM), nao mexemos
    if abs(bpm_atual - bpm_alvo) < 1.0:
        print("O BPM original ja bate certo com o alvo. Nenhuma alteracao necessaria.")
        return

    # 3. Calcular a taxa de ajuste (Rate)
    # Se a IA fez a 80 BPM e queremos 70, a taxa sera 70/80 = 0.875 (abranda)
    # Se a IA fez a 60 BPM e queremos 70, a taxa sera 70/60 = 1.166 (acelera)
    taxa_ajuste = bpm_alvo / bpm_atual
    print(f"A ajustar o tempo para {bpm_alvo} BPM. (Taxa de Stretch: {taxa_ajuste:.3f}x)")

    # 4. Aplicar o Time-Stretch (Ajusta o tempo, mas mantem o tom de La Menor)
    y_ajustado = librosa.effects.time_stretch(y, rate=taxa_ajuste)

    # 5. Guardar o novo ficheiro
    print(f"A exportar o resultado final para: {ficheiro_saida}")
    sf.write(ficheiro_saida, y_ajustado, sr)
    print("Processo de audio concluido com sucesso.")


# Exemplo de utilizacao:
if __name__ == "__main__":
    # Substitui pelo nome do ficheiro que o teu outro script descarregou
    ficheiro_original = "solo_blues_finalizado_2cac6c_1.mp3"
    ficheiro_corrigido = "solo_blues_70BPM_perfeito.wav"

    # Chama a funcao
    ajustar_bpm_automatico(ficheiro_original, ficheiro_corrigido, bpm_alvo=70.0)