"""
StorageService - Cloudflare R2 (S3-compatible) storage abstraction.

Centraliza todas as operacoes de ficheiros na cloud para que o resto do
codigo nao saiba se esta a falar com disco local ou R2.

Convencao de chaves S3:
  - audio de upload do utilizador: audio/{uuid}_{filename}
  - audio gerado pelo Celery:      generations/{generation_id}.wav
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    """Wrapper fino sobre boto3 para operacoes no bucket R2."""

    def __init__(self):
        # O cliente boto3 e criado apenas na primeira utilizacao real (ver
        # propriedade `_client` abaixo), nao aqui. Isto e importante porque
        # `storage = StorageService()` e instanciado uma unica vez, a nivel
        # de modulo, assim que qualquer coisa importa este ficheiro -- se o
        # cliente fosse construido logo aqui, importar este modulo sem
        # R2_ACCOUNT_ID configurado (ex.: correr a suite de testes sem um
        # .env) rebentava com `ValueError: Invalid endpoint` antes de
        # qualquer teste chegar a correr, mesmo em testes que nunca tocam
        # storage a serio (todos usam mocks).
        self._client_instance = None
        self._bucket = settings.R2_BUCKET_NAME

    @property
    def _client(self):
        if self._client_instance is None:
            self._client_instance = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version="s3v4",
                    # R2 usa path-style; virtual-hosted falha em alguns ambientes
                    s3={"addressing_style": "path"},
                ),
                region_name="auto",
            )
        return self._client_instance

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """Faz upload de um ficheiro local para o R2. Devolve True em sucesso."""
        try:
            self._client.upload_file(local_path, self._bucket, s3_key)
            return True
        except Exception as e:
            print(f"[StorageService] Erro ao fazer upload de {local_path} -> {s3_key}: {e}")
            return False

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Descarrega um ficheiro do R2 para o disco local. Devolve True em sucesso."""
        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self._client.download_file(self._bucket, s3_key, local_path)
            return True
        except Exception as e:
            print(f"[StorageService] Erro ao descarregar {s3_key} -> {local_path}: {e}")
            return False

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_file(self, s3_key: str) -> bool:
        """Apaga um objecto do R2. Devolve True em sucesso (ou se nao existia)."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=s3_key)
            return True
        except Exception as e:
            print(f"[StorageService] Erro ao apagar {s3_key}: {e}")
            return False

    # ------------------------------------------------------------------
    # Presigned URLs
    # ------------------------------------------------------------------

    def get_presigned_url(
        self,
        s3_key: str,
        expiry_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """
        Gera uma presigned URL para download directo do R2.
        O cliente faz redirect para esta URL sem passar pelo backend.
        """
        expiry = expiry_seconds or settings.R2_PRESIGNED_URL_EXPIRY
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": s3_key},
                ExpiresIn=expiry,
            )
            return url
        except Exception as e:
            print(f"[StorageService] Erro ao gerar presigned URL para {s3_key}: {e}")
            return None

    # ------------------------------------------------------------------
    # Existencia
    # ------------------------------------------------------------------

    def file_exists(self, s3_key: str) -> bool:
        """Verifica se um objecto existe no bucket."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            print(f"[StorageService] Erro ao verificar existencia de {s3_key}: {e}")
            return False
        except Exception as e:
            print(f"[StorageService] Erro ao verificar existencia de {s3_key}: {e}")
            return False

    # ------------------------------------------------------------------
    # Utilitario: download para ficheiro temporario
    # ------------------------------------------------------------------

    @contextmanager
    def temp_download(self, s3_key: str, suffix: str = ""):
        """
        Context manager que descarrega s3_key para um ficheiro temporario,
        disponibiliza o Path e apaga-o automaticamente ao sair.

        Uso:
            with storage.temp_download("audio/abc.mp3", suffix=".mp3") as tmp_path:
                process(tmp_path)
            # ficheiro ja foi apagado
        """
        ext = suffix or Path(s3_key).suffix
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            ok = self.download_file(s3_key, str(tmp_path))
            if not ok:
                raise RuntimeError(f"Nao foi possivel descarregar {s3_key} do R2.")
            yield tmp_path
        finally:
            tmp_path.unlink(missing_ok=True)


# Instancia global reutilizavel (stateless - boto3 client e thread-safe)
storage = StorageService()
