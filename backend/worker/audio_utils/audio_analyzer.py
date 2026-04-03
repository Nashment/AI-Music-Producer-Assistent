import librosa
import numpy as np
from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor


def obter_templates_acordes():
    notas = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    templates = {}
    for i, nota in enumerate(notas):
        template_maior = np.zeros(12)
        template_maior[[i, (i + 4) % 12, (i + 7) % 12]] = 1
        templates[nota] = template_maior

        template_menor = np.zeros(12)
        template_menor[[i, (i + 3) % 12, (i + 7) % 12]] = 1
        templates[nota + 'm'] = template_menor
    return templates


def detetar_tom_base(chroma):
    """Detecta a tonalidade da música"""
    soma_chroma = np.sum(chroma, axis=1)
    perfil_maior = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    perfil_menor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    notas = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    melhor_correlacao = -1
    tom_detetado = ""

    for i in range(12):
        corr_maior = np.corrcoef(soma_chroma, np.roll(perfil_maior, i))[0, 1]
        if corr_maior > melhor_correlacao:
            melhor_correlacao = corr_maior
            tom_detetado = notas[i] + " Maior"

        corr_menor = np.corrcoef(soma_chroma, np.roll(perfil_menor, i))[0, 1]
        if corr_menor > melhor_correlacao:
            melhor_correlacao = corr_menor
            tom_detetado = notas[i] + " Menor"

    return tom_detetado


def ajustar_tom_pela_progressao(tom_ks, progressao):
    """Corrige modo (Maior/Menor) pela progressão de acordes"""
    if len(progressao) == 0:
        return tom_ks

    primeiro_acorde = progressao[0]
    ultimo_acorde = progressao[-1]

    notas = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    nota_tom, modo = tom_ks.split(" ")
    idx = notas.index(nota_tom)

    if modo == "Maior":
        idx_relativa = (idx - 3) % 12
        acorde_relativo_menor = notas[idx_relativa] + "m"

        if primeiro_acorde == acorde_relativo_menor or ultimo_acorde == acorde_relativo_menor:
            return notas[idx_relativa] + " Menor"

    elif modo == "Menor":
        idx_relativa = (idx + 3) % 12
        acorde_relativo_maior = notas[idx_relativa]

        if primeiro_acorde == acorde_relativo_maior or ultimo_acorde == acorde_relativo_maior:
            return notas[idx_relativa] + " Maior"

    return tom_ks


def analisar_audio_completo(caminho_wav):
    print(f"A ler o ficheiro '{caminho_wav}'...")
    y, sr = librosa.load(caminho_wav, sr=None)

    duracao = librosa.get_duration(y=y, sr=sr)

    print("A calcular os BPMs...")
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=75)
    bpm = tempo[0] if isinstance(tempo, np.ndarray) else tempo

    print("A extrair a harmonia...")
    chroma = librosa.feature.chroma_cens(y=y, sr=sr, hop_length=4096)

    templates = obter_templates_acordes()
    nomes_acordes = list(templates.keys())
    vetores_acordes = np.array(list(templates.values()))

    frames_por_segundo = sr / 4096
    tamanho_bloco = int(frames_por_segundo * 0.5)
    if tamanho_bloco == 0: tamanho_bloco = 1

    acordes_detetados = []
    for i in range(0, chroma.shape[1], tamanho_bloco):
        bloco = chroma[:, i:i + tamanho_bloco]
        if bloco.shape[1] == 0: continue
        correlacoes = [np.dot(np.mean(bloco, axis=1), t) for t in vetores_acordes]
        melhor_acorde = nomes_acordes[np.argmax(correlacoes)]
        if len(acordes_detetados) == 0 or acordes_detetados[-1] != melhor_acorde:
            acordes_detetados.append(melhor_acorde)

    tom_matematico = detetar_tom_base(chroma)
    tom_corrigido = ajustar_tom_pela_progressao(tom_matematico, acordes_detetados)

    # 2. RETORNO ALTERADO: Agora devolvemos um dicionário com tudo o que o serviço pediu
    return {
        "bpm": round(bpm),
        "key": tom_corrigido,
        "chords": acordes_detetados,
        "duration": duracao,
        "sample_rate": sr,
        # O librosa não deteta time_signature (compasso) facilmente,
        # pelo que podemos deixar None ou predefinir para "4/4"
        "time_signature": None
    }


if __name__ == "__main__":
    ficheiro = "musiquinha para a IA.wav"

    try:
        bpm_resultado, tom_resultado, progressao = analisar_audio_completo(ficheiro)
        print(f"Tom: {tom_resultado}")
        print(f"BPM: {bpm_resultado} batidas por minuto")
        print(f"Progressao: {' -> '.join(progressao)}")
    except Exception as e:
        print(f"Erro ao ler o ficheiro: {e}")