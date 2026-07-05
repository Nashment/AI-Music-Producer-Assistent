"""
test_tablatura_do_maior.py
==========================
Testes unitários e de integração para o motor de tablatura de guitarra.

Cenário: Escala de Dó Maior a subir (C4→C5) e a descer (C5→C4).

PDFs gerados nesta mesma pasta:
  do_maior_com_otimizacao.pdf  — pipeline com algoritmo de otimização biomecânica
  do_maior_sem_otimizacao.pdf  — pipeline base (sem otimização)

Executar todos os testes:
    pytest backend/tests/test_tablatura_do_maior.py -v

Executar só os unitários (sem LilyPond):
    pytest backend/tests/test_tablatura_do_maior.py -v -m "not integration"

Executar só a geração de PDFs:
    pytest backend/tests/test_tablatura_do_maior.py -v -m integration
"""

import os
import sys
import shutil
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Garantir que o PYTHONPATH inclui a raiz do backend
# ---------------------------------------------------------------------------
TESTS_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    import pretty_midi
    from worker.audio_utils.audio_to_tablature2 import (
        AFINACAO_GUITARRA,
        MAX_TRASTES,
        CAMINHO_LILYPOND,
        obter_posicoes_possiveis,
        calcular_custo_biomecanico,
        otimizar_tablatura,
        extrair_eventos,
        extrair_lista_notas,
        gerar_ly_tablatura,
        compilar_pdf_lilypond,
    )
except ImportError as e:
    # `pretty_midi` (+ mido, sua dependência) é uma biblioteca do worker,
    # não da API -- não vem em requirements-api.txt. Se a suite for corrida
    # só com as dependências da API instaladas, salta este módulo com um
    # motivo claro em vez de rebentar a recolha de testes inteira.
    pytest.skip(f"Dependência do worker em falta: {e}", allow_module_level=True)

# ---------------------------------------------------------------------------
# Escala de Dó Maior em 2 oitavas (C3 = 48)
# ---------------------------------------------------------------------------
DO_MAIOR_SUBIR = [
    48, 50, 52, 53, 55, 57, 59,   # C3 D3 E3 F3 G3 A3 B3
    60, 62, 64, 65, 67, 69, 71,   # C4 D4 E4 F4 G4 A4 B4
    72,                            # C5
]
DO_MAIOR_DESCER = [
    72,                            # C5
    71, 69, 67, 65, 64, 62, 60,   # B4 A4 G4 F4 E4 D4 C4
    59, 57, 55, 53, 52, 50, 48,   # B3 A3 G3 F3 E3 D3 C3
]
# Sobe até C5 e desce de volta — C5 partilhado no ponto de viragem (29 notas)
DO_MAIOR_COMPLETO = DO_MAIOR_SUBIR + DO_MAIOR_DESCER[1:]


# ---------------------------------------------------------------------------
# Utilitário: criar PrettyMIDI a partir de uma lista de notas MIDI
# ---------------------------------------------------------------------------

def criar_midi(notas_midi: list, bpm: int = 80) -> pretty_midi.PrettyMIDI:
    """
    Constrói um objeto PrettyMIDI com as notas fornecidas em semínimas
    a tempo constante. Usa o programa 25 (Acoustic Guitar Nylon).
    Cada item pode ser um pitch (int) ou uma lista de pitches (acorde).
    """
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    instrumento = pretty_midi.Instrument(program=25)
    duracao = 60.0 / bpm                 # duração de uma semínima em segundos

    for i, item in enumerate(notas_midi):
        pitches = [item] if isinstance(item, int) else list(item)
        for pitch in pitches:
            instrumento.notes.append(pretty_midi.Note(
                velocity=80,
                pitch=pitch,
                start=i * duracao,
                end=(i + 0.9) * duracao,  # ligeiro staccato para clareza
            ))

    pm.instruments.append(instrumento)
    return pm


# ===========================================================================
# TESTES UNITÁRIOS
# Testam as funções puras do algoritmo — sem LilyPond, sem ficheiros externos.
# ===========================================================================

