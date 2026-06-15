"""Separação de faixas com Demucs.

Melhorias face à versão anterior:
- O Demucs escreve num diretório temporário próprio (`-o`) em vez de
  `./separated` relativo ao cwd do worker — duas tasks concorrentes
  deixavam de se corromper mutuamente e a limpeza é automática.
"""

import os
import shutil
import subprocess
import sys
import tempfile

MAPA_INSTRUMENTOS = {
    "bateria": "drums.wav",
    "baixo": "bass.wav",
    "piano": "piano.wav",
    "guitarra": "guitar.wav",
    "voz": "vocals.wav",
    "outros": "other.wav",
}

_MODELO_DEMUCS = "htdemucs_6s"


def extrair_instrumento(caminho_audio, instrumento_desejado, output_dir=None):
    instrumento_formatado = instrumento_desejado.lower().strip()

    if instrumento_formatado not in MAPA_INSTRUMENTOS:
        raise ValueError(
            f"Instrumento '{instrumento_desejado}' não suportado. "
            f"Escolhe um destes: {', '.join(MAPA_INSTRUMENTOS.keys())}"
        )

    if not os.path.exists(caminho_audio):
        raise FileNotFoundError(f"Ficheiro '{caminho_audio}' não encontrado.")

    nome_ficheiro_demucs = MAPA_INSTRUMENTOS[instrumento_formatado]
    nome_base_musica = os.path.splitext(os.path.basename(caminho_audio))[0]
    destino_dir = output_dir if output_dir else os.getcwd()

    with tempfile.TemporaryDirectory(prefix="demucs_") as tmp_dir:
        comando = [
            sys.executable, "-m", "demucs",
            "-n", _MODELO_DEMUCS,
            "--device", "cpu",
            "-o", tmp_dir,
            caminho_audio,
        ]

        try:
            result = subprocess.run(comando, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Erro ao correr o Demucs: {e.stderr if e.stderr else str(e)}"
            ) from e

        caminho_ficheiro_isolado = os.path.join(
            tmp_dir, _MODELO_DEMUCS, nome_base_musica, nome_ficheiro_demucs
        )
        novo_nome_ficheiro = os.path.join(
            destino_dir, f"{nome_base_musica}_{instrumento_formatado}.wav"
        )

        if not os.path.exists(caminho_ficheiro_isolado):
            raise RuntimeError(
                f"O Demucs não gerou o ficheiro esperado '{nome_ficheiro_demucs}'. "
                f"Stderr: {result.stderr[:500] if result.stderr else 'sem output'}"
            )

        os.makedirs(destino_dir, exist_ok=True)
        shutil.move(caminho_ficheiro_isolado, novo_nome_ficheiro)

    return novo_nome_ficheiro


if __name__ == "__main__":
    ficheiro_musica = "solo_blues_finalizado_cac6c_1.mp3"
    instrumento_escolhido = "guitarra"
    print(extrair_instrumento(ficheiro_musica, instrumento_escolhido))
