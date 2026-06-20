"""
Generation Service - Music generation orchestration and AI integration
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from app.data import AudioQueries, GenerationQueries
from app.data.models import GenerationStatusEnum
from app.domain.result import Resultado, Sucesso, Falha
from app.domain.errors.generation_errors import (
    AudioNaoEncontrado,
    GeracaoNaoEncontrada,
    CoverUrlInvalido,
    PesoAudioInvalido,
    WorkerIndisponivel,
    FilaIndisponivel,
    FalhaProcessamentoAudio,
    IntervaloCorteInvalido,
    FicheiroGeracaoIndisponivel,
)
from app.services.storage_service import storage

try:
    from worker.audio_utils.corte_audio import cortar_audio, obter_duracao_audio
except ImportError as e:
    print(f"Warning: Could not import corte_audio module: {e}")
    cortar_audio = obter_duracao_audio = None

try:
    from worker.audio_utils.audio_extractor import extrair_midi_do_audio
    from worker.audio_utils.audio_to_tablature2 import (
        extrair_lista_notas,
        otimizar_tablatura,
        converter_midi_para_ly,
        injetar_inteligencia_no_ly,
        forcar_tablatura_no_ly,
        compilar_pdf_lilypond,
    )
except ImportError as e:
    print(f"Warning: Could not import tablature modules: {e}")
    extrair_midi_do_audio = None
    extrair_lista_notas = otimizar_tablatura = converter_midi_para_ly = None
    injetar_inteligencia_no_ly = forcar_tablatura_no_ly = compilar_pdf_lilypond = None

try:
    from worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
except ImportError as e:
    print(f"Warning: Could not import partitura modules: {e}")
    exportar_pdf_automatico = None


class GenerationService:

    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Submissao
    # ------------------------------------------------------------------

    async def submit_generation(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
    ) -> Resultado:
        try:
            from worker.tasks.generation_tasks import process_generation_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        audio_resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(audio_resultado, Falha):
            return audio_resultado

        generation = await self._criar_registo_geracao(
            user_id, project_id, audio_id, prompt, instrument, genre, duration, tempo_override,
        )
        return await self._enfileirar_tarefa(
            generation, process_generation_task,
            {"generation_id": str(generation.id)},
        )

    async def submit_cover_generation(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
        upload_url: Optional[str],
        audio_weight: float,
    ) -> Resultado:
        try:
            from worker.tasks.generation_tasks import process_cover_generation_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        audio_resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(audio_resultado, Falha):
            return audio_resultado
        audio = audio_resultado.valor

        if upload_url:
            resolved_upload_url = upload_url
        else:
            # URL com 24h de validade para dar tempo ao Suno de processar a task
            resolved_upload_url = storage.get_presigned_url(audio.storage_key, expiry_seconds=86400)
        if not isinstance(resolved_upload_url, str) or not resolved_upload_url.startswith(("http://", "https://")):
            return Falha(CoverUrlInvalido(url_recebido=str(resolved_upload_url)))
        if audio_weight < 0.0 or audio_weight > 1.0:
            return Falha(PesoAudioInvalido(valor=audio_weight))

        generation = await self._criar_registo_geracao(
            user_id, project_id, audio_id, prompt, instrument, genre, duration, tempo_override,
        )
        return await self._enfileirar_tarefa(
            generation, process_cover_generation_task,
            {"generation_id": str(generation.id), "upload_url": resolved_upload_url, "audio_weight": audio_weight},
        )

    # ------------------------------------------------------------------
    # Leitura / Eliminacao
    # ------------------------------------------------------------------

    async def get_generation(self, generation_id: str, user_id: str) -> Resultado:
        gen = await GenerationQueries.get_generation(db=self.db, generation_id=generation_id)
        if not gen or str(gen.user_id) != user_id:
            return Falha(GeracaoNaoEncontrada(generation_id=generation_id))
        return Sucesso(gen)

    async def rename_generation(
        self, generation_id: str, user_id: str, name: str
    ) -> Resultado:
        """Define um nome amigavel para uma geracao/corte. String vazia limpa
        o nome (volta a mostrar o rotulo derivado do prompt)."""
        resultado = await self.get_generation(generation_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        clean = (name or "").strip()
        updated = await GenerationQueries.rename_generation(
            db=self.db, generation_id=generation_id, name=clean or None
        )
        return Sucesso(updated)

    async def delete_generation(self, generation_id: str, user_id: str) -> Resultado:
        resultado = await self.get_generation(generation_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        self._apagar_ficheiros_fisicos(resultado.valor)
        await GenerationQueries.delete_generation(db=self.db, generation_id=generation_id)
        return Sucesso(None)

    # ------------------------------------------------------------------
    # Geracao de notacao a partir de audio existente
    # ------------------------------------------------------------------

    async def generate_tablature(self, audio_id: uuid.UUID, user_id: str, tablatura_dir: str) -> Resultado:
        """Gera tablatura a partir de um audio_id. Usa o mesmo caminho via worker Celery."""
        try:
            from worker.tasks.generation_tasks import generate_tablature_from_audio_key_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        key_resultado = await self._get_audio_s3_key_or_fail(audio_id, user_id)
        if isinstance(key_resultado, Falha):
            return key_resultado
        audio_key = key_resultado.valor

        try:
            result = await asyncio.to_thread(
                lambda: generate_tablature_from_audio_key_task.apply_async(
                    kwargs={"audio_storage_key": audio_key, "prefix": str(audio_id)},
                    queue="notation",
                ).get(timeout=120)
            )
            r2_key = result["r2_key"]
        except Exception as e:
            return Falha(FalhaProcessamentoAudio(operacao=f"celery_tablature_audio: {e}"))

        out_dir = Path(tablatura_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        local_pdf = out_dir / f"{audio_id}_{uuid.uuid4().hex[:8]}_tablatura.pdf"
        ok = storage.download_file(r2_key, str(local_pdf))
        storage.delete_file(r2_key)
        if not ok or not local_pdf.exists():
            return Falha(FalhaProcessamentoAudio(operacao="download_pdf_r2"))
        return Sucesso(str(local_pdf))

    async def generate_partitura(self, audio_id: uuid.UUID, user_id: str, partitura_dir: str) -> Resultado:
        """Gera partitura a partir de um audio_id. Usa o mesmo caminho via worker Celery."""
        try:
            from worker.tasks.generation_tasks import generate_partitura_from_audio_key_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        key_resultado = await self._get_audio_s3_key_or_fail(audio_id, user_id)
        if isinstance(key_resultado, Falha):
            return key_resultado
        audio_key = key_resultado.valor

        try:
            result = await asyncio.to_thread(
                lambda: generate_partitura_from_audio_key_task.apply_async(
                    kwargs={"audio_storage_key": audio_key, "prefix": str(audio_id)},
                    queue="notation",
                ).get(timeout=120)
            )
            r2_key = result["r2_key"]
        except Exception as e:
            return Falha(FalhaProcessamentoAudio(operacao=f"celery_partitura_audio: {e}"))

        out_dir = Path(partitura_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        local_pdf = out_dir / f"{audio_id}_{uuid.uuid4().hex[:8]}_partitura.pdf"
        ok = storage.download_file(r2_key, str(local_pdf))
        storage.delete_file(r2_key)
        if not ok or not local_pdf.exists():
            return Falha(FalhaProcessamentoAudio(operacao="download_pdf_r2"))
        return Sucesso(str(local_pdf))

    async def _generate_tablature_from_path(self, input_path: Path, tablatura_dir: str) -> Resultado:
        if not all([extrair_midi_do_audio, converter_midi_para_ly, injetar_inteligencia_no_ly,
                    forcar_tablatura_no_ly, compilar_pdf_lilypond, extrair_lista_notas, otimizar_tablatura]):
            return Falha(WorkerIndisponivel(detalhe="Modulos de tablatura nao disponiveis."))

        out = Path(tablatura_dir)
        out.mkdir(parents=True, exist_ok=True)
        base      = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        midi_path = out / f"{base}.mid"
        ly_path   = out / f"{base}.ly"
        pdf_path  = out / f"{base}_tablatura.pdf"

        try:
            midi_resultado = await self._extrair_midi_async(input_path, midi_path)
            if isinstance(midi_resultado, Falha):
                return midi_resultado

            if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
                return Falha(FalhaProcessamentoAudio(operacao="conversao_midi_ly"))

            estilo_resultado = await self._aplicar_estilo_tablatura_async(ly_path, midi_resultado.valor)
            if isinstance(estilo_resultado, Falha):
                return estilo_resultado

            compilar_resultado = await self._compilar_pdf_com_fallback_async(midi_path, ly_path)
            if isinstance(compilar_resultado, Falha):
                return compilar_resultado

            ly_pdf_path = ly_path.with_suffix(".pdf")
            if ly_pdf_path.exists():
                ly_pdf_path.replace(pdf_path)
            if not pdf_path.exists():
                return Falha(FalhaProcessamentoAudio(operacao="geracao_pdf"))

            return Sucesso(str(pdf_path))
        finally:
            for p in [midi_path, ly_path]:
                p.unlink(missing_ok=True)

    async def _generate_partitura_from_path(self, input_path: Path, partitura_dir: str) -> Resultado:
        if not all([extrair_midi_do_audio, exportar_pdf_automatico]):
            return Falha(WorkerIndisponivel(detalhe="Modulos de partitura nao disponiveis."))

        out = Path(partitura_dir)
        out.mkdir(parents=True, exist_ok=True)
        base      = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        midi_path = out / f"{base}.mid"
        pdf_path  = out / f"{base}_partitura.pdf"

        try:
            midi_resultado = await self._extrair_midi_async(input_path, midi_path)
            if isinstance(midi_resultado, Falha):
                return midi_resultado

            try:
                await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_path))
            except RuntimeError:
                return Falha(FalhaProcessamentoAudio(operacao="geracao_partitura_pdf"))
            if not pdf_path.exists():
                return Falha(FalhaProcessamentoAudio(operacao="geracao_partitura_pdf"))

            return Sucesso(str(pdf_path))
        finally:
            midi_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Hierarquia: geracoes por audio + cortes
    # ------------------------------------------------------------------

    async def list_generations_for_audio(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        audio_resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(audio_resultado, Falha):
            return audio_resultado
        gens = await GenerationQueries.list_generations_by_audio(
            db=self.db, audio_file_id=audio_id, only_roots=True,
        )
        return Sucesso(gens)

    async def list_cuts_for_generation(self, generation_id: str, user_id: str) -> Resultado:
        parent_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(parent_resultado, Falha):
            return parent_resultado
        parent = parent_resultado.valor
        cuts = await GenerationQueries.list_cuts_of_generation(
            db=self.db, parent_generation_uuid=parent.id,
        )
        return Sucesso(cuts)

    async def get_generation_audio_url(self, generation_id: str, user_id: str) -> Resultado:
        gen_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(gen_resultado, Falha):
            return gen_resultado
        gen = gen_resultado.valor
        if not gen.audio_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="A geracao ainda nao tem audio disponivel.",
            ))
        url = storage.get_presigned_url(gen.audio_storage_key)
        if not url:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="Nao foi possivel gerar URL de download para o audio da geracao.",
            ))
        return Sucesso(url)

    async def cut_generation(
        self,
        parent_generation_id: str,
        user_id: str,
        inicio_segundos: float,
        fim_segundos: float,
        output_dir: str,
        max_window_seconds: float = 45.0,
    ) -> Resultado:
        if cortar_audio is None or obter_duracao_audio is None:
            return Falha(WorkerIndisponivel(detalhe="Modulo de corte de audio indisponivel."))

        parent_resultado = await self.get_generation(parent_generation_id, user_id)
        if isinstance(parent_resultado, Falha):
            return parent_resultado
        parent = parent_resultado.valor

        if inicio_segundos < 0 or fim_segundos <= inicio_segundos:
            return Falha(IntervaloCorteInvalido(detalhe="O inicio tem de ser >= 0 e menor do que o fim."))
        janela = fim_segundos - inicio_segundos
        if janela > max_window_seconds:
            return Falha(IntervaloCorteInvalido(
                detalhe=f"O corte nao pode ser maior do que {max_window_seconds:.0f} segundos.",
            ))

        if not parent.audio_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(detalhe="A geracao pai nao tem audio gerado."))

        out_tmp = Path(tempfile.mktemp(suffix=".wav"))
        try:
            with storage.temp_download(parent.audio_storage_key) as parent_path:
                try:
                    duracao_total = await asyncio.to_thread(obter_duracao_audio, str(parent_path))
                except Exception as e:
                    return Falha(FalhaProcessamentoAudio(operacao=f"obter_duracao: {e}"))

                if inicio_segundos >= duracao_total:
                    return Falha(IntervaloCorteInvalido(detalhe="O inicio esta fora da duracao do audio."))
                fim_clamped = min(fim_segundos, duracao_total)

                try:
                    await asyncio.to_thread(
                        cortar_audio,
                        str(parent_path),
                        str(out_tmp),
                        float(inicio_segundos),
                        float(fim_clamped),
                    )
                except RuntimeError:
                    return Falha(FalhaProcessamentoAudio(operacao="corte_audio"))

            if not out_tmp.exists():
                return Falha(FalhaProcessamentoAudio(operacao="corte_audio"))

            cut_uuid = uuid.uuid4()
            cut_key = f"generations/cut_{cut_uuid.hex[:12]}.wav"
            uploaded = storage.upload_file(str(out_tmp), cut_key)
            if not uploaded:
                return Falha(FalhaProcessamentoAudio(operacao="upload_r2_cut"))

            prompt_descricao = (
                f"Corte de {parent.id} "
                f"({inicio_segundos:.2f}s-{fim_clamped:.2f}s)"
            )
            cut = await GenerationQueries.create_generation(
                db=self.db,
                gen_id=cut_uuid,
                user_id=parent.user_id,
                project_id=parent.project_id,
                audio_file_id=parent.audio_file_id,
                prompt=prompt_descricao,
                instrument=parent.instrument,
                genre=parent.genre,
                duration=int(fim_clamped - inicio_segundos),
                tempo_override=parent.tempo_override,
                parent_generation_id=parent.id,
                status=GenerationStatusEnum.COMPLETED,
                audio_storage_key=cut_key,
            )
            return Sucesso(cut)
        finally:
            out_tmp.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Notacao a partir de uma GERACAO (fire-and-forget — padrao identico ao audio Suno)
    # ------------------------------------------------------------------

    async def request_tablature(self, generation_id: str, user_id: str) -> Resultado:
        """Enfileira geracao de tablatura em background (fire-and-forget).
        Devolve imediatamente a geracao com tablatura_status='pending'.
        O cliente faz polling em GET /{id}/status e aguarda tablatura_status='completed'."""
        try:
            from worker.tasks.generation_tasks import generate_tablature_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        gen_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(gen_resultado, Falha):
            return gen_resultado
        gen = gen_resultado.valor
        if not gen.audio_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(detalhe="A geracao nao tem audio disponivel."))

        # Apagar versao anterior do R2 se existir (caso de regerar)
        if gen.tablatura_storage_key:
            storage.delete_file(gen.tablatura_storage_key)

        # Marcar pending na DB antes de enfileirar para que o polling
        # ja mostre o estado correto mesmo antes do worker arrancar
        await GenerationQueries.update_notation_status(
            db=self.db, generation_id=generation_id,
            notation_type="tablatura", status="pending",
            clear_storage_key=True,  # garante DB consistente ao regenerar
        )

        try:
            generate_tablature_task.apply_async(
                kwargs={"generation_id": generation_id},
                queue="notation",
            )
        except Exception as e:
            return Falha(FilaIndisponivel(detalhe=str(e)))

        # Devolver geracao atualizada (tablatura_status='pending')
        return await self.get_generation(generation_id, user_id)

    async def request_partitura(self, generation_id: str, user_id: str) -> Resultado:
        """Enfileira geracao de partitura em background (fire-and-forget).
        Devolve imediatamente a geracao com partitura_status='pending'."""
        try:
            from worker.tasks.generation_tasks import generate_partitura_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        gen_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(gen_resultado, Falha):
            return gen_resultado
        gen = gen_resultado.valor
        if not gen.audio_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(detalhe="A geracao nao tem audio disponivel."))

        # Apagar versao anterior do R2 se existir (caso de regerar)
        if gen.partitura_storage_key:
            storage.delete_file(gen.partitura_storage_key)

        await GenerationQueries.update_notation_status(
            db=self.db, generation_id=generation_id,
            notation_type="partitura", status="pending",
            clear_storage_key=True,  # garante DB consistente ao regenerar
        )

        try:
            generate_partitura_task.apply_async(
                kwargs={"generation_id": generation_id},
                queue="notation",
            )
        except Exception as e:
            return Falha(FilaIndisponivel(detalhe=str(e)))

        return await self.get_generation(generation_id, user_id)

    async def get_tablature_url(self, generation_id: str, user_id: str) -> Resultado:
        """Devolve presigned URL da tablatura guardada no R2.
        Retorna erro se tablatura_status != 'completed'."""
        gen_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(gen_resultado, Falha):
            return gen_resultado
        gen = gen_resultado.valor
        if not gen.tablatura_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="Tablatura ainda nao disponivel.",
            ))
        url = storage.get_presigned_url(gen.tablatura_storage_key)
        if not url:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="Nao foi possivel gerar URL de download para a tablatura.",
            ))
        return Sucesso(url)

    async def get_partitura_url(self, generation_id: str, user_id: str) -> Resultado:
        """Devolve presigned URL da partitura guardada no R2."""
        gen_resultado = await self.get_generation(generation_id, user_id)
        if isinstance(gen_resultado, Falha):
            return gen_resultado
        gen = gen_resultado.valor
        if not gen.partitura_storage_key:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="Partitura ainda nao disponivel.",
            ))
        url = storage.get_presigned_url(gen.partitura_storage_key)
        if not url:
            return Falha(FicheiroGeracaoIndisponivel(
                detalhe="Nao foi possivel gerar URL de download para a partitura.",
            ))
        return Sucesso(url)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    async def _get_audio_or_fail(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            return Falha(AudioNaoEncontrado(audio_id=audio_id))
        return Sucesso(audio)

    async def _get_audio_s3_key_or_fail(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        return Sucesso(resultado.valor.storage_key)

    async def _criar_registo_geracao(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
    ):
        return await GenerationQueries.create_generation(
            db=self.db,
            user_id=user_id,
            project_id=project_id,
            audio_file_id=audio_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
        )

    async def _enfileirar_tarefa(self, generation, task, kwargs: dict) -> Resultado:
        try:
            async_result = task.apply_async(kwargs=kwargs, retry=False)
        except Exception as e:
            return Falha(FilaIndisponivel(detalhe=str(e)))
        return Sucesso((generation, async_result.id))

    @staticmethod
    def _apagar_ficheiros_fisicos(gen) -> None:
        for attr in ["audio_storage_key", "midi_storage_key", "partitura_storage_key", "tablatura_storage_key"]:
            s3_key = getattr(gen, attr, None)
            if s3_key:
                storage.delete_file(s3_key)

    async def _extrair_midi_async(self, input_path: Path, midi_path: Path) -> Resultado:
        try:
            midi_data = await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path))
            return Sucesso(midi_data)
        except RuntimeError:
            return Falha(FalhaProcessamentoAudio(operacao="extracao_midi"))

    async def _aplicar_estilo_tablatura_async(self, ly_path: Path, midi_data) -> Resultado:
        notas_midi = extrair_lista_notas(midi_data) if midi_data else []
        dedilhado  = otimizar_tablatura(notas_midi) if notas_midi else None
        if dedilhado:
            if not await asyncio.to_thread(injetar_inteligencia_no_ly, str(ly_path), dedilhado):
                return Falha(FalhaProcessamentoAudio(operacao="injecao_dedilhado"))
        else:
            if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
                return Falha(FalhaProcessamentoAudio(operacao="tablatura_padrao"))
        return Sucesso(None)

    async def _compilar_pdf_com_fallback_async(self, midi_path: Path, ly_path: Path) -> Resultado:
        try:
            await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
            return Sucesso(None)
        except RuntimeError:
            pass

        # Fallback: recriar .ly limpo sem dedilhado e tentar de novo
        ly_path.unlink(missing_ok=True)
        if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
            return Falha(FalhaProcessamentoAudio(operacao="conversao_midi_ly_fallback"))
        if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
            return Falha(FalhaProcessamentoAudio(operacao="tablatura_padrao_fallback"))
        try:
            await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
        except RuntimeError:
            return Falha(FalhaProcessamentoAudio(operacao="compilacao_pdf"))

        return Sucesso(None)