class TestObterPosicoesPossiveis:
    """Verifica o mapeamento nota MIDI → lista de posições (corda, traste, dedo)."""

    def test_nota_playavel_tem_posicoes(self):
        """C4 (MIDI 60) deve ter pelo menos uma posição na guitarra standard."""
        assert len(obter_posicoes_possiveis(60)) > 0

    def test_nota_sub_grave_sem_posicoes(self):
        """MIDI 10 (sub-grave) está fora do alcance de qualquer guitarra standard."""
        assert obter_posicoes_possiveis(10) == []

    def test_corda_solta_tem_dedo_zero(self):
        """
        E4 (MIDI 64) é a corda 1 solta.
        A posição correspondente deve ter traste=0 e dedo=0.
        """
        posicoes = obter_posicoes_possiveis(64)
        soltas = [(c, t, d) for c, t, d in posicoes if t == 0]
        assert len(soltas) > 0, "Deve existir a posição de corda solta"
        assert all(d == 0 for _, _, d in soltas), "Corda solta deve ter dedo=0"

    def test_todas_as_notas_da_escala_tem_posicoes(self):
        """Cada nota da escala de Dó Maior deve ser tocável na guitarra."""
        for nota in DO_MAIOR_COMPLETO:
            posicoes = obter_posicoes_possiveis(nota)
            assert len(posicoes) > 0, f"MIDI {nota} não tem posições na guitarra"

    def test_posicoes_dentro_dos_limites_fisicos(self):
        """Todas as posições devem respeitar os limites de corda e traste."""
        for nota in DO_MAIOR_COMPLETO:
            for corda, traste, dedo in obter_posicoes_possiveis(nota):
                assert 1 <= corda <= 6,          f"Corda inválida: {corda}"
                assert 0 <= traste <= MAX_TRASTES, f"Traste inválido: {traste}"
                assert 0 <= dedo <= 4,            f"Dedo inválido: {dedo}"

    def test_posicao_na_corda_correta(self):
        """
        Para cada corda, a nota resultante de (base_midi + traste) deve
        coincidir com a nota pedida.
        """
        for nota_midi in DO_MAIOR_COMPLETO:
            for corda, traste, _ in obter_posicoes_possiveis(nota_midi):
                assert AFINACAO_GUITARRA[corda] + traste == nota_midi


class TestCalcularCustoBiomecanico:
    """Verifica a função de custo entre dois estados consecutivos."""

    def test_custo_e_nao_negativo(self):
        assert calcular_custo_biomecanico((3, 5, 1), (3, 7, 3)) >= 0

    def test_mesma_corda_custo_menor_que_mudar_de_corda(self):
        """
        Mudar de corda deve ser mais caro do que ficar na mesma corda.
        A penalização é de 2.0 por corda de distância.
        """
        custo_mesmo = calcular_custo_biomecanico((3, 5, 1), (3, 7, 2))
        custo_outro  = calcular_custo_biomecanico((3, 5, 1), (1, 7, 2))
        assert custo_mesmo < custo_outro

    def test_dedo_errado_ao_subir_penalizado(self):
        """
        Ao subir nos trastes, vir do dedo 4 deve ser muito penalizado
        (obrigaria a dobrar a mão para trás) — custo ≥ 50.
        """
        custo_penalizado = calcular_custo_biomecanico((3, 5, 4), (3, 8, 1))
        custo_normal     = calcular_custo_biomecanico((3, 5, 1), (3, 8, 3))
        assert custo_penalizado > custo_normal
        assert custo_penalizado >= 50.0

    def test_dedo_errado_ao_descer_penalizado(self):
        """
        Ao descer nos trastes, vir do dedo 1 deve ser muito penalizado — custo ≥ 50.
        """
        custo_penalizado = calcular_custo_biomecanico((3, 8, 1), (3, 5, 4))
        custo_normal     = calcular_custo_biomecanico((3, 8, 3), (3, 5, 1))
        assert custo_penalizado > custo_normal
        assert custo_penalizado >= 50.0

    def test_corda_solta_tem_penalizacao_adicional(self):
        """
        Qualquer transição com corda solta (traste=0) deve ter custo
        superior a uma transição equivalente sem cordas soltas.
        """
        custo_solta  = calcular_custo_biomecanico((3, 0, 0), (3, 5, 2))
        custo_normal = calcular_custo_biomecanico((3, 3, 2), (3, 5, 3))
        assert custo_solta > custo_normal

    def test_stretch_aumenta_custo(self):
        """
        Quanto maior o desalinhamento entre distância de trastes e dedos,
        maior o custo (penalização de abertura da mão).
        """
        custo_normal  = calcular_custo_biomecanico((3, 5, 1), (3, 6, 2))  # stretch=0
        custo_stretch = calcular_custo_biomecanico((3, 5, 1), (3, 9, 2))  # stretch alto
        assert custo_stretch > custo_normal


