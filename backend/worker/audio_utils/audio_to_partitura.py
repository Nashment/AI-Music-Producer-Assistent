"""Geração de partitura (PDF) a partir de MIDI.

Pipeline:
    MIDI → music21 (quantização + armadura de tonalidade + compasso)
         → LilyPond (motor de renderização nativo do music21) → PDF
    Fallback: .ly gerado por template manual a partir do MIDI cru → LilyPond → PDF
    (usado apenas se o passo anterior falhar, ex.: MIDI degenerado ou falha
    interna do music21).

Não há dependência de MuseScore: o LilyPond já vem instalado na imagem do
worker e o music21 sabe exportar diretamente para ele (`score.write('lily.pdf')`),
o que evita passar por MusicXML e um segundo motor externo. A quantização e a
armadura de tonalidade calculadas pelo music21 são as que efetivamente chegam
ao PDF final, em vez de serem descartadas.
"""

import logging
import os
from pathlib import Path

from worker.audio_utils.audio_to_tablature2 import (
    CAMINHO_LILYPOND,
    gerar_ly_partitura,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MIDI → score do music21 (quantizado, com armadura e compasso)
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


def _midi_para_score(caminho_midi, tonalidade=None, compasso="4/4"):
    """Carrega o MIDI, quantiza e devolve um score do music21 já com
    armadura de tonalidade, compasso e marca de metrónomo."""
    from music21 import converter, meter, tempo as m21tempo

    score = converter.parse(caminho_midi, quantizePost=True,
                            quarterLengthDivisors=(4, 3))

    chave = _tonalidade_para_music21(tonalidade)
    if chave is None:
        try:
            chave = score.analyze("key")
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

    return score


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------

def _extrair_bpm_do_score(score):
    """Devolve o BPM (MetronomeMark) já presente no score, se existir.

    O `converter.parse` de um MIDI com tempo embutido já cria este objeto
    automaticamente (é assim que o BPM real chega até aqui) -- isto só lê
    o valor, não o insere.
    """
    from music21 import tempo as m21tempo

    marcas = score.recurse().getElementsByClass(m21tempo.MetronomeMark)
    if marcas:
        try:
            return float(marcas[0].number)
        except (TypeError, ValueError):
            return None
    return None


def _injetar_tempo_no_ly(ly_path, bpm):
    """Insere um `\\tempo` logo a seguir ao `\\time` no ficheiro .ly.

    Necessário porque o conversor LilyPond do music21 (`music21.lily.translate`)
    não traduz `MetronomeMark` -- não existe nenhuma referência a "tempo" no
    código desse módulo. Sem isto o BPM nunca aparece na partitura, por mais
    que o music21 o tenha corretamente identificado internamente.
    """
    try:
        texto = ly_path.read_text(encoding="utf-8")
        idx = texto.find("\\time ")
        if idx == -1:
            return False
        fim_linha = texto.find("\n", idx)
        if fim_linha == -1:
            fim_linha = len(texto)
        marca = f"\\tempo 4 = {int(round(bpm))}\n"
        ly_path.write_text(texto[:fim_linha + 1] + marca + texto[fim_linha + 1:], encoding="utf-8")
        return True
    except Exception as e:
        logger.warning("[partitura] Não foi possível injetar \\tempo no .ly: %s", e)
        return False


def _renderizar_com_music21_lilypond(score, caminho_pdf):
    """Renderiza o score do music21 (já quantizado, com armadura/compasso)
    diretamente para PDF usando o motor LilyPond nativo do music21.

    Devolve (pdf | None, erro | None).
    """
    if not os.path.exists(CAMINHO_LILYPOND):
        return None, f"LilyPond não encontrado em: {CAMINHO_LILYPOND}"

    from music21 import environment
    from worker.audio_utils.audio_to_tablature2 import compilar_pdf_lilypond

    # Definido apenas em memória para este processo (não persiste em disco,
    # não precisa de escrita em ~/.music21rc como o UserSettings faria).
    try:
        environment.Environment()["lilypondPath"] = CAMINHO_LILYPOND
    except Exception as e:
        return None, f"Não foi possível configurar lilypondPath no music21: {e}"

    pdf_path = Path(caminho_pdf)
    ly_path = pdf_path.with_suffix(".ly")
    bpm = _extrair_bpm_do_score(score)

    try:
        # 1) Só gerar o .ly (sem compilar) para podermos injetar o \tempo,
        #    que o music21 não escreve sozinho.
        gerado = score.write("lily", fp=str(ly_path))
        gerado_path = Path(gerado)
        if gerado_path != ly_path:
            gerado_path.replace(ly_path)

        if bpm:
            _injetar_tempo_no_ly(ly_path, bpm)

        # 2) Compilar com o LilyPond diretamente (mesmo binário, sem passar
        #    outra vez pelo wrapper do music21).
        compilar_pdf_lilypond(str(ly_path))

        generated_pdf = ly_path.with_suffix(".pdf")
        if generated_pdf.exists():
            if generated_pdf != pdf_path:
                generated_pdf.replace(pdf_path)
            return str(pdf_path), None
        return None, f"music21/LilyPond executou mas não gerou PDF em {generated_pdf}"
    except Exception as e:
        return None, f"music21/LilyPond: {e}"
    finally:
        ly_path.unlink(missing_ok=True)


def _gerar_com_lilypond(caminho_midi, caminho_pdf, tonalidade=None):
    """Fallback: partitura via template .ly manual + LilyPond, direto do MIDI
    cru (sem passar pelo music21). Usado apenas se o passo principal falhar."""
    import pretty_midi
    from worker.audio_utils.audio_to_tablature2 import compilar_pdf_lilypond

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

    Ordem: music21 (quantização + armadura) → LilyPond nativo do music21.
    Fallback: LilyPond direto sobre o MIDI cru (template manual), caso o
    passo principal falhe.
    Levanta RuntimeError se nenhum caminho funcionar.
    """
    if not os.path.exists(caminho_midi):
        raise RuntimeError("Ficheiro MIDI não encontrado.")

    erros = []

    # 1) music21 (quantizado, com armadura) → LilyPond nativo do music21
    try:
        score = _midi_para_score(caminho_midi, tonalidade, compasso)
        pdf, erro = _renderizar_com_music21_lilypond(score, caminho_pdf)
        if pdf:
            logger.info(
                "[partitura] Gerada via music21 + LilyPond (quantizada, com armadura de tonalidade): %s",
                pdf,
            )
            return pdf
        if erro:
            erros.append(erro)
    except Exception as e:
        erros.append(f"music21/LilyPond: {e}")

    logger.warning(
        "[partitura] Motor principal (music21 + LilyPond) falhou (%s); "
        "a tentar fallback LilyPond direto do MIDI cru.",
        "; ".join(erros),
    )

    # 2) Fallback: LilyPond direto sobre o MIDI cru (template manual)
    fallback_pdf, fallback_error = _gerar_com_lilypond(caminho_midi, caminho_pdf, tonalidade)
    if fallback_pdf:
        logger.info(
            "[partitura] Gerada via fallback LilyPond direto do MIDI cru (sem quantização/armadura do music21): %s",
            fallback_pdf,
        )
        return fallback_pdf

    raise RuntimeError(" ; ".join(erros + ([fallback_error] if fallback_error else [])))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        resultado = exportar_pdf_automatico("teste_rapido.mid", "Partitura_Solo_Guitarra.pdf")
        print(f"Partitura gerada: {resultado}")
    except RuntimeError as e:
        print(f"Erro: {e}")
