"""
Celery worker tasks for background processing
"""

from celery import Celery
from app.core.config import settings
import os
import sys
from pathlib import Path

# Add worker utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent / "worker"))

# Initialize Celery
app = Celery(
    "music_ai_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
)


@app.task(bind=True, name="generate_music")
def generate_music(
    self,
    generation_id: str,
    audio_id: str,
    prompt: str,
    instrument: str,
    genre: str,
    duration: int,
    tempo_override: int = None,
    suno_prompt: str = ""
):
    """
    Async task to generate music using Suno API
    
    Args:
        self: Celery task instance
        generation_id: Unique generation identifier
        audio_id: Reference audio file ID
        prompt: User prompt
        instrument: Target instrument
        genre: Music genre
        duration: Duration in seconds
        tempo_override: Optional BPM override
        suno_prompt: Detailed prompt for Suno API
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "Initializing generation..."})
        
        try:
            from ai_models.suno_audio_generator import iniciar_geracao, verificar_estado
        except ImportError:
            raise Exception("Could not import Suno generator module")
        
        # Start generation with Suno API
        task_id = iniciar_geracao()
        if not task_id:
            raise Exception("Failed to start generation with Suno API")
        
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing with AI", "suno_task_id": task_id}
        )
        
        # Monitor task completion (simplified - in production would use webhook)
        import time
        max_attempts = 180  # 30 minutes with 10 second intervals
        for attempt in range(max_attempts):
            time.sleep(10)
            
            dados = verificar_estado(task_id)
            if dados and dados.get("code") == 200:
                musicas = dados.get("data", [])
                if musicas and musicas[0].get("audio_url"):
                    # Generation complete
                    return {
                        "generation_id": generation_id,
                        "status": "completed",
                        "suno_task_id": task_id,
                        "audio_url": musicas[0].get("audio_url"),
                        "duration": duration
                    }
            
            progress = int((attempt / max_attempts) * 100)
            self.update_state(
                state="PROGRESS",
                meta={"status": "Generating music with AI", "progress": progress}
            )
        
        raise Exception("Generation timeout - exceeded maximum wait time")
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "generation_id": generation_id}
        )
        raise


@app.task(bind=True, name="convert_to_partitura")
def convert_to_partitura(self, midi_path: str, generation_id: str):
    """
    Async task to convert MIDI to sheet music
    
    Args:
        self: Celery task instance
        midi_path: Path to MIDI file
        generation_id: Generation identifier
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "Converting to sheet music..."})
        
        try:
            from audio_utils.audio_to_partitura import exportar_pdf_automatico
        except ImportError:
            raise Exception("Could not import partitura converter")
        
        pdf_path = exportar_pdf_automatico(midi_path)
        
        if not pdf_path:
            raise Exception("Failed to generate PDF")
        
        return {
            "generation_id": generation_id,
            "status": "completed",
            "partitura_path": pdf_path
        }
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "generation_id": generation_id}
        )
        raise


@app.task(bind=True, name="convert_to_tablatura")
def convert_to_tablatura(self, audio_path: str, generation_id: str):
    """
    Async task to convert audio to guitar tablature
    
    Args:
        self: Celery task instance
        audio_path: Path to audio file
        generation_id: Generation identifier
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "Converting to tablature..."})
        
        try:
            from audio_utils.audio_to_tablature import (
                extrair_midi_do_audio, converter_midi_para_ly,
                forcar_tablatura_no_ly, compilar_pdf_lilypond
            )
        except ImportError:
            raise Exception("Could not import tablature converter")
        
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        midi_path = f"/tmp/{base_name}.mid"
        ly_path = f"/tmp/{base_name}.ly"
        pdf_path = f"/tmp/{base_name}_tablatura.pdf"
        
        # Step 1: Extract MIDI
        self.update_state(state="PROGRESS", meta={"status": "Extracting MIDI from audio..."})
        if not extrair_midi_do_audio(audio_path, midi_path):
            raise Exception("Failed to extract MIDI")
        
        # Step 2: Convert to LilyPond
        self.update_state(state="PROGRESS", meta={"status": "Converting to LilyPond format..."})
        if not converter_midi_para_ly(midi_path, ly_path):
            raise Exception("Failed to convert to LilyPond")
        
        # Step 3: Force tablature
        self.update_state(state="PROGRESS", meta={"status": "Formatting as tablature..."})
        if not forcar_tablatura_no_ly(ly_path):
            raise Exception("Failed to force tablature format")
        
        # Step 4: Compile PDF
        self.update_state(state="PROGRESS", meta={"status": "Compiling PDF..."})
        if not compilar_pdf_lilypond(ly_path):
            raise Exception("Failed to compile PDF")
        
        return {
            "generation_id": generation_id,
            "status": "completed",
            "tablatura_path": pdf_path
        }
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "generation_id": generation_id}
        )
        raise


@app.task(bind=True, name="analyze_audio")
def analyze_audio(self, audio_path: str, audio_id: str):
    """
    Async task to analyze uploaded audio
    
    Args:
        self: Celery task instance
        audio_path: Path to audio file
        audio_id: Audio file identifier
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "Analyzing audio..."})
        
        try:
            from audio_utils.audio_analyzer import analisar_audio_completo
        except ImportError:
            raise Exception("Could not import audio analyzer")
        
        result = analisar_audio_completo(audio_path)
        
        return {
            "audio_id": audio_id,
            "status": "completed",
            "analysis": result
        }
        
    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "audio_id": audio_id}
        )
        raise


if __name__ == "__main__":
    app.start()
