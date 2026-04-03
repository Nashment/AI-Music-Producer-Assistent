"""
Audio Service - Audio processing and analysis business logic
"""

import os
import uuid
from typing import Optional
from backend.app.data import AudioQueries

from backend.worker.audio_utils.audio_analyzer import analisar_audio_completo


# Assumindo que a tua função de análise vem de outro ficheiro:
# from app.utils.audio_analyzer import analisar_audio_completo


class AudioService:
    def __init__(self, db_session):
        """
        Initialize service

        Args:
            db_session: Sessão do SQLAlchemy injetada pelo FastAPI
        """
        self.db = db_session

    async def upload_and_analyze_audio(
        self,
        file_path: str,
        user_id: str,
        project_id: Optional[str] = None
    ):
        """
        Upload audio file and analyze characteristics

        Args:
            file_path: Path to uploaded audio file
            user_id: User ID (UUID string)
            project_id: Optional Project ID (UUID string)

        Returns:
            O registo do ficheiro de áudio criado na base de dados
        """
        # 1. VALIDAÇÃO DE FORMATO E TAMANHO
        valid_extensions = {'.mp3', '.wav'}
        _, ext = os.path.splitext(file_path.lower())

        if ext not in valid_extensions:
            raise ValueError(f"Formato não suportado. Formatos válidos: {valid_extensions}")

        if not os.path.exists(file_path):
            raise FileNotFoundError("O ficheiro de áudio não foi encontrado no servidor.")

        file_size = os.path.getsize(file_path)
        max_size_bytes = 50 * 1024 * 1024  # Limite de 50 MB

        if file_size > max_size_bytes:
            raise ValueError(f"O ficheiro é demasiado grande ({file_size / 1024 / 1024:.2f}MB). O limite é 50MB.")

        # 2. PROCESSAMENTO E GRAVAÇÃO
        try:
            # Chama a tua função externa de análise de áudio
            analysis_result = analisar_audio_completo(file_path)

            # Preparar IDs (converter strings para UUIDs reais)
            user_uuid = uuid.UUID(user_id)
            project_uuid = uuid.UUID(project_id) if project_id else None

            # Extrair os dados de forma segura (com valores por defeito se o analisador falhar em algum)
            duration = analysis_result.get("duration", 0.0)
            sample_rate = analysis_result.get("sample_rate", 44100) # Exemplo de default

            # Garantir que o BPM é um inteiro, se existir
            bpm_raw = analysis_result.get("bpm")
            bpm = int(bpm_raw) if bpm_raw is not None else None

            key = analysis_result.get("key")
            time_signature = analysis_result.get("time_signature")

            # 3. GUARDAR NA BASE DE DADOS
            # Delegamos a gravação à nossa classe AudioQueries
            audio_record = AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_uuid,
                project_id=project_uuid,
                file_path=file_path,
                file_size=file_size,
                duration=duration,
                sample_rate=sample_rate,
                bpm=bpm,
                key=key,
                time_signature=time_signature
            )

            # Podes adicionar os "chords" dinâmicos ao objeto antes de devolver, se precisares deles na API
            audio_record.chords = analysis_result.get("chords", [])

            return audio_record

        except Exception as e:
            # Em vez de devolver um dict vazio, levantamos o erro.
            # Isto permite que a tua rota FastAPI apanhe a exceção e devolva um erro HTTP 500 ou 400 real ao telemóvel.
            print(f"Erro ao processar áudio: {e}")
            raise

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
