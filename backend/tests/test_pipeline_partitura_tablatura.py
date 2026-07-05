r"""
test_pipeline_partitura_tablatura.py
=====================================
Teste manual/integração do pipeline completo:

    áudio (ficheiro local OU chave no storage/Cloudflare R2)
        -> extração de MIDI (Basic Pitch)
        -> partitura PDF (music21 + LilyPond, fallback LilyPond direto do MIDI)
        -> tablatura PDF (eventos + otimização de dedilhado + LilyPond)

Este ficheiro existe para testares manualmente se a extração de MIDI e a
geração de partitura/tablatura estão corretas para um áudio real, sem teres
de correr uma geração completa via Celery/Suno.

Como usar
---------
Edita as constantes na secção "CONFIGURAÇÃO DO TESTE" mais abaixo:

    AUDIO_PATH : caminho local para o ficheiro de áudio (wav/mp3/flac/...),
                 OU None se quiseres usar AUDIO_S3_KEY.
    AUDIO_S3_KEY : key no bucket Cloudflare/S3 (usa o StorageService já
                 configurado na app). Só é usado se AUDIO_PATH for None.
    BPM : BPM a forçar, ou None para deteção automática.
    TOM : tonalidade a forçar (ex: "D Maior" / "C Menor"), ou None para
          deteção automática.

Depois corre:
    pytest backend/tests/test_pipeline_partitura_tablatura.py -v -m integration -s

Resultados
----------
Os ficheiros gerados (midi, partitura PDF, tablatura PDF) ficam em:
    backend/tests/output_pipeline/<nome>.mid
    backend/tests/output_pipeline/<nome>_partitura.pdf
    backend/tests/output_pipeline/<nome>_tablatura.pdf

para poderes abrir e ouvir/ver o resultado.
"""

import os
import sys
import shutil

import pytest

# ---------------------------------------------------------------------------
# Garantir que o PYTHONPATH inclui a raiz do backend
# ---------------------------------------------------------------------------
TESTS_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from worker.audio_utils.audio_extractor import extrair_midi_do_audio
    from worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
    from worker.audio_utils.audio_to_tablature2 import (
        extrair_eventos,
        otimizar_tablatura,
        gerar_ly_tablatura,
        compilar_pdf_lilypond,
    )
except ImportError as e:
    # Este ficheiro testa o pipeline completo (áudio -> MIDI -> PDF), que
    # depende das bibliotecas pesadas do worker (basic-pitch, torch, etc. --
    # ver docker/requirements-worker.txt), não apenas das da API. Se alguém
    # correr a suite só com as dependências da API instaladas, salta este
    # módulo com um motivo claro em vez de rebentar a recolha de testes
    # inteira com um ModuleNotFoundError.
    pytest.skip(
        f"Dependências do worker em falta para este teste de pipeline: {e}",
        allow_module_level=True,
    )

OUTPUT_DIR = os.path.join(TESTS_DIR, "output_pipeline")


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DO TESTE -- edita estes valores
# ---------------------------------------------------------------------------

# Caminho local para o áudio a testar (usa raw string r"..." no Windows).
# Se ficar None, usa-se AUDIO_S3_KEY em vez disso.
AUDIO_PATH: str | None = "/app/tests/Monday at 21.08.wav"

# Alternativa: key do ficheiro no bucket Cloudflare/S3 (só usada se AUDIO_PATH for None)
AUDIO_S3_KEY: str | None = None

# Parâmetros opcionais da música. None => deteção automática.
BPM: float | None = 88         # ex: 96
TOM: str | None = "C Maior"            # ex: "D Maior" / "C Menor"


# ---------------------------------------------------------------------------
# Função principal do pipeline (reutilizável)
# ---------------------------------------------------------------------------

