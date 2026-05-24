# ============================================================
#  Dockerfile — Backend API (FastAPI)
#  Imagem leve: sem PyTorch/Demucs/ML. Build rapido.
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Dependencias de sistema minimas para o backend
RUN apt-get update && apt-get install -y --no-install-recommends     libpq-dev     && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (camada cacheada separada do codigo)
COPY docker/requirements-api.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo da aplicacao
COPY backend/ /app/

RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
