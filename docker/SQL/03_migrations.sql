-- ==========================================
-- MIGRATIONS
-- ==========================================
-- Cada bloco usa IF EXISTS / DO $$ para ser idempotente
-- (pode ser executado múltiplas vezes sem erros).
--
-- NOTA: TODAS as migrações abaixo (001 a 005) já estão incorporadas em
-- 02_create_tables.sql -- uma instalação nova (`01_init_schema.sql` +
-- `02_create_tables.sql`) fica com o schema completo e atualizado sem
-- precisar de correr este ficheiro.
--
-- Este ficheiro so continua a ser necessario para atualizar bases de dados
-- ja existentes, criadas com versoes anteriores do schema (ex.: producao).
-- Sempre que 02_create_tables.sql for alterado para incluir uma coluna nova,
-- adiciona aqui o bloco ALTER TABLE idempotente correspondente, para quem
-- tiver uma base de dados antiga a poder atualizar.

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

-- ==========================================
-- Migração 005 — audio_files.project_id passa a obrigatório
-- ==========================================
-- Um AudioFile deixava de ter projeto (project_id = NULL) quando o projeto
-- era apagado (ON DELETE SET NULL), o que permitia áudios "órfãos" sem
-- projeto associado. Isso deixou de fazer sentido: um áudio só existe
-- dentro de um projeto. Passa a ser NOT NULL com ON DELETE CASCADE —
-- eliminar o projeto elimina agora também os áudios que lhe pertencem,
-- tal como já acontecia com generations.project_id.
--
-- NOTA: os audio_files órfãos existentes (project_id NULL) são apagados
-- antes de aplicar a restrição NOT NULL. Os objetos correspondentes no
-- Cloudflare R2 não são apagados por este script — se existirem órfãos,
-- os ficheiros no R2 devem ser limpos manualmente.
DO $$
BEGIN
    DELETE FROM audio_files WHERE project_id IS NULL;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audio_files'
          AND column_name = 'project_id'
          AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE audio_files
            ALTER COLUMN project_id SET NOT NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'audio_files'
          AND constraint_name = 'audio_files_project_id_fkey'
    ) THEN
        ALTER TABLE audio_files
            DROP CONSTRAINT audio_files_project_id_fkey;
    END IF;

    ALTER TABLE audio_files
        ADD CONSTRAINT audio_files_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
END $$;