class TestOtimizarTablatura:
    """Verifica o algoritmo de programação dinâmica (Viterbi com backpointers)."""

    def test_comprimento_resultado_igual_ao_input(self):
        resultado = otimizar_tablatura(DO_MAIOR_SUBIR)
        assert len(resultado) == len(DO_MAIOR_SUBIR)

    def test_cada_estado_tem_formato_valido(self):
        resultado = otimizar_tablatura(DO_MAIOR_SUBIR)
        for corda, traste, dedo in resultado:
            assert 1 <= corda <= 6
            assert 0 <= traste <= MAX_TRASTES
            assert 0 <= dedo <= 4

    def test_escala_completa_retorna_resultado(self):
        resultado = otimizar_tablatura(DO_MAIOR_COMPLETO)
        assert resultado is not None
        assert len(resultado) == len(DO_MAIOR_COMPLETO)

    def test_lista_vazia_retorna_lista_vazia(self):
        assert otimizar_tablatura([]) == []

    def test_nota_invalida_retorna_none(self):
        """
        MIDI 5 não existe em nenhuma guitarra standard.
        O algoritmo deve sinalizar isso devolvendo None.
        """
        resultado = otimizar_tablatura([60, 5, 64])
        assert resultado is None

    def test_posicoes_resultantes_tocam_as_notas_corretas(self):
        """
        Cada (corda, traste) do resultado deve corresponder
        exatamente à nota MIDI pedida.
        """
        resultado = otimizar_tablatura(DO_MAIOR_COMPLETO)
        for (corda, traste, _), nota_midi in zip(resultado, DO_MAIOR_COMPLETO):
            assert AFINACAO_GUITARRA[corda] + traste == nota_midi, (
                f"Posição ({corda},{traste}) não toca a nota MIDI {nota_midi}"
            )

    def test_custo_otimizado_menor_ou_igual_ao_naive(self):
        """
        O caminho calculado pelo algoritmo deve ter custo total menor ou igual
        ao de uma estratégia gulosa (sempre usar a primeira posição disponível).
        """
        resultado = otimizar_tablatura(DO_MAIOR_SUBIR)

        custo_otimizado = sum(
            calcular_custo_biomecanico(resultado[i], resultado[i + 1])
            for i in range(len(resultado) - 1)
        )

        # Estratégia naive: sempre usar a primeira posição disponível
        naive = [obter_posicoes_possiveis(n)[0] for n in DO_MAIOR_SUBIR]
        custo_naive = sum(
            calcular_custo_biomecanico(naive[i], naive[i + 1])
            for i in range(len(naive) - 1)
        )

        assert custo_otimizado <= custo_naive, (
            f"Algoritmo deveria ser ≤ naive: "
            f"otimizado={custo_otimizado:.2f}, naive={custo_naive:.2f}"
        )

    def test_subir_e_descer_produzem_resultados_distintos(self):
        """
        A escala a subir e a descer são sequências diferentes e
        devem produzir dedilhados globalmente diferentes.
        """
        subir  = otimizar_tablatura(DO_MAIOR_SUBIR)
        descer = otimizar_tablatura(DO_MAIOR_DESCER)
        assert subir != descer

    # ------------------------------------------------------------------
    # Acordes (novo na versão com eventos)
    # ------------------------------------------------------------------

    def test_acorde_usa_cordas_distintas(self):
        """Um acorde de Dó (C3+E3+G3) deve usar três cordas diferentes."""
        resultado = otimizar_tablatura([[48, 52, 55]])
        assert resultado is not None
        posicoes = resultado[0]
        assert len(posicoes) == 3
        cordas = [c for c, _, _ in posicoes]
        assert len(set(cordas)) == 3

    def test_acorde_toca_as_notas_corretas(self):
        resultado = otimizar_tablatura([[48, 52, 55]])
        notas_tocadas = sorted(
            AFINACAO_GUITARRA[c] + t for c, t, _ in resultado[0]
        )
        assert notas_tocadas == [48, 52, 55]

    def test_acorde_abertura_limitada(self):
        """Os trastes pisados de um acorde não podem abrir mais de 4 casas."""
        resultado = otimizar_tablatura([[48, 52, 55], [50, 53, 57]])
        for posicoes in resultado:
            pisados = [t for _, t, _ in posicoes if t > 0]
            if pisados:
                assert max(pisados) - min(pisados) <= 4

    def test_mistura_notas_e_acordes(self):
        sequencia = [60, [48, 52, 55], 64]
        resultado = otimizar_tablatura(sequencia)
        assert resultado is not None
        assert len(resultado) == 3
        assert isinstance(resultado[0], tuple) and isinstance(resultado[0][0], int)
        assert isinstance(resultado[1][0], tuple)   # acorde → tuplo de posições