def gerar_partitura_e_tablatura(
    caminho_audio: str,
    nome_saida: str,
    bpm: float | None = None,
    tonalidade: str | None = None,
    compasso: str = "4/4",
) -> dict:
    """Corre o pipeline completo de notação para um ficheiro de áudio.

    Parâmetros
    ----------
    caminho_audio : caminho local para o ficheiro de áudio (wav/mp3/...).
    nome_saida    : prefixo dos ficheiros gerados (sem extensão).
    bpm           : BPM a usar (se None, é detetado automaticamente).
    tonalidade    : ex. "D Maior" / "B Menor" (se None, music21 tenta analisar).
    compasso      : assinatura de tempo, ex. "4/4".

    Devolve um dict com os caminhos gerados:
        {
            "midi": "<...>.mid",
            "partitura_pdf": "<...>_partitura.pdf" | None,
            "tablatura_pdf": "<...>_tablatura.pdf" | None,
            "erros": [...]  # mensagens de erro não fatais
        }
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    midi_path      = os.path.join(OUTPUT_DIR, f"{nome_saida}.mid")
    partitura_pdf  = os.path.join(OUTPUT_DIR, f"{nome_saida}_partitura.pdf")
    tablatura_pdf  = os.path.join(OUTPUT_DIR, f"{nome_saida}_tablatura.pdf")

    resultado = {
        "midi": None,
        "partitura_pdf": None,
        "tablatura_pdf": None,
        "erros": [],
    }

    # 1) Áudio -> MIDI -----------------------------------------------------
    midi_data = extrair_midi_do_audio(caminho_audio, midi_path, bpm=bpm)
    resultado["midi"] = midi_path

    # 2) MIDI -> Partitura PDF ----------------------------------------------
    try:
        pdf_gerado = exportar_pdf_automatico(
            midi_path, partitura_pdf, tonalidade=tonalidade, compasso=compasso,
        )
        if pdf_gerado and os.path.exists(pdf_gerado):
            resultado["partitura_pdf"] = pdf_gerado
    except RuntimeError as e:
        resultado["erros"].append(f"partitura: {e}")

    # 3) MIDI -> Tablatura PDF -----------------------------------------------
    try:
        eventos = extrair_eventos(midi_data)
        dedilhado = otimizar_tablatura([p for _, _, p in eventos]) if eventos else None

        ly_path = os.path.join(OUTPUT_DIR, f"{nome_saida}.ly")
        gerar_ly_tablatura(midi_data, dedilhado, ly_path, bpm=bpm, tonalidade=tonalidade, compasso=compasso)

        try:
            compilar_pdf_lilypond(ly_path)
        except RuntimeError:
            # fallback sem dedilhado otimizado (LilyPond escolhe as cordas)
            os.remove(ly_path)
            gerar_ly_tablatura(midi_data, None, ly_path, bpm=bpm, tonalidade=tonalidade, compasso=compasso)
            compilar_pdf_lilypond(ly_path)

        ly_pdf_gerado = os.path.splitext(ly_path)[0] + ".pdf"
        if os.path.exists(ly_pdf_gerado):
            if ly_pdf_gerado != tablatura_pdf:
                shutil.move(ly_pdf_gerado, tablatura_pdf)
            resultado["tablatura_pdf"] = tablatura_pdf

        if os.path.exists(ly_path):
            os.remove(ly_path)
    except Exception as e:
        resultado["erros"].append(f"tablatura: {e}")

    return resultado


# ---------------------------------------------------------------------------
# Resolução do áudio de teste (local ou Cloudflare/S3)
# ---------------------------------------------------------------------------

def _resolver_audio_teste():
    """Devolve (caminho_audio, ctx_temp) ou None se não estiver configurado.

    `ctx_temp` é o context manager de `temp_download` quando se usa
    AUDIO_S3_KEY (para limpar o ficheiro temporário no final), ou None
    quando se usa AUDIO_PATH (ficheiro local, não é apagado).
    """
    if AUDIO_PATH:
        if not os.path.exists(AUDIO_PATH):
            pytest.skip(f"AUDIO_PATH definido mas o ficheiro não existe: {AUDIO_PATH}")
        return AUDIO_PATH, None

    if AUDIO_S3_KEY:
        from app.services.storage_service import storage

        suffix = os.path.splitext(AUDIO_S3_KEY)[1] or ".wav"
        ctx = storage.temp_download(AUDIO_S3_KEY, suffix=suffix)
        tmp_path = ctx.__enter__()
        if tmp_path is None:
            ctx.__exit__(None, None, None)
            pytest.skip(f"Não foi possível descarregar AUDIO_S3_KEY do storage: {AUDIO_S3_KEY}")
        return str(tmp_path), ctx

    return None


# ---------------------------------------------------------------------------
# Teste
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_pipeline_audio_real_gera_partitura_e_tablatura():
    """
    Corre o pipeline completo (MIDI -> partitura -> tablatura) sobre um
    áudio real e verifica que pelo menos um dos PDFs foi gerado.

    Requer AUDIO_PATH ou AUDIO_S3_KEY configurados no topo do ficheiro.
    Caso contrário o teste é saltado.
    """
    audio_info = _resolver_audio_teste()
    if audio_info is None:
        pytest.skip(
            "Define AUDIO_PATH (ficheiro local) ou AUDIO_S3_KEY "
            "(chave no storage Cloudflare) no topo do ficheiro para correr este teste."
        )

    caminho_audio, ctx_temp = audio_info
    try:
        resultado = gerar_partitura_e_tablatura(
            caminho_audio=caminho_audio,
            nome_saida="audio_real",
            bpm=BPM,
            tonalidade=TOM,
        )

        print("\nResultado do pipeline:")
        print(f"  MIDI:      {resultado['midi']}")
        print(f"  Partitura: {resultado['partitura_pdf']}")
        print(f"  Tablatura: {resultado['tablatura_pdf']}")
        if resultado["erros"]:
            print(f"  Erros (não fatais): {resultado['erros']}")

        assert os.path.exists(resultado["midi"]), "MIDI não foi gerado."
        assert resultado["partitura_pdf"] or resultado["tablatura_pdf"], (
            f"Nem partitura nem tablatura foram geradas. Erros: {resultado['erros']}"
        )
    finally:
        if ctx_temp is not None:
            # ctx_temp é o context manager de temp_download -- limpa o ficheiro temporário
            ctx_temp.__exit__(None, None, None)
