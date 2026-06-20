"""Helpers auxiliares para construir prompts e interpretar respostas da API Suno.

A "superprompt" gerada por build_suno_prompt() é determinística e tem 3 objetivos:

1. Dar contexto musical ao Suno a partir da análise do áudio base
   (instrumento, género, BPM, tonalidade, compasso).
2. Fazer o Suno destacar o instrumento-alvo e manter uma mistura limpa e
   bem separada — isto facilita a extração posterior com o Demucs.
3. Reduzir falhas/inconsistências: ancorar a tonalidade e o modo (evita que
   palavras de humor como "triste" empurrem o Suno para menor quando o áudio
   é maior) e remover referências a artistas/expressões sensíveis que violam
   a política do Suno e fazem a geração falhar.
"""

import os
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Tabelas de tradução / heurísticas
# ---------------------------------------------------------------------------

# Instrumento (PT) -> termo em inglês (o Suno responde melhor em inglês).
_INSTRUMENTO_EN = {
    "guitarra": "electric guitar",
    "piano": "piano",
    "baixo": "bass guitar",
    "bateria": "drum kit",
    "voz": "lead vocals",
    "outros": "lead instrument",
}

# Modo PT -> EN (a nota — C, F#, … — já é igual em ambos).
_MODO_EN = {"maior": "major", "menor": "minor"}

# Palavras de humor que IMPLICAM um modo. Servem para detetar conflito com a
# tonalidade analisada e evitar que o Suno troque maior<->menor.
# Único caso removido por contradizer o tom: o utilizador escrever
# explicitamente o modo OPOSTO ao analisado (ex.: "menor" num áudio maior).
# O humor/feeling do utilizador é preservado — é a intenção criativa dele.
_MODO_OPOSTO = {"major": {"minor", "menor"}, "minor": {"major", "maior"}}

# Expressões que referenciam artistas / imitação de estilo — removidas porque
# o Suno bloqueia nomes próprios e isto induz falhas de geração.
_PADROES_ESTILO = [
    r"\bin the style of\b[^,.;:]*",
    r"\bstyle of\b[^,.;:]*",
    r"\bsounds?\s+like\b[^,.;:]*",
    r"\bà\s+la\b[^,.;:]*",
    r"\bao\s+estilo\s+d[eoa]\b[^,.;:]*",
    r"\bestilo\s+d[eoa]\b[^,.;:]*",
    r"\bno\s+estilo\s+d[eoa]\b[^,.;:]*",
    r"\bsoa\s+como\b[^,.;:]*",
    r"\binspired\s+by\b[^,.;:]*",
    r"\binspirad[oa]\s+(em|por|n[oa])\b[^,.;:]*",
]


def _carregar_blocklist() -> set:
    """Blocklist de termos a remover (nomes/sensíveis). Expansível via env
    SUNO_PROMPT_BLOCKLIST (separado por vírgulas)."""
    base = set()
    extra = os.getenv("SUNO_PROMPT_BLOCKLIST", "")
    for termo in extra.split(","):
        t = termo.strip().lower()
        if t:
            base.add(t)
    return base


# ---------------------------------------------------------------------------
# Sanitização
# ---------------------------------------------------------------------------

def _parse_tonalidade(key: Optional[str]):
    """'C Maior' -> ('C', 'major'); 'F# Menor' -> ('F#', 'minor'). Caso contrário (None, None)."""
    if not key or not isinstance(key, str) or " " not in key.strip():
        return None, None
    nota, modo = key.strip().split(" ", 1)
    modo_en = _MODO_EN.get(modo.strip().lower())
    return (nota, modo_en) if modo_en else (nota, None)


def _remover_palavras(texto: str, palavras: set, prefixo: bool = False) -> str:
    """Remove palavras do texto (case-insensitive, Unicode).

    prefixo=True trata cada termo como raiz e remove a palavra inteira que
    começa por essa raiz (ex.: 'melancólic' -> 'melancólica', 'melancólicos').
    """
    if not palavras:
        return texto
    for p in palavras:
        if prefixo:
            texto = re.sub(rf"(?<!\w){re.escape(p)}\w*", "", texto, flags=re.IGNORECASE)
        else:
            texto = re.sub(rf"(?<!\w){re.escape(p)}(?!\w)", "", texto, flags=re.IGNORECASE)
    return texto


