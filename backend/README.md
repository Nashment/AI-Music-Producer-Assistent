"""
README - Backend Setup and Documentation
"""

# AI Music Production Assistant - Backend

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── app/
│   ├── __init__.py
│   ├── api/                   # REST API endpoints
│   │   ├── endpoints/
│   │   │   ├── user.py       # User authentication endpoints
│   │   │   ├── projects.py   # Project management endpoints
│   │   │   ├── audio.py      # Audio upload/analysis endpoints
│   │   │   └── generation.py # Music generation endpoints
│   │   └── router.py         # API router aggregation
│   ├── core/                  # Core configuration and setup
│   │   ├── config.py         # Application settings
│   │   └── __init__.py
│   ├── data/                  # Database layer
│   │   ├── database.py       # Database connection management
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── queries.py        # SQL queries and operations
│   │   └── __init__.py
│   ├── services/              # Business logic layer
│   │   ├── user_service.py       # User management logic
│   │   ├── project_service.py    # Project management logic
│   │   ├── audio_service.py      # Audio processing logic
│   │   ├── generation_service.py # Music generation orchestration
│   │   └── __init__.py
├── worker/                    # Background tasks (Celery)
│   ├── ai_models/            # AI model integrations
│   ├── audio_utils/          # Audio processing utilities
│   └── core/                 # Audio synthesis engine
├── tests/                     # Unit and integration tests
│   ├── conftest.py           # Pytest configuration
│   ├── test_user_service.py
│   ├── test_project_service.py
│   ├── test_audio_service.py
│   └── test_generation_service.py
└── generations/              # Generated files storage
    ├── audio/
    ├── partitura/
    └── tablatura/
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15
- Redis (for async tasks)
- Docker & Docker Compose (recommended)

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   source venv/bin/activate      # Linux/Mac
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**
   ```bash
   # Using Docker Compose (recommended)
   docker-compose up -d postgres redis
   ```

5. **Run migrations** (when available)
   ```bash
   alembic upgrade head
   ```

6. **Start development server**
   ```bash
   uvicorn main:app --reload
   ```

### Docker Setup (Recommended)

```bash
# From docker/ directory
cd ../docker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

**Services:**
- Backend API: http://localhost:8000
- pgAdmin: http://localhost:5050
- PostgreSQL: postgres://localhost:5432
- Redis: redis://localhost:6379

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Endpoints

### Users
- `POST /api/v1/users/register` - Register user
- `POST /api/v1/users/login` - User login
- `GET /api/v1/users/me` - Get current user

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List user projects
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Audio
- `POST /api/v1/audio/upload` - Upload and analyze audio
- `GET /api/v1/audio/{id}` - Download audio

### Generation
- `POST /api/v1/generation` - Submit generation request
- `GET /api/v1/generation/{id}` - Get generation result
- `GET /api/v1/generation/{id}/status` - Check generation status

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_user_service.py

# Run with verbose output
pytest -v
```

## Architecture

### Service Layer
- **UserService**: User authentication and profile management
- **ProjectService**: Project CRUD and metadata
- **AudioService**: Audio file handling and analysis
- **GenerationService**: Music generation orchestration

### Data Layer
- **Database**: Connection management and pooling
- **Models**: SQLAlchemy ORM definitions
- **Queries**: Raw SQL and query operations

### API Layer
- FastAPI endpoints with Pydantic validation
- RESTful routing and error handling
- CORS support for frontend

## Key Features Roadmap

- [x] Project structure and organization
- [x] Basic API scaffolding
- [x] Database schema design
- [x] Service layer templates
- [ ] Authentication & JWT tokens
- [ ] Audio analysis implementation
- [ ] LLM integration for music generation
- [ ] MIDI synthesis with FluidSynth
- [ ] Notation conversion (sheet music/tabs)
- [ ] Celery async task processing
- [ ] WebSocket support for real-time updates

## Development Notes

### Music Context Flow
1. User uploads audio file
2. `AudioService.upload_and_analyze_audio()` extracts BPM, key, time signature
3. User provides prompt for generation
4. `GenerationService` queues task to Celery worker
5. Worker calls `GenerationService.process_generation()`
6. LLM generates MIDI based on audio context and prompt
7. MIDI is synthesized to audio using FluidSynth
8. Notation converters generate sheet music / tabs
9. Results stored and delivered to user

### Database Schema
- **users**: User accounts and authentication
- **projects**: Music projects owned by users
- **audio_files**: Uploaded audio files with analysis
- **generations**: Generation history and results

## Performance Considerations

- Database connection pooling (10 base, 20 overflow)
- Redis caching for task results
- Async processing with Celery for long-running tasks
- Indexed queries on frequently accessed columns

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL health
docker-compose exec postgres pg_isready

# View logs
docker-compose logs postgres
```

### API Not Responding
```bash
# Check backend logs
docker-compose logs -f backend

# Verify database connection
# The health check endpoint: GET /health
```

## Contributing

1. Create feature branch
2. Follow PEP 8 style guide
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Librosa Audio Analysis](https://librosa.org/)
- [Music21 MIDI](https://mit.edu/music21/)
