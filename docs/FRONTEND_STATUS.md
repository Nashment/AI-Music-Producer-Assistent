# Frontend Status

## Estado atual no repositório

Frontend ainda não está implementado como aplicação funcional.

Existe atualmente:
- `frontend/src/components/` (vazio)
- `frontend/src/hooks/` (vazio)
- `frontend/src/pages/` (vazio)
- `frontend/src/services/` (vazio)
- `frontend/src/utils/` (vazio)
- `frontend/src/main.tsx` (vazio)
- `frontend/style/` (vazio)
- `frontend/tests/` (vazio)

Não existe atualmente:
- `package.json` em `frontend/`
- Configuração Vite/React
- Rotas/páginas/componentes implementados
- Integração API no frontend

## Implicações

- OAuth atualmente é tratado apenas no backend.
- Não há UI para iniciar login, gerir projetos ou visualizar gerações.
- Não há cliente web para upload de áudio no estado atual.

## Próximo passo natural

Criar base frontend (Vite + React + TypeScript), depois integrar:
1. Login Google (`/api/v1/users/auth/google/login`)
2. CRUD de projetos
3. Upload de áudio por projeto
4. Fluxo de geração e polling de status