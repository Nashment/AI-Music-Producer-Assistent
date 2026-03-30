"""
Audio Service - Audio processing and analysis business logic
"""

from typing import Optional, Dict
import os
import sys
from pathlib import Path

# Add worker to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "worker"))

try:
    from audio_utils.audio_analyzer import analisar_audio_completo
    from audio_utils.corte_audio import cortar_audio_para_30_segundos
    from audio_utils.ajuste_bpm import ajustar_bpm_automatico
    from audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import worker modules: {e}")

from app.core.config import settings


class AudioService:
    """
    Service for audio operations and analysis
    """

    def __init__(self, data_accessor):
        """
        Initialize service
        
        Args:
            data_accessor: Data access layer instance
        """
        self.data = data_accessor

    async def upload_and_analyze_audio(self, file_path: str, user_id: int) -> dict:
        """
        Upload audio file and analyze characteristics
        
        Args:
            file_path: Path to uploaded audio file
            user_id: User ID
            
        Returns:
            Audio analysis results (BPM, key, duration, etc.)
        """
        # TODO: Validate file format and size
        try:
            # Call audio_analyzer to extract characteristics
            analysis_result = analisar_audio_completo(file_path)
            
            # Structure the results
            audio_analysis = {
                "file_path": file_path,
                "bpm": analysis_result.get("bpm"),
                "key": analysis_result.get("key"),
                "time_signature": analysis_result.get("time_signature"),
                "duration": analysis_result.get("duration"),
                "chords": analysis_result.get("chords", [])
            }
            
            # TODO: Store analysis in database
            return audio_analysis
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return {}

    async def get_audio_analysis(self, audio_id: str) -> Optional[dict]:
        """
        Get previously computed audio analysis
        
        Args:
            audio_id: Audio file identifier
            
        Returns:
            Audio characteristics
        """
        # TODO: Implement cache/database lookup
        pass

    async def extract_audio_characteristics(self, file_path: str) -> dict:
        """
        Extract musical characteristics from audio
        
        Uses: audio_analyzer.py, librosa, etc.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dict with keys: bpm, key, duration, time_signature, sample_rate
        """
        try:
            result = analisar_audio_completo(file_path)
            return {
                "bpm": result.get("bpm", 0),
                "key": result.get("key", "Unknown"),
                "duration": result.get("duration", 0),
                "time_signature": result.get("time_signature", "4/4"),
                "sample_rate": result.get("sample_rate", 44100),
                "chords": result.get("chords", [])
            }
        except Exception as e:
            print(f"Error extracting characteristics: {e}")
            return {}

    async def get_audio_file(self, audio_id: str, user_id: int) -> Optional[str]:
        """
        Get audio file path for download
        
        Args:
            audio_id: Audio identifier
            user_id: User ID (for authorization)
            
        Returns:
            File path or None if not found
        """
        # TODO: Implement
        pass

    async def delete_audio(self, audio_id: str, user_id: int) -> bool:
        """Delete audio file"""
        # TODO: Implement with file cleanup
        pass

    async def cut_audio(self, audio_id: str, start_second: float, end_second: float) -> str:
        """
        Cut audio segment
        
        Uses: corte_audio.py
        
        Args:
            audio_id: Audio identifier
            start_second: Start position
            end_second: End position
            
        Returns:
            Path to cut audio file
        """
        try:
            # Get audio file path from database
            # audio = await self.data.get_audio(audio_id)
            # For now, assuming we have the file path
            output_path = os.path.join(
                settings.AUDIO_UPLOAD_DIR,
                f"cut_{audio_id}_{start_second}_{end_second}.wav"
            )
            
            duration = int(end_second - start_second)
            # cortar_audio_para_30_segundos(input_path, output_path, duration)
            
            return output_path
        except Exception as e:
            print(f"Error cutting audio: {e}")
            return ""

    async def adjust_bpm(self, audio_id: str, target_bpm: int) -> str:
        """
        Adjust audio tempo/BPM
        
        Uses: ajuste_bpm.py
        
        Args:
            audio_id: Audio identifier
            target_bpm: Target BPM
            
        Returns:
            Path to adjusted audio
        """
        try:
            # Get audio file path
            # audio = await self.data.get_audio(audio_id)
            # input_path = audio.file_path
            
            output_path = os.path.join(
                settings.AUDIO_UPLOAD_DIR,
                f"adjusted_{audio_id}_{target_bpm}bpm.wav"
            )
            
            # ajustar_bpm_automatico(input_path, output_path, target_bpm)
            
            return output_path
        except Exception as e:
            print(f"Error adjusting BPM: {e}")
            return ""

    async def separate_tracks(self, audio_id: str) -> dict:
        """
        Separate audio into different instrument tracks
        
        Uses: separador_faixas.py (Demucs)
        
        Args:
            audio_id: Audio identifier
            
        Returns:
            Dict with paths to separated tracks
        """
        try:
            # Available instruments from Demucs
            instruments = ["bateria", "baixo", "piano", "guitarra", "voz", "outros"]
            separated_tracks = {}
            
            # Get audio file path
            # audio = await self.data.get_audio(audio_id)
            # input_path = audio.file_path
            
            # for instrument in instruments:
            #     output_path = os.path.join(
            #         settings.AUDIO_UPLOAD_DIR,
            #         f"{audio_id}_{instrument}.wav"
            #     )
            #     extrair_instrumento(input_path, instrument)
            #     separated_tracks[instrument] = output_path
            
            return separated_tracks
        except Exception as e:
            print(f"Error separating tracks: {e}")
            return {}
