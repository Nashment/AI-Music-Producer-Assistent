"""Análise de áudio: BPM, tonalidade, progressão de acordes e compasso.

Melhorias face à versão anterior:
- BPM sem prior enviesado + correção de erros de oitava (dobro/metade).
- HPSS (componente harmónica) antes do chroma — a percussão deixa de
  contaminar a deteção de acordes e tonalidade.
- Chroma beat-síncrono em vez de blocos fixos de 0.75 s.
- Deteção de acordes por Viterbi (custo de transição) em vez de votação
  por bloco — elimina o "flicker" sem descartar acordes curtos.
- Estimativa simples de compasso (4/4 vs 3/4) com fallback para 4/4.
"""

import librosa
import numpy as np

NOTAS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Intervalo "musicalmente plausível" para dobrar/reduzir o BPM detetado.
_BPM_MIN, _BPM_MAX = 70.0, 180.0

# Penalização por mudar de acorde entre beats consecutivos (escala das
# correlações normalizadas, ~[0, 1]). Valores maiores = progressões mais
# estáveis; menores = mais sensível a mudanças rápidas.
_PENALIZACAO_TRANSICAO = 0.12

_SR_ANALISE = 22050
_HOP = 512


# ---------------------------------------------------------------------------
# BPM
# ---------------------------------------------------------------------------

def detetar_bpm_robusto(y: np.ndarray, sr: int) -> tuple[float, np.ndarray]:
    """Devolve (bpm, frames_de_beats).

    Corrige erros de oitava dobrando/reduzindo até [_BPM_MIN, _BPM_MAX) e
    re-estima os beats com o prior corrigido para manter a grelha coerente.
    """
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=_HOP)

    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr, hop_length=_HOP
    )
    bpm = float(np.atleast_1d(tempo)[0])
    if bpm <= 0:
        return 120.0, beats

    bpm_corrigido = bpm
    while bpm_corrigido < _BPM_MIN:
        bpm_corrigido *= 2.0
    while bpm_corrigido >= _BPM_MAX:
        bpm_corrigido /= 2.0

    if abs(bpm_corrigido - bpm) > 1e-6:
        tempo, beats = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr, hop_length=_HOP,
            start_bpm=bpm_corrigido, tightness=100,
        )
        bpm = float(np.atleast_1d(tempo)[0])

    return bpm, beats


# ---------------------------------------------------------------------------
# Acordes
# ---------------------------------------------------------------------------

def obter_templates_acordes():
    templates = {}
    for i, nota in enumerate(NOTAS):
        template_maior = np.zeros(12)
        template_maior[[i, (i + 4) % 12, (i + 7) % 12]] = 1
        templates[nota] = template_maior

        template_menor = np.zeros(12)
        template_menor[[i, (i + 3) % 12, (i + 7) % 12]] = 1
        templates[nota + 'm'] = template_menor
    return templates


def _detetar_acordes_viterbi(chroma_sync: np.ndarray) -> list[str]:
    """Sequência de acordes mais provável sobre chroma beat-síncrono.

    Programação dinâmica com custo de transição: mudar de acorde só
    compensa quando a evidência espectral o justifica.
    """
    n_frames = chroma_sync.shape[1]
    if n_frames == 0:
        return []

    templates = obter_templates_acordes()
    nomes = list(templates.keys())
    T = np.array(list(templates.values()), dtype=float)          # (24, 12)
    T = T / np.linalg.norm(T, axis=1, keepdims=True)

    C = chroma_sync.astype(float)
    normas = np.linalg.norm(C, axis=0, keepdims=True)
    normas[normas == 0] = 1.0
    C = C / normas

    emissao = T @ C                                              # (24, N)

    n_estados = len(nomes)
    custo = emissao[:, 0].copy()
    backptr = np.zeros((n_frames, n_estados), dtype=int)

    for t in range(1, n_frames):
        # ficar no mesmo estado: custo; mudar: custo - penalização
        melhor_mudanca_idx = int(np.argmax(custo))
        melhor_mudanca = custo[melhor_mudanca_idx] - _PENALIZACAO_TRANSICAO

        novo_custo = np.empty(n_estados)
        for s in range(n_estados):
            if custo[s] >= melhor_mudanca:
                novo_custo[s] = custo[s]
                backptr[t, s] = s
            else:
                novo_custo[s] = melhor_mudanca
                backptr[t, s] = melhor_mudanca_idx
        custo = novo_custo + emissao[:, t]

    # Reconstrução
    estado = int(np.argmax(custo))
    sequencia = [estado]
    for t in range(n_frames - 1, 0, -1):
        estado = backptr[t, estado]
        sequencia.append(estado)
    sequencia.reverse()

    # Colapsar repetições consecutivas
    acordes = []
    for s in sequencia:
        nome = nomes[s]
        if not acordes or acordes[-1] != nome:
            acordes.append(nome)
    return acordes


# ---------------------------------------------------------------------------
# Tonalidade
# ---------------------------------------------------------------------------

