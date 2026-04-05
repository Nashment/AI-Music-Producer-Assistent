"""
Generation Service - Music generation orchestration and AI integration
"""

from typing import Optional
from enum import Enum
import os
import sys
from pathlib import Path
import uuid

# Add worker to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "worker"))

try:
    from ai_models.suno_audio_generator import iniciar_geracao, verificar_estado, guardar_ficheiro
    from ai_models.get_suno_audio import extrair_e_guardar_musicas, consultar_detalhes_oficiais
    from audio_utils.audio_to_partitura import exportar_pdf_automatico
    from audio_utils.audio_to_tablature import (
        extrair_midi_do_audio, converter_midi_para_ly, 
        forcar_tablatura_no_ly, compilar_pdf_lilypond
    )
except ImportError as e:
    print(f"Warning: Could not import worker modules: {e}")

from backend.app.core.config import settings


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
