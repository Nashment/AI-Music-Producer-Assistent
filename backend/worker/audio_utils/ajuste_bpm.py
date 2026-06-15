"""Ajuste de BPM por time-stretch.

Melhorias face à versão anterior:
- Erros deixam de ser engolidos (levanta RuntimeError) — a task que chama
  já faz o try/except e regista o erro no resumo.
- Usa a deteção de BPM robusta (correção de oitava) — antes, um erro de
  dobro/metade no BPM detetado deformava gravemente o áudio.
- Devolve um dicionário com o que foi feito. Só escreve `ficheiro_saida`
  se houver ajuste (contrato esperado pelas tasks: `caminho.exists()`).
"""

import librosa
import soundfile as sf

from worker.audio_utils.audio_analyzer import detetar_bpm_robusto

LIMIAR_BPM = 1.0


def ajustar_bpm_automatico(ficheiro_entrada, ficheiro_saida, bpm_alvo=70.0) -> dict:
    try:
        y, sr = librosa.load(ficheiro_entrada, sr=None)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar o ficheiro '{ficheiro_entrada}': {e}") from e

    bpm_atual, _ = detetar_bpm_robusto(y, sr)

    if abs(bpm_atual - bpm_alvo) < LIMIAR_BPM:
        return {"bpm_detetado": bpm_atual, "ajustado": False, "ficheiro_saida": None}

    taxa_ajuste = bpm_alvo / bpm_atual
    try:
        y_ajustado = librosa.effects.time_stretch(y, rate=taxa_ajuste)
        sf.write(ficheiro_saida, y_ajustado, sr)
    except Exception as e:
        raise RuntimeError(f"Falha no time-stretch para {bpm_alvo} BPM: {e}") from e

    return {"bpm_detetado": bpm_atual, "ajustado": True, "ficheiro_saida": ficheiro_saida}


if __name__ == "__main__":
    resultado = ajustar_bpm_automatico(
        "solo_blues_finalizado_2cac6c_1.mp3",
        "solo_blues_70BPM_perfeito.wav",
        bpm_alvo=70.0,
    )
    print(resultado)
