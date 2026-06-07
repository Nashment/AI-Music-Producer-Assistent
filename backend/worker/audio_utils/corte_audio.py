"""
Util de corte de áudio.

Carrega um ficheiro de áudio (mp3/wav), extrai o intervalo
[inicio_segundos, fim_segundos] e escreve um novo ficheiro WAV.

Devolve True/False em vez de simplesmente imprimir, para o serviço poder
mapear para um Resultado de domínio. Se o ficheiro original tiver duração
menor do que `fim_segundos`, o corte é truncado em vez de falhar — o
chamador pode validar antes se quiser ser estrito.
"""

import warnings
from pathlib import Path

import librosa
import soundfile as sf

warnings.filterwarnings("ignore")


def cortar_audio(
    ficheiro_entrada: str,
    ficheiro_saida: str,
    inicio_segundos: float = 0.0,
    fim_segundos: float = 30.0,
) -> None:
    """Corta `ficheiro_entrada` entre os tempos dados e grava em `ficheiro_saida`.

    Levanta RuntimeError em caso de erro.
    """
    if inicio_segundos < 0:
        raise RuntimeError("O tempo de início não pode ser negativo.")
    if fim_segundos <= inicio_segundos:
        raise RuntimeError("O tempo de fim deve ser maior que o tempo de início.")

    Path(ficheiro_saida).parent.mkdir(parents=True, exist_ok=True)

    y, sr = librosa.load(ficheiro_entrada, sr=None)

    total_samples = len(y)
    inicio_samples = int(inicio_segundos * sr)
    fim_samples = min(int(fim_segundos * sr), total_samples)

    if inicio_samples >= total_samples:
        raise RuntimeError("O tempo de início está fora da duração do ficheiro.")

    y_cortado = y[inicio_samples:fim_samples]
    if len(y_cortado) == 0:
        raise RuntimeError("O intervalo de corte resultou em áudio vazio.")

    sf.write(ficheiro_saida, y_cortado, sr)


def obter_duracao_audio(ficheiro_entrada: str) -> float:
    """Devolve a duração em segundos. Lança se não conseguir ler."""
    return float(librosa.get_duration(path=ficheiro_entrada))


if __name__ == "__main__":
    try:
        cortar_audio("solo_blues_finalizado_2cac6c_1.mp3", "solo_blues_corte.wav", 10, 40)
        print("OK")
    except RuntimeError as e:
        print(f"FALHOU: {e}")