class TestExtrairEventos:
    """Verifica o agrupamento de notas MIDI em eventos (notas/acordes)."""

    def test_notas_sequenciais_geram_eventos_individuais(self):
        pm = criar_midi(DO_MAIOR_SUBIR)
        eventos = extrair_eventos(pm)
        assert len(eventos) == len(DO_MAIOR_SUBIR)
        assert [p for _, _, ps in eventos for p in ps] == DO_MAIOR_SUBIR

    def test_notas_simultaneas_agrupadas_em_acorde(self):
        pm = criar_midi([[48, 52, 55], 60])
        eventos = extrair_eventos(pm)
        assert len(eventos) == 2
        assert eventos[0][2] == [48, 52, 55]
        assert eventos[1][2] == [60]

    def test_extrair_lista_notas_compatibilidade(self):
        pm = criar_midi(DO_MAIOR_COMPLETO)
        assert extrair_lista_notas(pm) == DO_MAIOR_COMPLETO

    def test_midi_sem_notas_devolve_lista_vazia(self):
        pm = pretty_midi.PrettyMIDI()
        pm.instruments.append(pretty_midi.Instrument(program=25))
        assert extrair_eventos(pm) == []
        assert extrair_lista_notas(pm) == []

    def test_midi_vazio_sem_instrumentos_devolve_lista_vazia(self):
        pm = pretty_midi.PrettyMIDI()
        assert extrair_lista_notas(pm) == []


class TestGerarLyTablatura:
    """Verifica a geração do ficheiro .ly (sem compilar com LilyPond)."""

    def _gerar(self, notas, dedilhado="auto", **kwargs):
        pm = criar_midi(notas)
        if dedilhado == "auto":
            eventos = extrair_eventos(pm)
            dedilhado = otimizar_tablatura([p for _, _, p in eventos])
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, "t.ly")
            gerar_ly_tablatura(pm, dedilhado, caminho, **kwargs)
            with open(caminho, encoding="utf-8") as f:
                return f.read()

    def test_gera_tabstaff_com_clef_moderna(self):
        conteudo = self._gerar(DO_MAIOR_SUBIR)
        assert "\\new TabStaff" in conteudo
        assert '\\clef "moderntab"' in conteudo

    def test_tempo_real_do_midi_no_ly(self):
        """O BPM do MIDI (80 no criar_midi) deve aparecer no .ly."""
        conteudo = self._gerar(DO_MAIOR_SUBIR)
        assert "\\tempo 4 = 80" in conteudo

    def test_dedilhado_inclui_anotacoes_de_corda(self):
        conteudo = self._gerar(DO_MAIOR_SUBIR)
        assert "\\5" in conteudo or "\\6" in conteudo, \
            "Deviam existir anotações de corda (\\n) no .ly otimizado"

    def test_sem_dedilhado_nao_ha_anotacoes(self):
        conteudo = self._gerar(DO_MAIOR_SUBIR, dedilhado=None)
        # As notas existem (C3 escreve-se "c" em LilyPond) mas sem anotações \corda
        assert "c4" in conteudo
        for corda in range(1, 7):
            assert f"\\{corda}" not in conteudo.replace("\\time", "").replace("\\tempo", "")

    def test_tonalidade_gera_armadura(self):
        conteudo = self._gerar(DO_MAIOR_SUBIR, tonalidade="D Maior")
        assert "\\key d \\major" in conteudo

    def test_acorde_renderizado_com_angulos(self):
        conteudo = self._gerar([[48, 52, 55], 60])
        assert "<" in conteudo and ">" in conteudo

    def test_midi_sem_notas_levanta_erro(self):
        pm = pretty_midi.PrettyMIDI()
        pm.instruments.append(pretty_midi.Instrument(program=25))
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(RuntimeError):
                gerar_ly_tablatura(pm, None, os.path.join(tmp, "t.ly"))


