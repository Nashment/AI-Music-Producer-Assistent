"""Geração de partitura (PDF) a partir de MIDI.

Pipeline novo:
    MIDI → music21 (quantização + armadura de tonalidade + compasso)
         → MusicXML → MuseScore → PDF
    Fallback sem MuseScore: .ly gerado por template → LilyPond → PDF.

Face à versão anterior (MIDI cru → MuseScore / midi2ly):
- A quantização é controlada por nós, ao BPM real do MIDI.
- A partitura sai com armadura de tonalidade (analisada pelo music21 ou
  fornecida pela análise de áudio) em vez de acidentes em todas as notas.
- O midi2ly deixa de ser necessário.
"""

import os
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings
from worker.audio_utils.audio_to_tablature2 import (
    CAMINHO_LILYPOND,
    compilar_pdf_lilypond,
    gerar_ly_partitura,
)

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


# ---------------------------------------------------------------------------
# MIDI → MusicXML (music21)
# ---------------------------------------------------------------------------

def _tonalidade_para_music21(tonalidade):
    """'C# Maior' → music21.key.Key('C#') / 'A Menor' → Key('a')."""
    from music21 import key as m21key

    if not tonalidade or " " not in tonalidade:
        return None
    nota, modo = tonalidade.split(" ", 1)
    try:
        if modo.strip().lower().startswith("maior"):
            return m21key.Key(nota)
        return m21key.Key(nota.lower())
    except Exception:
        return None


def _midi_para_musicxml(caminho_midi, caminho_xml, tonalidade=None, compasso="4/4"):
    """Carrega o MIDI, quantiza e escreve MusicXML com armadura e compasso."""
    from music21 import converter, meter, tempo as m21tempo

    score = converter.parse(caminho_midi, quantizePost=True,
                            quarterLengthDivisors=(4, 3))

    chave = _tonalidade_para_music21(tonalidade)
    if chave is None:
        try:
            analisada = score.analyze("key")
            chave = analisada
        except Exception:
            chave = None

    for parte in score.parts:
        medidas = parte.recurse().getElementsByClass(meter.TimeSignature)
        if not medidas:
            parte.insert(0, meter.TimeSignature(compasso))
        if chave is not None:
            parte.insert(0, chave)

    # Garantir marca de metrónomo visível (o tempo vem no MIDI)
    if not score.recurse().getElementsByClass(m21tempo.MetronomeMark):
        score.insert(0, m21tempo.MetronomeMark(number=120))

    score.write("musicxml", fp=caminho_xml)
    return caminho_xml


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------

def _renderizar_com_musescore(caminho_entrada, caminho_pdf):
    """Tenta os executáveis MuseScore. Devolve (pdf | None, lista_de_erros)."""
    erros = []
    for executable in _executaveis_musescore_candidatos():
        try:
            subprocess.run(
                [executable, "-o", caminho_pdf, caminho_entrada],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if os.path.exists(caminho_pdf):
                return caminho_pdf, erros
            erros.append(f"{executable}: executou mas não gerou {caminho_pdf}")
        except FileNotFoundError:
            erros.append(f"{executable}: executável não encontrado")
        except subprocess.CalledProcessError as e:
            erros.append(f"{executable}: {(e.stderr or str(e)).strip()}")
        except Exception as e:
            erros.append(f"{executable}: {e}")
    return None, erros


def _gerar_com_lilypond(caminho_midi, caminho_pdf, tonalidade=None):
    """Fallback: partitura via template .ly + LilyPond."""
    import pretty_midi

    if not os.path.exists(CAMINHO_LILYPOND):
        return None, f"LilyPond não encontrado em: {CAMINHO_LILYPOND}"

    pdf_path = Path(caminho_pdf)
    ly_path = pdf_path.with_suffix(".ly")

    try:
        midi_data = pretty_midi.PrettyMIDI(caminho_midi)
        gerar_ly_partitura(midi_data, str(ly_path), tonalidade=tonalidade)
        compilar_pdf_lilypond(str(ly_path))

        generated_pdf = ly_path.with_suffix(".pdf")
        if generated_pdf.exists():
            if generated_pdf != pdf_path:
                generated_pdf.replace(pdf_path)
            return str(pdf_path), None
        return None, f"LilyPond executou mas não gerou PDF esperado em {generated_pdf}"
    except Exception as e:
        return None, f"Falha no fallback LilyPond: {e}"
    finally:
        ly_path.unlink(missing_ok=True)


def exportar_pdf_automatico(caminho_midi, caminho_pdf="solo_partitura.pdf",
                            tonalidade=None, compasso="4/4"):
    """Converte MIDI em partitura PDF.

    Ordem: music21 → MusicXML → MuseScore; fallback LilyPond.
    Levanta RuntimeError se nenhum caminho funcionar.
    """
    if not os.path.exists(caminho_midi):
        raise RuntimeError("Ficheiro MIDI não encontrado.")

    erros = []

    # 1) music21 → MusicXML → MuseScore (quantizado, com armadura)
    xml_tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False)
        tmp.close()
        xml_tmp = tmp.name
        _midi_para_musicxml(caminho_midi, xml_tmp, tonalidade, compasso)

        pdf, erros_ms = _renderizar_com_musescore(xml_tmp, caminho_pdf)
        erros.extend(erros_ms)
        if pdf:
            return pdf
    except Exception as e:
        erros.append(f"music21/MusicXML: {e}")
    finally:
        if xml_tmp:
            Path(xml_tmp).unlink(missing_ok=True)

    # 2) MuseScore diretamente sobre o MIDI (sem quantização nossa)
    pdf, erros_ms = _renderizar_com_musescore(caminho_midi, caminho_pdf)
    erros.extend(erros_ms)
    if pdf:
        return pdf

    # 3) Fallback LilyPond
    fallback_pdf, fallback_error = _gerar_com_lilypond(caminho_midi, caminho_pdf, tonalidade)
    if fallback_pdf:
        return fallback_pdf

    raise RuntimeError(" ; ".join(erros + ([fallback_error] if fallback_error else [])))


if __name__ == "__main__":
    try:
        resultado = exportar_pdf_automatico("teste_rapido.mid", "Partitura_Solo_Guitarra.pdf")
        print(f"Partitura gerada: {resultado}")
    except RuntimeError as e:
        print(f"Erro: {e}")