def detetar_tom_base(chroma):
    """Deteta a tonalidade por correlação com perfis de Krumhansl."""
    soma_chroma = np.sum(chroma, axis=1)
    perfil_maior = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    perfil_menor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    melhor_correlacao = -np.inf
    tom_detetado = ""

    for i in range(12):
        corr_maior = np.corrcoef(soma_chroma, np.roll(perfil_maior, i))[0, 1]
        if corr_maior > melhor_correlacao:
            melhor_correlacao = corr_maior
            tom_detetado = NOTAS[i] + " Maior"

        corr_menor = np.corrcoef(soma_chroma, np.roll(perfil_menor, i))[0, 1]
        if corr_menor > melhor_correlacao:
            melhor_correlacao = corr_menor
            tom_detetado = NOTAS[i] + " Menor"

    return tom_detetado


def ajustar_tom_pela_progressao(tom_ks, progressao):
    """Corrige o modo (Maior/Menor) com base na progressão de acordes.

    Em vez de olhar apenas para o primeiro/último acorde, conta as
    ocorrências: só troca para a relativa se o acorde da tónica detetada
    estiver ausente e o da relativa estiver presente na progressão.
    """
    if not progressao or " " not in tom_ks:
        return tom_ks

    nota_tom, modo = tom_ks.split(" ", 1)
    if nota_tom not in NOTAS:
        return tom_ks
    idx = NOTAS.index(nota_tom)

    contagem = {}
    for acorde in progressao:
        contagem[acorde] = contagem.get(acorde, 0) + 1

    if modo == "Maior":
        acorde_tonica = nota_tom
        acorde_relativa = NOTAS[(idx - 3) % 12] + "m"
        tom_relativa = NOTAS[(idx - 3) % 12] + " Menor"
    else:
        acorde_tonica = nota_tom + "m"
        acorde_relativa = NOTAS[(idx + 3) % 12]
        tom_relativa = NOTAS[(idx + 3) % 12] + " Maior"

    if contagem.get(acorde_tonica, 0) == 0 and contagem.get(acorde_relativa, 0) > 0:
        return tom_relativa
    return tom_ks


# ---------------------------------------------------------------------------
# Compasso
# ---------------------------------------------------------------------------

def _estimar_compasso(onset_env: np.ndarray, beats: np.ndarray) -> str:
    """Estimativa conservadora de compasso: 4/4 vs 3/4.

    Compara a força média dos onsets nos beats agrupados de 4 em 4 e de
    3 em 3 (todas as fases). Só devolve 3/4 com margem clara; caso
    contrário assume 4/4.
    """
    if beats is None or len(beats) < 12:
        return "4/4"

    forca = onset_env[beats[beats < len(onset_env)]]
    if len(forca) < 12:
        return "4/4"
    forca = (forca - forca.min()) / (forca.max() - forca.min() + 1e-9)

    def pontuacao(grupo: int) -> float:
        melhores = []
        for fase in range(grupo):
            acentos = forca[fase::grupo]
            outros = np.delete(forca, np.arange(fase, len(forca), grupo))
            if len(acentos) == 0 or len(outros) == 0:
                continue
            melhores.append(float(np.mean(acentos) - np.mean(outros)))
        return max(melhores) if melhores else 0.0

    p4, p3 = pontuacao(4), pontuacao(3)
    if p3 > p4 * 1.25 and p3 > 0.05:
        return "3/4"
    return "4/4"


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------

def analisar_audio_completo(caminho_wav):
    sr_original = librosa.get_samplerate(caminho_wav)
    y, sr = librosa.load(caminho_wav, sr=_SR_ANALISE, mono=True)

    duracao = float(len(y)) / sr

    bpm, beats = detetar_bpm_robusto(y, sr)

    # Componente harmónica: remove transientes percussivos do chroma
    y_harm = librosa.effects.harmonic(y)
    chroma = librosa.feature.chroma_cens(y=y_harm, sr=sr, hop_length=_HOP)

    # Chroma beat-síncrono — cada coluna corresponde a um beat
    if beats is not None and len(beats) > 1:
        chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)
    else:
        chroma_sync = chroma

    acordes_detetados = _detetar_acordes_viterbi(chroma_sync)

    tom_matematico = detetar_tom_base(chroma)
    tom_corrigido = ajustar_tom_pela_progressao(tom_matematico, acordes_detetados)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=_HOP)
    compasso = _estimar_compasso(onset_env, beats)

    return {
        "bpm": round(bpm),
        "key": tom_corrigido,
        "chords": acordes_detetados,
        "duration": duracao,
        "sample_rate": int(sr_original),
        "time_signature": compasso,
    }


if __name__ == "__main__":
    ficheiro = "musiquinha para a IA.wav"

    try:
        resultado = analisar_audio_completo(ficheiro)
        print(f"Tom: {resultado['key']}")
        print(f"BPM: {resultado['bpm']} batidas por minuto")
        print(f"Compasso: {resultado['time_signature']}")
        print(f"Progressao: {' -> '.join(resultado['chords'])}")
        print(f"Duração: {resultado['duration']:.2f}s")
    except Exception as e:
        print(f"Erro ao ler o ficheiro: {e}")
