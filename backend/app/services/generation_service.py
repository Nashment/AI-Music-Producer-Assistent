"""
Generation Service - Music generation orchestration and AI integration
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from backend.app.data import AudioQueries, GenerationQueries
from backend.app.data.models import GenerationStatusEnum

try:
    from backend.worker.ai_models.suno_audio_generator import (
        iniciar_geracao, verificar_estado, guardar_ficheiro
    )
    from backend.worker.audio_utils.audio_to_tablature import (
        extrair_midi_do_audio, converter_midi_para_ly,
        forcar_tablatura_no_ly, compilar_pdf_lilypond
    )
    from backend.worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
except ImportError as e:
    print(f"Warning: Could not import worker modules: {e}")
    iniciar_geracao = None
    verificar_estado = None
    guardar_ficheiro = None
    extrair_midi_do_audio = None
    converter_midi_para_ly = None
    forcar_tablatura_no_ly = None
    compilar_pdf_lilypond = None
    exportar_pdf_automatico = None


class GenerationService:

    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Submissão
    # ------------------------------------------------------------------

    async def submit_generation(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: str,
        duration: int,
        tempo_override: Optional[int],
        audio_output_dir: str,
        partitura_output_dir: str,
        tablatura_output_dir: str,
    ):
        """Submete para o Suno, guarda na BD com status PENDING e inicia polling em background."""
        if not iniciar_geracao:
            raise NotImplementedError("Suno integration not available.")

        # Validar que o áudio pertence ao utilizador
        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado ou sem permissão.")

        # Construir prompt para o Suno
        style_prompt = self._build_suno_prompt(prompt, instrument, genre, audio, tempo_override)
        title = f"{instrument} {genre} - {prompt[:40]}"

        # Chamar API do Suno (operação de rede — correr em thread para não bloquear event loop)
        task_id = await asyncio.to_thread(iniciar_geracao, style_prompt, title)
        if not task_id:
            raise RuntimeError("Falha ao iniciar a geração no Suno. Verifica a API key.")

        # Guardar na base de dados
        generation = await GenerationQueries.create_generation(
            db=self.db,
            generation_id=task_id,
            user_id=uuid.UUID(user_id),
            project_id=project_id,
            audio_file_id=audio_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
        )

        return generation, task_id, audio_output_dir, partitura_output_dir, tablatura_output_dir

    # ------------------------------------------------------------------
    # Polling (chamado como BackgroundTask pelo endpoint)
    # ------------------------------------------------------------------

    @staticmethod
    async def poll_and_complete(
        generation_id: str,
        audio_output_dir: str,
        partitura_output_dir: str,
        tablatura_output_dir: str,
    ):
        """
        Faz polling ao Suno até a geração estar pronta, descarrega o áudio
        e gera partitura + tablatura. Corre como BackgroundTask.
        """
        from backend.app.data.database import db as db_manager

        db = db_manager.get_session()
        try:
            await GenerationService._poll_loop(
                db, generation_id,
                audio_output_dir, partitura_output_dir, tablatura_output_dir
            )
        except Exception as e:
            try:
                await GenerationQueries.update_generation_status(
                    db=db,
                    generation_id=generation_id,
                    status=GenerationStatusEnum.FAILED,
                    error_message=str(e),
                )
            except Exception:
                pass
        finally:
            await db.close()

    @staticmethod
    async def _poll_loop(db, generation_id, audio_dir, partitura_dir, tablatura_dir):
        max_attempts = 20  # máx. ~10 minutos

        for _ in range(max_attempts):
            await asyncio.sleep(30)

            dados = await asyncio.to_thread(verificar_estado, generation_id)

            if not dados or dados.get("code") != 200:
                continue

            musicas = dados.get("data", [])
            if not musicas or not musicas[0].get("audio_url"):
                continue  # ainda a processar

            # Atualizar para PROCESSING
            await GenerationQueries.update_generation_status(
                db=db, generation_id=generation_id,
                status=GenerationStatusEnum.PROCESSING,
            )

            audio_url = musicas[0]["audio_url"]
            Path(audio_dir).mkdir(parents=True, exist_ok=True)
            audio_path = Path(audio_dir) / f"{generation_id}.mp3"

            ok = await asyncio.to_thread(guardar_ficheiro, audio_url, str(audio_path))
            if not ok:
                raise RuntimeError("Falha ao descarregar o áudio gerado.")

            # Gerar partitura e tablatura (ignorar erros — não são críticos)
            midi_path = None
            partitura_path = None
            tablatura_path = None

            if extrair_midi_do_audio:
                Path(partitura_dir).mkdir(parents=True, exist_ok=True)
                Path(tablatura_dir).mkdir(parents=True, exist_ok=True)
                base = generation_id
                midi_path = Path(partitura_dir) / f"{base}.mid"
                try:
                    midi_ok = await asyncio.to_thread(
                        extrair_midi_do_audio, str(audio_path), str(midi_path)
                    )
                    if midi_ok:
                        # Partitura
                        if exportar_pdf_automatico:
                            p_pdf = Path(partitura_dir) / f"{base}_partitura.pdf"
                            result = await asyncio.to_thread(
                                exportar_pdf_automatico, str(midi_path), str(p_pdf)
                            )
                            if result:
                                partitura_path = str(p_pdf)

                        # Tablatura
                        if all([converter_midi_para_ly, forcar_tablatura_no_ly, compilar_pdf_lilypond]):
                            t_ly = Path(tablatura_dir) / f"{base}.ly"
                            t_pdf = Path(tablatura_dir) / f"{base}_tablatura.pdf"
                            ok_ly = await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(t_ly))
                            if ok_ly:
                                await asyncio.to_thread(forcar_tablatura_no_ly, str(t_ly))
                                ok_pdf = await asyncio.to_thread(compilar_pdf_lilypond, str(t_ly))
                                if ok_pdf:
                                    tablatura_path = str(t_pdf)
                            if t_ly.exists():
                                t_ly.unlink(missing_ok=True)
                except Exception as e:
                    print(f"Aviso: erro na geração de notação: {e}")
                finally:
                    if midi_path and midi_path.exists():
                        midi_path.unlink(missing_ok=True)

            await GenerationQueries.update_generation_status(
                db=db,
                generation_id=generation_id,
                status=GenerationStatusEnum.COMPLETED,
                audio_path=str(audio_path),
                partitura_path=partitura_path,
                tablatura_path=tablatura_path,
            )
            return

        # Timeout
        raise RuntimeError("Tempo limite de geração excedido (10 minutos).")

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    async def get_generation(self, generation_id: str, user_id: str):
        gen = await GenerationQueries.get_generation(db=self.db, generation_id=generation_id)
        if not gen:
            raise ValueError("Geração não encontrada.")
        if str(gen.user_id) != user_id:
            raise PermissionError("Acesso negado.")
        return gen

    async def delete_generation(self, generation_id: str, user_id: str):
        gen = await self.get_generation(generation_id, user_id)
        # Apagar ficheiros gerados do disco
        for attr in ["audio_file_path", "midi_file_path", "partitura_file_path", "tablatura_file_path"]:
            path_str = getattr(gen, attr, None)
            if path_str:
                p = Path(path_str)
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as e:
                        print(f"Aviso: não foi possível apagar {path_str}: {e}")
        await GenerationQueries.delete_generation(db=self.db, generation_id=generation_id)

    # ------------------------------------------------------------------
    # Geração de notação a partir de áudio existente
    # ------------------------------------------------------------------

    async def generate_tablature(self, audio_id: uuid.UUID, user_id: str, tablatura_dir: str) -> str:
        """Gera uma tablatura PDF a partir de um ficheiro de áudio existente."""
        if not all([extrair_midi_do_audio, converter_midi_para_ly, forcar_tablatura_no_ly, compilar_pdf_lilypond]):
            raise NotImplementedError("Tablature generation not available.")

        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado.")

        input_path = Path(audio.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        base = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        out = Path(tablatura_dir)
        out.mkdir(parents=True, exist_ok=True)
        midi_path = out / f"{base}.mid"
        ly_path = out / f"{base}.ly"
        pdf_path = out / f"{base}_tablatura.pdf"

        try:
            if not await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path)):
                raise RuntimeError("Falha na extração MIDI.")
            if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
                raise RuntimeError("Falha na conversão MIDI→LilyPond.")
            if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
                raise RuntimeError("Falha na formatação de tablatura.")
            if not await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path)):
                raise RuntimeError("Falha na compilação PDF.")
            if not pdf_path.exists():
                raise RuntimeError("PDF não foi gerado.")
            return str(pdf_path)
        finally:
            for p in [midi_path, ly_path]:
                if p.exists():
                    p.unlink(missing_ok=True)

    async def generate_partitura(self, audio_id: uuid.UUID, user_id: str, partitura_dir: str) -> str:
        """Gera uma partitura PDF a partir de um ficheiro de áudio existente."""
        if not all([extrair_midi_do_audio, exportar_pdf_automatico]):
            raise NotImplementedError("Partitura generation not available.")

        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado.")

        input_path = Path(audio.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        base = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        out = Path(partitura_dir)
        out.mkdir(parents=True, exist_ok=True)
        midi_path = out / f"{base}.mid"
        pdf_path = out / f"{base}_partitura.pdf"

        try:
            if not await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path)):
                raise RuntimeError("Falha na extração MIDI.")
            result = await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_path))
            if not result or not pdf_path.exists():
                raise RuntimeError("Falha na geração da partitura PDF.")
            return str(pdf_path)
        finally:
            if midi_path.exists():
                midi_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_suno_prompt(self, prompt: str, instrument: str, genre: str, audio, tempo_override: Optional[int]) -> str:
        bpm = tempo_override or getattr(audio, "bpm", None)
        key = getattr(audio, "key", None)
        time_sig = getattr(audio, "time_signature", None)

        parts = [prompt, f"{instrument} solo", genre]
        if bpm:
            parts.append(f"{bpm} BPM")
        if key:
            parts.append(f"Key of {key}")
        if time_sig:
            parts.append(f"{time_sig} time signature")
        parts.append("professional quality")

        return ", ".join(parts)



class GenerationStatus(str, Enum):
    """Generation task status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationService:
    """
    Service for orchestrating music generation using AI models
    """

    def __init__(self, data_accessor, llm_service=None, audio_service=None):
        """
        Initialize service
        
        Args:
            data_accessor: Data access layer
            llm_service: LLM service for prompts (optional)
            audio_service: Audio service for synthesis (optional)
        """
        self.data = data_accessor
        self.llm = llm_service
        self.audio = audio_service

    async def submit_generation_request(
        self,
        project_id: int,
        audio_id: str,
        user_id: int,
        prompt: str,
        instrument: str,
        genre: str,
        duration: int,
        tempo_override: Optional[int] = None
    ) -> dict:
        """
        Submit a music generation request to worker queue
        
        Uses: Suno API integration
        
        Args:
            project_id: Project identifier
            audio_id: Reference audio file ID
            user_id: User ID
            prompt: User prompt/instruction
            instrument: Target instrument
            genre: Music genre
            duration: Duration in seconds
            tempo_override: Optional tempo override
            
        Returns:
            Generation task metadata with ID
        """
        generation_id = str(uuid.uuid4())
        
        try:
            # Build prompt for Suno API
            style_prompt = self._build_suno_prompt(prompt, instrument, genre, tempo_override)
            
            # TODO: Implement queue to worker with these params
            # For now, returning task structure
            
            task_metadata = {
                "generation_id": generation_id,
                "project_id": project_id,
                "user_id": user_id,
                "status": GenerationStatus.PENDING.value,
                "prompt": prompt,
                "instrument": instrument,
                "genre": genre,
                "duration": duration,
                "suno_prompt": style_prompt
            }
            
            # TODO: Save to database
            return task_metadata
        except Exception as e:
            print(f"Error submitting generation request: {e}")
            return {"error": str(e)}

    async def get_generation_status(self, generation_id: str, user_id: int) -> Optional[dict]:
        """
        Get status of a generation task
        
        Args:
            generation_id: Generation task ID
            user_id: User ID (for authorization)
            
        Returns:
            Task status with progress
        """
        # TODO: Query database/task queue
        # TODO: Return status
        pass

    async def get_generation_result(self, generation_id: str, user_id: int) -> Optional[dict]:
        """
        Get completed generation results
        
        Args:
            generation_id: Generation task ID
            user_id: User ID
            
        Returns:
            Dict with audio_url, partitura_url, tablatura_url, midi_url
        """
        # TODO: Query database
        # TODO: Verify task is completed
        # TODO: Return file URLs
        pass

    async def convert_audio_to_partitura(self, midi_path: str) -> Optional[str]:
        """
        Convert MIDI to sheet music PDF
        
        Uses: MuseScore
        
        Args:
            midi_path: Path to MIDI file
            
        Returns:
            Path to generated PDF or None
        """
        try:
            pdf_path = os.path.join(
                settings.PARTITURA_OUTPUT_DIR,
                f"partitura_{os.path.basename(midi_path)}.pdf"
            )
            
            result = exportar_pdf_automatico(midi_path, pdf_path)
            return result
        except Exception as e:
            print(f"Error converting to partitura: {e}")
            return None

    async def convert_audio_to_tablatura(self, audio_path: str) -> Optional[str]:
        """
        Convert audio to guitar tablature
        
        Uses: LilyPond + basic_pitch
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Path to generated tablature PDF
        """
        try:
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            midi_path = os.path.join(
                settings.TABLATURA_OUTPUT_DIR,
                f"{base_name}.mid"
            )
            ly_path = os.path.join(
                settings.TABLATURA_OUTPUT_DIR,
                f"{base_name}.ly"
            )
            pdf_path = os.path.join(
                settings.TABLATURA_OUTPUT_DIR,
                f"{base_name}_tablatura.pdf"
            )
            
            # Step 1: Extract MIDI from audio
            if not extrair_midi_do_audio(audio_path, midi_path):
                return None
            
            # Step 2: Convert MIDI to LilyPond format
            if not converter_midi_para_ly(midi_path, ly_path):
                return None
            
            # Step 3: Force tablature format
            if not forcar_tablatura_no_ly(ly_path):
                return None
            
            # Step 4: Compile to PDF
            if not compilar_pdf_lilypond(ly_path):
                return None
            
            return pdf_path
        except Exception as e:
            print(f"Error converting to tablatura: {e}")
            return None

    async def process_generation(
        self,
        generation_id: str,
        audio_analysis: dict,
        prompt: str,
        instrument: str,
        genre: str,
        duration: int
    ) -> dict:
        """
        Process generation (called by worker)
        
        Args:
            generation_id: Task ID
            audio_analysis: Analyzed audio characteristics
            prompt: User prompt
            instrument: Target instrument
            genre: Music genre
            duration: Duration in seconds
            
        Returns:
            Generated MIDI data and audio
        """
        # TODO: Call LLM to generate MIDI sequence
        # TODO: Call synthesizer to create audio
        # TODO: Call notation conversion
        # TODO: Save results
        pass

    async def generate_midi_from_analysis(
        self,
        audio_analysis: dict,
        prompt: str,
        instrument: str,
        genre: str,
        duration: int
    ) -> bytes:
        """
        Generate MIDI data using LLM based on audio analysis
        
        Uses: get_suno_audio.py, suno_audio_generator.py, LLM
        
        Args:
            audio_analysis: Audio characteristics
            prompt: User instructions
            instrument: Target instrument
            genre: Music genre
            duration: Duration in seconds
            
        Returns:
            MIDI file bytes
        """
        # TODO: Build LLM prompt with context
        # TODO: Call LLM to generate music notes
        # TODO: Convert to MIDI format
        pass

    async def synthesize_audio(self, midi_data: bytes, instrument: str) -> bytes:
        """
        Synthesize audio from MIDI
        
        Uses: fluidsynth, soundfonts
        
        Args:
            midi_data: MIDI file bytes
            instrument: Instrument name
            
        Returns:
            WAV audio bytes
        """
        # TODO: Load appropriate soundfont
        # TODO: Synthesize with fluidsynth
        # TODO: Return audio data
        pass

    async def convert_to_notation(
        self,
        midi_data: bytes,
        notation_type: str  # "partitura" or "tablatura"
    ) -> bytes:
        """
        Convert MIDI to notation format
        
        Uses: audio_to_partitura.py, audio_to_tablature.py
        
        Args:
            midi_data: MIDI file bytes
            notation_type: "partitura" for sheet music or "tablatura" for tabs
            
        Returns:
            Notation file bytes (MusicXML, PDF, etc.)
        """
        # TODO: Call appropriate converter module
        pass

    async def regenerate_with_prompt(
        self,
        generation_id: str,
        new_prompt: str,
        user_id: int
    ) -> dict:
        """Regenerate music with new prompt"""
        # TODO: Implement
        pass

    async def delete_generation(self, generation_id: str, user_id: int) -> bool:
        """Delete generation result and cleanup files"""
        # TODO: Implement
        pass

    def _build_suno_prompt(self, prompt: str, instrument: str, genre: str, tempo: Optional[int] = None) -> str:
        """
        Build a detailed prompt for Suno API based on user input and audio analysis
        
        Args:
            prompt: User's original prompt
            instrument: Target instrument
            genre: Music genre
            tempo: Optional tempo/BPM
            
        Returns:
            Detailed prompt for Suno API
        """
        tempo_str = f"{tempo} BPM, " if tempo else ""
        
        suno_prompt = f"{prompt}, {instrument} solo, {genre}, {tempo_str}professional quality"
        
        return suno_prompt
