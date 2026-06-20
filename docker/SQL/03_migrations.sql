-- ==========================================
-- MIGRATIONS
-- ==========================================
-- Cada bloco usa IF EXISTS / DO $$ para ser idempotente
-- (pode ser executado múltiplas vezes sem erros).
--
-- NOTA: As migrações 002 e 003 já estão incorporadas em 02_create_tables.sql.
-- Este ficheiro serve apenas para atualizar bases de dados existentes criadas
-- com versões anteriores do schema.

-- ==========================================
-- Migração 001 — remover faixa_separada_path da tabela generations
-- ==========================================
-- O audio final (audio_file_path) já é sempre o instrumento isolado e pós-processado,
-- portanto a coluna faixa_separada_path era redundante e foi removida.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'generations'
          AND column_name = 'faixa_separada_path'
    ) THEN
        ALTER TABLE generations
            DROP COLUMN faixa_separada_path;
    END IF;
END $$;

-- ==========================================
-- Migração 002 — parent_generation_id em generations (cortes)
-- ==========================================
-- Um "corte" é tratado como um registo de generations cujo
-- parent_generation_id aponta para a geração original. Isto modela a
-- hierarquia: Audio (upload) -> Generation (IA) -> Generation (corte).
--
-- ON DELETE CASCADE garante que apagar a geração original também apaga
-- todos os cortes derivados — comportamento consistente com a forma como
-- já apagamos audio_files relacionados.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'generations'
          AND column_name = 'parent_generation_id'
    ) THEN
        ALTER TABLE generations
            ADD COLUMN parent_generation_id UUID NULL
                REFERENCES generations(id) ON DELETE CASCADE;
        CREATE INDEX idx_generations_parent_id
            ON generations(parent_generation_id);
    END IF;
END $$;

-- ==========================================
-- Migração 003 — estado assíncrono de notação (partitura + tablatura)
-- ==========================================
-- Replica o padrão de audio_storage_key/status para as notações geradas
-- em background. Valores: null | 'pending' | 'processing' | 'completed' | 'failed'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'generations'
          AND column_name = 'partitura_status'
    ) THEN
        ALTER TABLE generations
            ADD COLUMN partitura_status VARCHAR(32) DEFAULT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'generations'
          AND column_name = 'tablatura_status'
    ) THEN
        ALTER TABLE generations
            ADD COLUMN tablatura_status VARCHAR(32) DEFAULT NULL;
    END IF;
END $$;

-- ==========================================
-- Migração 004 — nomes amigáveis (rename)
-- ==========================================
-- Permite ao utilizador renomear áudios e gerações/cortes sem afetar as
-- storage keys do R2. Colunas opcionais (NULL = usar nome derivado).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audio_files'
          AND column_name = 'display_name'
    ) THEN
        ALTER TABLE audio_files
            ADD COLUMN display_name VARCHAR(255) DEFAULT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'generations'
          AND column_name = 'name'
    ) THEN
        ALTER TABLE generations
            ADD COLUMN name VARCHAR(255) DEFAULT NULL;
    END IF;
END $$;
