# =============================================================================
# Frontend Dockerfile — Multi-stage
#
# Stage 1: Node compila o bundle de producao para /app/dist.
# Stage 2: Nginx serve esse /dist e faz proxy de /api/* para o backend.
#
# A imagem final tem ~25MB (apenas nginx-alpine + assets estaticos).
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — build
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependencias primeiro (boa cache: so reinstala se package*.json mudar)
COPY package.json package-lock.json* ./
RUN npm ci

# Copia o resto do projecto e cria o bundle
COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2 — serve via Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine

# Configuracao custom (SPA fallback + proxy /api -> backend:8000/api/v1)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia os ficheiros estaticos compilados
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
