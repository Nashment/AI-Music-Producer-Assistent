# OAuth - Implementação Atual

## O que está implementado no código

### Endpoints ativos

- `GET /api/v1/users/auth/google/login`
- `GET /api/v1/users/auth/google/callback?code=...`
- `GET /api/v1/users/me` (JWT)
- `PUT /api/v1/users/me` (JWT)
- `DELETE /api/v1/users/me` (JWT)

### Serviço

Implementado em `backend/app/services/user_service.py`:
- construção da URL de autorização Google
- troca de `code` por token Google
- leitura do user info Google
- criação/obtenção de utilizador por `oauth_provider + oauth_id`
- emissão e validação de JWT

### Persistência

Modelos em `backend/app/data/models.py`:
- `User` com `oauth_provider` e `oauth_id`
- `UniqueConstraint(oauth_provider, oauth_id)`

Operações OAuth em `backend/app/data/oauth_queries.py`.

## O que não está implementado como endpoint

- Login/callback GitHub
- Login/callback Microsoft

Apesar de existirem variáveis de ambiente para outros providers, o router atual de users expõe apenas Google.

## Fluxo real

1. Cliente chama `GET /api/v1/users/auth/google/login`
2. Backend devolve `authorization_url`
3. Utilizador autentica no Google
4. Google redireciona para callback com `code`
5. Cliente chama `GET /api/v1/users/auth/google/callback?code=...`
6. Backend devolve JWT (`access_token`)
7. Cliente usa `Authorization: Bearer <token>` nas rotas protegidas