def _limpar_residuos(texto: str) -> str:
    """Colapsa espaços/vírgulas e remove conjunções soltas deixadas pelas remoções."""
    texto = re.sub(r"\s+", " ", texto)
    chunks = []
    for c in texto.split(","):
        c = c.strip()
        c = re.sub(r"^(e|and|ou|or)\b\s*", "", c, flags=re.IGNORECASE)   # conjunção no início
        c = re.sub(r"\s*\b(e|and|ou|or|like|feat|ft|by|com|with)$", "", c, flags=re.IGNORECASE)  # conector solto no fim
        c = c.strip(" .;:-")
        if c:
            chunks.append(c)
    return ", ".join(chunks)


def _sanitizar_descricao(prompt: str, modo_en: Optional[str], blocklist: set) -> str:
    """Limpa a descrição do utilizador:
      - remove frases de imitação de estilo / nomes de artistas;
      - remove termos da blocklist;
      - remove palavras de humor que contradizem o modo analisado.
    """
    texto = prompt or ""

    # 1) frases "estilo de X" / "like X" / "inspired by X"
    for padrao in _PADROES_ESTILO:
        texto = re.sub(padrao, " ", texto, flags=re.IGNORECASE)

    # 2) blocklist de nomes/sensíveis
    texto = _remover_palavras(texto, blocklist)

    # 3) só removemos uma contradição EXPLÍCITA de modo (ex.: o utilizador
    #    escreve "menor" mas o áudio é maior). O feeling, estilos e técnicas
    #    (rock, flamenco, valsa, bends, arpejos…) são SEMPRE preservados.
    if modo_en in _MODO_OPOSTO:
        texto = _remover_palavras(texto, _MODO_OPOSTO[modo_en])

    # 4) limpeza de resíduos (conjunções soltas, vírgulas/espaços)
    return _limpar_residuos(texto)


# ---------------------------------------------------------------------------
# Construção da superprompt
# ---------------------------------------------------------------------------

def build_suno_prompt(prompt: str, instrument: str, genre: Optional[str], audio, tempo_override: Optional[int]) -> str:
    """Constroi o campo de estilo para a API Suno (determinístico).

    Estrutura: identidade sonora (instrumento + género) -> contexto musical
    (BPM, tonalidade, compasso) -> ênfase no instrumento p/ separação ->
    descrição (sanitizada) do utilizador -> âncora explícita da tonalidade.
    """
    inst_pt = (instrument or "").lower().strip()
    inst_en = _INSTRUMENTO_EN.get(inst_pt, inst_pt or "lead instrument")

    bpm = tempo_override or getattr(audio, "bpm", None)
    key = getattr(audio, "key", None)
    time_sig = getattr(audio, "time_signature", None)
    nota, modo_en = _parse_tonalidade(key)

    blocklist = _carregar_blocklist()
    descricao = _sanitizar_descricao(prompt, modo_en, blocklist)

    partes = [f"solo {inst_en}"]
    if genre:
        partes.append(str(genre))
    if bpm:
        partes.append(f"{int(bpm)} BPM")
    if nota and modo_en:
        partes.append(f"in the key of {nota} {modo_en}")
    elif nota:
        partes.append(f"in {nota}")
    if time_sig:
        partes.append(f"{time_sig} time signature")

    # Ênfase ligeira para ajudar a extração com o Demucs, sem sufocar o feeling:
    partes.append(
        f"{inst_en} clearly in the foreground and well separated "
        "from the other instruments, clean mix"
    )
    partes.append("professional studio quality")

    if descricao:
        partes.append(descricao)

    estilo = ", ".join(p for p in partes if p)

    # Âncora final imperativa da tonalidade/modo (reduz troca maior<->menor).
    if nota and modo_en:
        estilo += (
            f". Keep strictly in the key of {nota} {modo_en} (do not change key or mode); "
            "convey the mood through phrasing, dynamics and tempo, not by changing the key."
        )

    return estilo


# ---------------------------------------------------------------------------
# Interpretação das respostas da API Suno
# ---------------------------------------------------------------------------

def extract_suno_audio_url(payload: dict) -> Optional[str]:
    """Extrai o URL de audio da resposta da API Suno.

    Estrutura documentada: payload["data"]["response"]["sunoData"][n]["audioUrl"]
    Fallback para streamAudioUrl se audioUrl estiver ausente.
    """
    try:
        suno_data = payload["data"]["response"]["sunoData"]
        for item in suno_data:
            url = item.get("audioUrl") or item.get("streamAudioUrl")
            if isinstance(url, str) and url.strip().startswith(("http://", "https://")):
                return url.strip()
    except (KeyError, TypeError):
        return None
    return None


def extract_suno_task_status(payload: dict) -> Optional[str]:
    try:
        return payload["data"]["status"].strip().lower()
    except (KeyError, AttributeError):
        return None
