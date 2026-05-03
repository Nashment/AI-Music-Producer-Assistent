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
) -> bool:
    """Corta `ficheiro_entrada` entre os tempos dados e grava em `ficheiro_saida`.

    Devolve True em caso de sucesso, False em caso de erro.
    """
    try:
        if fim_segundos <= inicio_segundos:
            return False
        if inicio_segundos < 0:
            return False

        Path(ficheiro_saida).parent.mkdir(parents=True, exist_ok=True)

        y, sr = librosa.load(ficheiro_entrada, sr=None)

        total_samples = len(y)
        inicio_samples = int(inicio_segundos * sr)
        fim_samples = min(int(fim_segundos * sr), total_samples)

        if inicio_samples >= total_samples:
            return False

        y_cortado = y[inicio_samples:fim_samples]
        if len(y_cortado) == 0:
            return False

        sf.write(ficheiro_saida, y_cortado, sr)
        return True

    except Exception as e:
        # Mantemos o print para logs locais sem mascarar problemas reais
        print(f"[corte_audio] Erro: {e}")
        return False


def obter_duracao_audio(ficheiro_entrada: str) -> float:
    """Devolve a duração em segundos. Lança se não conseguir ler."""
    return float(librosa.get_duration(path=ficheiro_entrada))


if __name__ == "__main__":
    # Smoke test manual
    ok = cortar_audio(
        "solo_blues_finalizado_2cac6c_1.mp3",
        "solo_blues_corte.wav",
        inicio_segundos=10,
        fim_segundos=40,
    )
    print("OK" if ok else "FALHOU")
