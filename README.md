# 🎵 AI Music Producer Assistant

> **Status:** Backend Complete, Frontend Pending (Academic Research Project - ISEL 2026)

## Overview

A web-based music production assistant that leverages Generative AI and Large Language Models (LLMs) to overcome creative blocks. The platform allows users to upload a base audio track, provide text prompts (e.g., "generate a jazz piano solo"), and receive complementary musical arrangements in both audio and structured notation (sheet music/tabs).

## System Architecture

The system is built on a modular, service-oriented architecture designed to handle computationally heavy, asynchronous AI generation tasks without blocking the user interface.

* **Backend:** RESTful API built in **Python** with FastAPI, handling business logic, audio processing, and system orchestration.
* **AI Orchestration:** Integration with external AI services (Suno API) for music generation, with Celery for asynchronous processing.
* **Database & Storage:** **PostgreSQL** for relational data persistence (users, project metadata) and local file storage for audio files.
* **Authentication:** OAuth 2.0 integration with Google, GitHub, and Microsoft for secure, passwordless login.
* **Frontend:** *Not yet implemented* - Planned as Single Page Application (SPA) built with React for seamless user interaction.

## Core Features

1. **OAuth Authentication:** Secure login via Google, GitHub, or Microsoft accounts.
2. **Context & Feature Extraction:** Automated analysis of uploaded audio files to extract musical characteristics (BPM, scale, key) using Librosa.
3. **Generative Composition:** Integration with Suno AI API guided by text prompts and extracted harmonic context.
4. **Multi-Format Output:** Translates generated compositions into synthesized audio and MIDI files.
5. **Asynchronous Processing:** Celery workers handle heavy audio synthesis and AI model inference without blocking the API.

## Project Structure

```
AI-Music-Producer-Assistent/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/                # REST API endpoints
│   │   ├── core/               # Configuration and auth
│   │   ├── data/               # Database models and queries
│   │   ├── services/           # Business logic services
│   │   └── worker.py           # Celery task definitions
│   ├── tests/                  # Unit tests (placeholders)
│   ├── main.py                 # Application entry point
│   ├── requirements.txt        # Python dependencies
│   └── README.md               # Backend documentation
├── worker/                     # AI models and audio utilities
│   ├── ai_models/              # Suno API integration
│   └── audio_utils/            # Audio processing tools
├── docker/                     # Docker configuration
│   ├── docker-compose.yml      # Multi-service setup
│   ├── Dockerfile              # Backend container
│   └── SQL/                    # Database initialization
├── frontend/                   # Frontend (not implemented)
│   └── src/
│       └── main.tsx            # Placeholder
└── docs/                       # Documentation
    ├── README.md               # This file
    ├── ESTRUTURA_CRIADA.md     # Project structure details
    ├── INTEGRACAO_WORKER.md    # Worker integration guide
    ├── OAUTH_IMPLEMENTATION.md # OAuth setup and usage
    └── OAUTH_SETUP.md          # OAuth provider configuration
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- OAuth credentials for Google/GitHub/Microsoft (see `docs/OAUTH_SETUP.md`)

### 1. Clone and Setup Environment
```bash
git clone <repository-url>
cd AI-Music-Producer-Assistent

# Copy environment template
cp backend/.env.example backend/.env
# Edit .env with your OAuth credentials and database settings
```

### 2. Start Services with Docker
```bash
cd docker/
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis for Celery (port 6379)
- FastAPI backend (port 8000)
- pgAdmin for database management (port 5050)

### 3. Verify Installation
- **API Health Check:** http://localhost:8000/health
- **API Documentation:** http://localhost:8000/docs
- **pgAdmin:** http://localhost:5050 (admin@example.com / admin)

### 4. Test OAuth Flow
See `docs/OAUTH_SETUP.md` for configuring OAuth providers and testing login flows.

## Development

### Backend Development
```bash
cd backend/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Running Tests
```bash
cd backend/
pytest
# Note: Tests are currently placeholders and need implementation
```

### Worker Tasks
```bash
# Start Celery worker
cd backend/
celery -A app.worker worker --loglevel=info

# Monitor tasks (optional)
celery -A app.worker flower
```

## API Endpoints

### Authentication
- `GET /api/v1/users/auth/{provider}/login` - Initiate OAuth login
- `POST /api/v1/users/auth/{provider}/callback` - Handle OAuth callback
- `GET /api/v1/users/me` - Get current user profile (JWT protected)

### Projects
- `GET /api/v1/projects` - List user projects
- `POST /api/v1/projects` - Create new project
- `GET /api/v1/projects/{id}` - Get project details

### Audio
- `POST /api/v1/audio/upload` - Upload and analyze audio file
- `GET /api/v1/audio/{id}` - Get audio file info

### Generation
- `POST /api/v1/generation` - Request music generation
- `GET /api/v1/generation/{id}` - Get generation status/results

## Roadmap (2026)

- [x] Backend API Development & AI Engine Prototyping (April)
- [x] Worker Integration & Asynchronous Processing (April)
- [x] OAuth Authentication Implementation (April)
- [ ] Frontend SPA Development & Integration (May)
- [ ] Full System Integration & Audio/Notation Synthesis (June)
- [ ] Unit Tests Implementation (Ongoing)
- [ ] Beta Release & Final Optimization (July)

## Dependencies

### Backend
- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Primary database
- **Redis** - Message broker for Celery
- **Celery** - Asynchronous task processing
- **Librosa** - Audio analysis
- **Authlib** - OAuth 2.0 client
- **PyJWT** - JWT token handling

### External Services
- **Suno AI API** - Music generation
- **Google/GitHub/Microsoft OAuth** - Authentication providers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is part of an academic research initiative at ISEL.

---

*Developed by Paulo Nascimento as part of the Computer Engineering degree at ISEL.*