import os
import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from worker.audio_utils.audio_to_tablature2 import CAMINHO_MIDI2LY, CAMINHO_LILYPOND

CAMINHO_MUSESCORE = settings.MUSESCORE_PATH

def _executaveis_musescore_candidatos():
    candidates = [CAMINHO_MUSESCORE]
    if os.name != "nt":
        candidates.extend([
            "/usr/bin/mscore3",
            "/usr/bin/musescore",
            "mscore3",
            "musescore",
        ])
    # remove duplicados preservando ordem
    return list(dict.fromkeys(candidates))


def _build_midi2ly_cmd(caminho_midi, caminho_ly):
    if CAMINHO_MIDI2LY.lower().endswith(".py"):
        return [sys.executable, CAMINHO_MIDI2LY, "-o", caminho_ly, caminho_midi]
    return [CAMINHO_MIDI2LY, "-o", caminho_ly, caminho_midi]


def _gerar_com_lilypond(caminho_midi, caminho_pdf):
    errors = []

    if not os.path.exists(CAMINHO_MIDI2LY):
        errors.append(f"midi2ly não encontrado em: {CAMINHO_MIDI2LY}")
    if not os.path.exists(CAMINHO_LILYPOND):
        errors.append(f"LilyPond não encontrado em: {CAMINHO_LILYPOND}")
    if errors:
        return None, " | ".join(errors)

    pdf_path = Path(caminho_pdf)
    ly_path = pdf_path.with_suffix(".ly")
    output_prefix = str(pdf_path.with_suffix(""))

    try:
        cmd_midi2ly = _build_midi2ly_cmd(caminho_midi, str(ly_path))
        subprocess.run(cmd_midi2ly, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        cmd_lilypond = [CAMINHO_LILYPOND, "--output", output_prefix, str(ly_path)]
        subprocess.run(cmd_lilypond, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        generated_pdf = Path(f"{output_prefix}.pdf")
        if generated_pdf.exists():
            return str(generated_pdf), None
        return None, f"LilyPond executou mas não gerou PDF esperado em {generated_pdf}"
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        detail = stderr or stdout or str(e)
        return None, f"Falha no fallback LilyPond: {detail}"
    except Exception as e:
        return None, f"Falha no fallback LilyPond: {e}"
    finally:
        if ly_path.exists():
            ly_path.unlink(missing_ok=True)


def exportar_pdf_automatico(caminho_midi, caminho_pdf="solo_partitura.pdf"):
    if not os.path.exists(caminho_midi):
        raise RuntimeError("Ficheiro MIDI não encontrado.")

    musescore_errors = []
    for executable in _executaveis_musescore_candidatos():
        try:
            subprocess.run(
                [executable, "-o", caminho_pdf, caminho_midi],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if os.path.exists(caminho_pdf):
                return caminho_pdf
            musescore_errors.append(f"{executable}: executou mas não gerou {caminho_pdf}")
        except FileNotFoundError:
            musescore_errors.append(f"{executable}: executável não encontrado")
        except subprocess.CalledProcessError as e:
            musescore_errors.append(f"{executable}: {(e.stderr or str(e)).strip()}")
        except Exception as e:
            musescore_errors.append(f"{executable}: {e}")

    fallback_pdf, fallback_error = _gerar_com_lilypond(caminho_midi, caminho_pdf)
    if fallback_pdf:
        return fallback_pdf

    raise RuntimeError(" ; ".join(musescore_errors + ([fallback_error] if fallback_error else [])))


if __name__ == "__main__":
    try:
        resultado = exportar_pdf_automatico("teste_rapido.mid", "Partitura_Solo_Guitarra.pdf")
        print(f"Partitura gerada: {resultado}")
    except RuntimeError as e:
        print(f"Erro: {e}")