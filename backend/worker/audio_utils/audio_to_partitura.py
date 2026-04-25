import os
import subprocess
import sys
from pathlib import Path

if os.name == "nt":
    _DEFAULT_MUSESCORE = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
    _DEFAULT_MIDI2LY = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\midi2ly.py"
    _DEFAULT_LILYPOND = r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\lilypond.exe"
else:
    _DEFAULT_MUSESCORE = "/usr/bin/mscore3"
    _DEFAULT_MIDI2LY = "/usr/bin/midi2ly"
    _DEFAULT_LILYPOND = "/usr/bin/lilypond"

CAMINHO_MUSESCORE = os.getenv("MUSESCORE_PATH", _DEFAULT_MUSESCORE)
CAMINHO_MIDI2LY = os.getenv("MIDI2LY_PATH", _DEFAULT_MIDI2LY)
CAMINHO_LILYPOND = os.getenv("LILYPOND_PATH", _DEFAULT_LILYPOND)
ULTIMO_ERRO_PARTITURA = None


def obter_ultimo_erro_partitura():
    return ULTIMO_ERRO_PARTITURA


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
    global ULTIMO_ERRO_PARTITURA
    ULTIMO_ERRO_PARTITURA = None
    print(f"A gerar PDF a partir de: {caminho_midi}")

    if not os.path.exists(caminho_midi):
        ULTIMO_ERRO_PARTITURA = "Ficheiro MIDI não encontrado."
        print(f"Erro: {ULTIMO_ERRO_PARTITURA}")
        return None

    musescore_errors = []
    for executable in _executaveis_musescore_candidatos():
        comando = [executable, "-o", caminho_pdf, caminho_midi]
        try:
            subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if os.path.exists(caminho_pdf):
                return caminho_pdf
            musescore_errors.append(f"{executable}: executou mas não gerou {caminho_pdf}")
        except FileNotFoundError:
            musescore_errors.append(f"{executable}: executável não encontrado")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            detail = stderr or stdout or str(e)
            musescore_errors.append(f"{executable}: {detail}")
        except Exception as e:
            musescore_errors.append(f"{executable}: {e}")

    fallback_pdf, fallback_error = _gerar_com_lilypond(caminho_midi, caminho_pdf)
    if fallback_pdf:
        return fallback_pdf

    ULTIMO_ERRO_PARTITURA = " ; ".join(musescore_errors + ([fallback_error] if fallback_error else []))
    print(f"Erro ao gerar PDF: {ULTIMO_ERRO_PARTITURA}")
    return None


if __name__ == "__main__":
    ficheiro_midi = "teste_rapido.mid"
    nome_do_pdf = "Partitura_Solo_Guitarra.pdf"
    resultado = exportar_pdf_automatico(ficheiro_midi, nome_do_pdf)
    if resultado:
        print("Partitura gerada com sucesso!")
        print(f"A sua partitura foi guardada automaticamente em: {resultado}")
        print("Verifique a pasta do seu projeto!")
        print("=" * 50)