# ===========================================================================
# TESTES DE INTEGRAÇÃO — Geração de PDFs
# Requerem: LilyPond instalado e configurado no ambiente.
# ===========================================================================

@pytest.mark.integration
class TestGeracaoPdfDoMaior:
    """
    Gera os dois PDFs de comparação direto na pasta backend/tests/.

    Os ficheiros intermédios (.mid, .ly) são criados em subpasta temporária
    e eliminados no final; apenas os PDFs ficam persistidos.
    """

    PDF_COM_OTM = os.path.join(TESTS_DIR, "do_maior_com_otimizacao.pdf")
    PDF_SEM_OTM = os.path.join(TESTS_DIR, "do_maior_sem_otimizacao.pdf")

    @pytest.fixture(autouse=True)
    def _requer_lilypond(self):
        """Salta os testes desta classe com uma mensagem clara em vez de
        deixar rebentar com FileNotFoundError quando o binário do LilyPond
        não está instalado/configurado no ambiente onde a suite corre."""
        if not os.path.exists(CAMINHO_LILYPOND):
            pytest.skip(
                f"LilyPond não encontrado em: {CAMINHO_LILYPOND} "
                "(define LILYPOND_PATH no .env ou instala o binário para "
                "correr estes testes de integração)"
            )

    def _gerar_pdf(self, dedilhado_auto: bool, destino: str):
        pasta = tempfile.mkdtemp(dir=TESTS_DIR, prefix="_tmp_tab_")
        try:
            pm = criar_midi(DO_MAIOR_COMPLETO)

            dedilhado = None
            if dedilhado_auto:
                eventos = extrair_eventos(pm)
                dedilhado = otimizar_tablatura([p for _, _, p in eventos])
                assert dedilhado is not None
                assert len(dedilhado) == len(eventos)

            caminho_ly = os.path.join(pasta, "do_maior.ly")
            gerar_ly_tablatura(pm, dedilhado, caminho_ly)
            assert os.path.exists(caminho_ly)

            compilar_pdf_lilypond(caminho_ly)

            pdf_temp = os.path.splitext(caminho_ly)[0] + ".pdf"
            assert os.path.exists(pdf_temp), \
                f"LilyPond não gerou o PDF esperado em: {pdf_temp}"
            shutil.move(pdf_temp, destino)

            assert os.path.exists(destino)
            assert os.path.getsize(destino) > 0
            print(f"\n  PDF gerado: {destino}")
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_gerar_pdf_com_otimizacao(self):
        """
        Fluxo: PrettyMIDI → eventos → otimizar_tablatura
               → gerar_ly_tablatura (cordas otimizadas) → LilyPond → PDF
        """
        self._gerar_pdf(dedilhado_auto=True, destino=self.PDF_COM_OTM)

    def test_gerar_pdf_sem_otimizacao(self):
        """
        Fluxo: PrettyMIDI → gerar_ly_tablatura sem dedilhado
               (o LilyPond escolhe as cordas) → LilyPond → PDF
        """
        self._gerar_pdf(dedilhado_auto=False, destino=self.PDF_SEM_OTM)
