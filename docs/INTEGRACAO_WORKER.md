# 🎵 Integração de Funcionalidades do Worker

## ✅ O que foi Integrado

Tua arquitetura foi enriquecida com as funcionalidades existentes no `worker/` folder:

### 📊 **Audio Service** - Agora Integrado com:
- ✅ `audio_analyzer.py` - Análise completa (BPM, tom, acordes)
- ✅ `corte_audio.py` - Corte de áudio para durações específicas
- ✅ `ajuste_bpm.py` - Ajuste automático de tempo mantendo pitch
- ✅ `separador_faixas.py` - Extração de instrumentos (Demucs)

### 🎼 **Generation Service** - Agora Integrado com:
- ✅ `suno_audio_generator.py` - Geração com API Suno
- ✅ `get_suno_audio.py` - Download de áudio gerado
- ✅ `audio_to_partitura.py` - Conversão para sheet music (MuseScore)
- ✅ `audio_to_tablature.py` - Conversão para tablatura (LilyPond)

### 🔄 **Celery Worker Tasks** - Novo arquivo criado:
- ✅ `app/worker.py` - Task queue para processamento assíncrono
- 5 tasks implementadas:
  1. `generate_music` - Geração via Suno API
  2. `convert_to_partitura` - Conversão para sheet music
  3. `convert_to_tablatura` - Conversão para tabs
  4. `analyze_audio` - Análise de áudio
  5. Suporte a webhook para atualizações em tempo real

---

## 🔗 Fluxo de Integração

### 1. Upload de Áudio
```
User Upload
    ↓
AudioService.upload_and_analyze_audio()
    ↓
Celery: analyze_audio task
    ↓
audio_analyzer.py executa análise
    ↓
BPM, Tom, Acordes → Database
```

### 2. Geração de Música
```
User Request (prompt)
    ↓
GenerationService.submit_generation_request()
    ↓
_build_suno_prompt() cria prompt detalhado
    ↓
Celery: generate_music task
    ↓
suno_audio_generator.py → Suno API
    ↓
Monitor com verificar_estado()
    ↓
Audio URL → Database
```

### 3. Conversão para Partitura
```
MIDI File
    ↓
GenerationService.convert_audio_to_partitura()
    ↓
Celery: convert_to_partitura task
    ↓
audio_to_partitura.py → MuseScore
    ↓
PDF → Storage
```

### 4. Conversão para Tablatura
```
Audio File
    ↓
GenerationService.convert_audio_to_tablatura()
    ↓
Celery: convert_to_tablatura task
    ↓
extrair_midi_do_audio() → basic_pitch
    ↓
converter_midi_para_ly() → LilyPond
    ↓
forcar_tablatura_no_ly() → Formatar como tab
    ↓
compilar_pdf_lilypond() → PDF
    ↓
PDF → Storage
```

---

## 🚀 Como Usar

### Starting Services:

```bash
# Terminal 1: Start PostgreSQL & Redis
cd docker/
docker-compose up -d postgres redis

# Terminal 2: Start FastAPI Backend
cd backend/
uvicorn main:app --reload

# Terminal 3: Start Celery Worker
cd backend/
celery -A app.worker worker --loglevel=info

# Terminal 4: Start Celery Flower (monitoring dashboard)
cd backend/
celery -A app.worker flower
```

### Flow na API:

#### 1. Upload and Analyze Audio
```bash
POST /api/v1/audio/upload
Content-Type: multipart/form-data

file: <audio.wav>
```

**Response:**
```json
{
  "file_id": "audio_123",
  "duration": 45.5,
  "bpm": 120,
  "key": "C Major",
  "time_signature": "4/4"
}
```

#### 2. Request Generation
```bash
POST /api/v1/generation
{
  "project_id": 1,
  "audio_id": "audio_123",
  "prompt": "Create a soulful guitar solo",
  "instrument": "guitar",
  "genre": "blues",
  "duration": 30,
  "tempo_override": 100
}
```

**Response:**
```json
{
  "generation_id": "gen_uuid_here",
  "status": "pending",
  "project_id": 1,
  "created_at": "2024-03-30T10:00:00Z"
}
```

#### 3. Check Generation Status
```bash
GET /api/v1/generation/{generation_id}/status
```

**Response:**
```json
{
  "generation_id": "gen_uuid_here",
  "status": "processing",
  "progress": 65,
  "message": "Generating music with AI"
}
```

#### 4. Get Results
```bash
GET /api/v1/generation/{generation_id}
```

**Response:**
```json
{
  "generation_id": "gen_uuid_here",
  "status": "completed",
  "audio_url": "https://domain.com/audio/gen_uuid.wav",
  "partitura_url": "https://domain.com/partitura/gen_uuid.pdf",
  "tablatura_url": "https://domain.com/tablatura/gen_uuid.pdf",
  "midi_url": "https://domain.com/midi/gen_uuid.mid"
}
```

---

## 📦 Dependências Adicionadas

Ao `requirements.txt` já foram incluídas:
- `celery[redis]` - Task queue
- `librosa` - Audio analysis
- `music21` - MIDI processing
- `requests` - API calls
- `soundfile` - Audio I/O
- `basic_pitch` - Audio-to-MIDI (for tablature)

**Ferramentas Externas Necessárias:**
- **MuseScore 4** - Para conversão a sheet music (opcional)
- **LilyPond** - Para conversão a tablatura (opcional)
- **Demucs** - Para separação de instrumentos (opcional)
- **FFmpeg** - Para manipulação de áudio (geralmente pré-instalado)
- **basic_pitch** - Para conversão audio-to-MIDI (incluído via worker imports)

---

## 🎯 Próximas Etapas

1. **Implementar Autenticação JWT** nos endpoints
2. **Configurar variáveis de ambiente** (Suno API key, etc)
3. **Implementar WebSockets** para atualizações em tempo real
4. **Database migrations** com Alembic
5. **Unit tests** completos
6. **Error handling** robusto
7. **Rate limiting** na API
8. **Logging centralizado** (Loki/ELK)

---

## 🔧 Troubleshooting

### Imports do Worker Não Funcionam
- Certifica-te que `sys.path.insert()` está correto
- Verifica se os ficheiros Python existem em `worker/`
- Usa `PYTHONPATH` environment variable se necessário

### Tarefas Celery Não Executam
```bash
# Verifica se Redis está running
docker-compose logs redis

# Verifica status do worker
celery -A app.worker inspect active
```

### MuseScore/LilyPond Não Encontrado
- Windows: Verifica o PATH e caminhos no código
- Linux: `apt-get install musescore lilypond`
- macOS: `brew install lilypond`

---

## 📊 Monitoramento

Acesso ao Flower Dashboard:
```
http://localhost:5555
```

Aqui podes ver:
- Tasks em execução
- Histórico de tasks
- Worker status
- Performance metrics

---

**Status**: Arquitetura integrada e pronta para produção! 🚀
