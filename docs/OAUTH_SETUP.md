# OAuth Setup (Estado Atual)

Este projeto expõe endpoints OAuth apenas para Google.

## 1. Variáveis necessárias

No ficheiro de ambiente usado pela app (ex.: `docker/.env`):

```env
GOOGLE_CLIENT_ID=seu_client_id
GOOGLE_CLIENT_SECRET=seu_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/users/auth/google/callback

JWT_SECRET_KEY=trocar_isto_em_producao
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

## 2. Endpoints ativos

- `GET /api/v1/users/auth/google/login`
- `GET /api/v1/users/auth/google/callback?code=...`

## 3. Fluxo de teste manual

1. Chamar login:

```bash
curl http://localhost:8000/api/v1/users/auth/google/login
```

2. Abrir `authorization_url` no browser e autenticar.
3. Obter `code` devolvido pelo Google.
4. Chamar callback:

```bash
curl "http://localhost:8000/api/v1/users/auth/google/callback?code=SEU_CODE"
```

5. Usar `access_token` nas rotas protegidas:

```text
Authorization: Bearer <token>
```

## 4. Validar token

Exemplo:

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 5. Nota sobre outros providers

Mesmo que existam chaves de GitHub/Microsoft no `.env`, os endpoints desses providers não estão implementados no router atual.
