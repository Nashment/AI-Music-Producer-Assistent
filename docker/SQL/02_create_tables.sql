-- ==========================================
-- DROP EXISTING TABLES (if they exist)
-- ==========================================
DROP TABLE IF EXISTS generations CASCADE;
DROP TABLE IF EXISTS audio_files CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ==========================================
-- CREATE APPLICATION TABLES (Privacy-First)
-- ==========================================

-- ==========================================
-- USERS TABLE (Strict OAuth, Minimal Data)
-- ==========================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(128) UNIQUE NOT NULL, -- O nome público dentro da app

    -- Configuração OAuth (O estritamente necessário para o login)
    oauth_provider VARCHAR(50) NOT NULL,   -- ex: 'google', 'github', 'apple'
    oauth_id VARCHAR(255) NOT NULL,        -- O ID anónimo fornecido pelo provider

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Garante que a combinação provedor + ID é única, mas permite que o mesmo utilizador
    -- possa futuramente ligar múltiplas contas se precisares
    UNIQUE(oauth_provider, oauth_id)
);

CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- PROJECTS TABLE
-- ==========================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tempo INTEGER,  -- BPM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_projects_user_title UNIQUE (user_id, title)
);

CREATE TRIGGER update_projects_timestamp
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- AUDIO_FILES TABLE
-- ==========================================
CREATE TABLE audio_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER,  -- bytes
    duration FLOAT,     -- segundos
    sample_rate INTEGER,
    bpm INTEGER,
    key VARCHAR(32),
    time_signature VARCHAR(32),
    parent_audio_id UUID REFERENCES audio_files(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- GENERATIONS TABLE
-- ==========================================
CREATE TABLE generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generation_id VARCHAR(128) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    audio_file_id UUID REFERENCES audio_files(id) ON DELETE SET NULL,

    -- Self-FK para suportar cortes derivados de uma geração original.
    -- Ver hierarquia: Audio -> Generation (IA) -> Generation (corte).
    parent_generation_id UUID REFERENCES generations(id) ON DELETE CASCADE,

    -- Generation parameters
    prompt TEXT NOT NULL,
    instrument VARCHAR(128),
    genre VARCHAR(128),
    duration INTEGER,  -- segundos
    tempo_override INTEGER,

    -- Status and results
    -- audio_file_path armazena o áudio final: instrumento isolado, BPM e tom corrigidos.
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    audio_fi    le_path VARCHAR(512),
    midi_file_path VARCHAR(512),
    partitura_file_path VARCHAR(512),
    tablatura_file_path VARCHAR(512),
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ==========================================
-- INDEXES FOR PERFORMANCE
-- ==========================================

-- Índices para os Utilizadores
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

-- Índices para os Projetos
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- Índices para os Ficheiros de Áudio
CREATE INDEX idx_audio_files_user_id ON audio_files(user_id);
CREATE INDEX idx_audio_files_project_id ON audio_files(project_id);
CREATE INDEX idx_audio_files_created_at ON audio_files(created_at DESC);

-- Índices para as Gerações
CREATE INDEX idx_generations_user_id ON generations(user_id);
CREATE INDEX idx_generations_project_id ON generations(project_id);
CREATE INDEX idx_generations_status ON generations(status);
CREATE INDEX idx_generations_generation_id ON generations(generation_id);
CREATE INDEX idx_generations_created_at ON generations(created_at DESC);
CREATE INDEX idx_generations_user_project ON generations(user_id, project_id);
CREATE INDEX idx_generations_parent_id ON generations(parent_generation_id);
CREATE INDEX idx_generations_audio_file_id ON generations(audio_file_id);
