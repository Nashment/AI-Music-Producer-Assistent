# Frontend — Music AI

Aplicação **Vite + React 19 + TypeScript** para o backend FastAPI em `../backend/`.

Implementa o fluxo completo do produto:

```
Project ─▶ Audio (upload do utilizador) ─▶ Generation (IA) ─▶ Cut (clip da geração)
```

| Entidade   | Tabela / Endpoint base       | UI                                         |
|------------|------------------------------|--------------------------------------------|
| Project    | `projects`                   | `/projects`, `/projects/:id`               |
| Audio      | `audio_files`                | filhos de um project                       |
| Generation | `generations` (raiz)         | árvore lateral em `audioDetail`            |
| Cut        | `generations` + `parent_generation_id` | filhos da geração na mesma árvore |

**Cuts são generations** com `parent_generation_id` populado — partilham
a mesma tabela e o mesmo endpoint base, o que mantém a API ortogonal.

---

## Como arrancar

Há dois modos: **Docker (tudo de uma vez)** ou **dev nativo (HMR rápido)**.

### Modo 1 — Docker Compose (recomendado para demos)

Levanta Postgres, Redis, backend, worker, pgAdmin **e** o frontend num só
comando:

```bash
cd docker
docker compose up --build
```

> **Migração da BD:** os ficheiros `docker/SQL/01_init_schema.sql`,
> `02_create_tables.sql` e `03_migrations.sql` são executados pelo Postgres
> via `docker-entrypoint-initdb.d/` apenas **na primeira vez** que o
> volume é criado. Se já tens uma BD a correr de antes desta feature,
> aplica a migração 002 manualmente:
>
> ```bash
> docker compose exec postgres \
>   psql -U music_user -d music_ai_db -f /docker-entrypoint-initdb.d/03_migrations.sql
> ```
>
> ou simplesmente apaga o volume e re-cria do zero:
> `docker compose down -v && docker compose up --build`.

Endpoints (no host):

| Serviço         | URL                       |
|-----------------|---------------------------|
| **Frontend**    | http://localhost:5173     |
| Backend (raw)   | http://localhost:8000     |
| pgAdmin         | http://localhost:5050     |
| Postgres        | localhost:5432            |
| Redis           | localhost:6379            |

O frontend é um build estático Vite servido por nginx. O nginx ainda faz
proxy de `/api/*` para o container `backend:8000/api/v1/*` — ou seja, do
ponto de vista do browser está tudo na mesma origin (porta 5173) e não há
qualquer dance de CORS.

> Para mudar a porta exposta do frontend, define `FRONTEND_PORT` no
> `docker/.env` (ex.: `FRONTEND_PORT=80`). Lembra-te depois de actualizar o
> redirect URI no Google Cloud Console e a allowlist `CORS_ORIGINS` em
> `backend/app/core/config.py`.

### Modo 2 — Dev nativo (iteração rápida com HMR)

Para mexer no frontend ao vivo (HMR, source maps confortáveis), continua a
fazer mais sentido correr o Vite directamente:

```bash
cd frontend
npm install     # também puxa wavesurfer.js para a waveform de corte
npm run dev
```

A aplicação abre em **http://localhost:5173** e o Vite faz proxy de
`/api/*` para `http://localhost:8000/api/v1/*` (ver `vite.config.ts`). Para
isto funcionar, o backend tem de estar a correr — podes levantar só os
serviços de backend com:

```bash
cd docker
docker compose up postgres redis backend celery_worker
```

> Atenção: se o container `frontend` também estiver a correr na porta 5173
> ao mesmo tempo que o `npm run dev`, vais ter conflito de porta. Pára o
> container ou muda `FRONTEND_PORT`.

### Outros comandos

```bash
npm run build       # tsc + bundle de produção (./dist)
npm run preview     # serve o build local sem nginx
```

---

## Pré-requisitos

| Ferramenta             | Versão recomendada |
|------------------------|--------------------|
| Docker + Compose       | ≥ 24               |
| Node.js (só dev nativo)| ≥ 20               |
| npm (só dev nativo)    | ≥ 10               |

E claro: Google OAuth configurado (ver `backend/.env` / `docs/OAUTH_SETUP.md`).

> **Importante para o OAuth:** o redirect URI registado na Google Cloud
> Console tem de apontar para o **backend** (ex.:
> `http://localhost:8000/api/v1/users/auth/google/callback`). O backend é
> que faz a troca pelo JWT — o frontend só recebe o `code` no seu callback
> (`http://localhost:5173/auth/callback`).

---

## Funcionalidades já integradas

### 🔐 Autenticação (`/users`)
- Landing/login com botão **Continuar com Google**
  → `GET /users/auth/google/login`
- Callback (`/auth/callback`) troca o `code` por JWT
  → `GET /users/auth/google/callback?code=…`
- Token guardado em `localStorage` (`utils/auth.ts`).
- `ProtectedRoute` valida o token a cada montagem chamando
  `GET /users/me`.

### 👤 Perfil (`/profile`)
- Lê o utilizador via `GET /users/me`.
- Edita o username via `PUT /users/me`.
- Apaga conta via `DELETE /users/me` (com confirmação modal).

### 🎼 Projetos (`/projects`)
- Lista, pesquisa e ordenação local (`GET /projects`).
- Criação em modal (`POST /projects`).
- Detalhe (`/projects/:id`) com edição em modal (`PUT /projects/:id`)
  e eliminação confirmada (`DELETE /projects/:id`).

### 🎧 Áudio (`/projects/:id/audio/:audioId`)
- Lista por projeto (`GET /audio/project/{projectId}`).
- Upload com **drag & drop** + validação de tamanho/formato
  (`POST /audio/project/{projectId}/upload`, multipart).
- Player com lazy-load (`GET /audio/{audioId}` retorna o blob).
- Painel de operações:
  - **Ajustar BPM** (`POST /audio/{id}/adjust-bpm?target_bpm=`).
  - **Cortar excerto** (`POST /audio/{id}/cut?inicio_segundos=&fim_segundos=`).
  - **Separar instrumento** (`POST /audio/{id}/separate-tracks?instrument=`)
    e download do WAV resultante.
- Eliminação (`DELETE /audio/{id}`).

### 🔮 Geração (em pausa)
Os ficheiros existem (`services/generation`, `hooks/generation`,
`components/Generation`, `pages/generationCreation.tsx`) e estão alinhados
com os endpoints actuais do backend, mas **não há rota activa**. Quando
quiseres ligar, basta:

1. Adicionar a rota em `src/main.tsx`:
   ```tsx
   import GenerationCreationPage from './pages/generationCreation';
   // …
   { path: '/projects/:projectId/audio/:audioId/generate', element: <GenerationCreationPage /> }
   ```
2. Adicionar um link/botão no `audioDetail.tsx` que vá para essa URL.

---

## Estrutura

```
frontend/
├── index.html                              # importa fontes (Inter) + CSS
├── package.json
├── tsconfig.json
├── vite.config.ts                          # proxy /api -> /api/v1
├── style/                                  # 1 CSS por área
│   ├── style.css                           # design system (tokens, botões, inputs, modal, toast…)
│   ├── layout.css                          # AppShell + AppHeader + PageHeader
│   ├── authentication.css
│   ├── HomePage.css
│   ├── profile.css
│   ├── projects.css
│   ├── projectDetail.css
│   ├── audio.css
│   └── generation.css                      # (não usado por agora)
└── src/
    ├── main.tsx                            # router (públicas + protegidas em <AppLayout>)
    ├── components/
    │   ├── ProtectedRoute.tsx
    │   ├── Layout/
    │   │   ├── AppLayout.tsx               # shell com <AppHeader> + <Outlet>
    │   │   ├── AppHeader.tsx               # nav global + user menu
    │   │   ├── PageHeader.tsx              # título/descrição/ações por página
    │   │   ├── Spinner.tsx
    │   │   ├── EmptyState.tsx
    │   │   ├── Modal.tsx                   # acessível (Esc + backdrop + body lock)
    │   │   ├── ConfirmDialog.tsx           # acima de Modal
    │   │   └── Toast.tsx                   # ToastProvider + useToast()
    │   ├── Home/HomeElements.tsx
    │   ├── Project/{ProjectCard,ProjectList,ProjectForm,ProjectError,ProjectLoading}.tsx
    │   ├── Audio/{AudioCard,AudioList,AudioUpload,AudioPlayer,AudioToolsPanel,AudioDetails}.tsx
    │   └── Generation/{GenerationCard,GenerationList,GenerationForm}.tsx   # standby
    ├── hooks/
    │   ├── auth/useAuth.ts
    │   ├── project/{projectReducer,useProjectActions,useProjects,useProject}.ts
    │   ├── audio/{audioReducer,useAudioActions,useAudios}.ts
    │   └── generation/{generationReducer,useGenerationActions,useGenerationSubscription,useGeneration}.ts
    ├── pages/
    │   ├── authentication.tsx              # /  e  /login
    │   ├── oauthCallback.tsx                # /auth/callback
    │   ├── HomePage.tsx                     # /home
    │   ├── profile.tsx                      # /profile
    │   ├── projects.tsx                     # /projects
    │   ├── projectDetail.tsx                # /projects/:projectId
    │   ├── audioDetail.tsx                  # /projects/:projectId/audio/:audioId
    │   ├── generationCreation.tsx           # standby (não montada)
    │   └── logout.tsx                       # /logout
    ├── services/
    │   ├── request.ts                       # fetch + Bearer JWT + Problem Details → ApiError
    │   ├── user/{userService,userResponseTypes}.ts
    │   ├── project/{projectService,projectResponseTypes}.ts
    │   ├── audio/{audioService,audioResponseTypes}.ts
    │   └── generation/{generationService,generationResponseTypes}.ts
    └── utils/
        ├── common.ts                        # BASE_URL = '/api'
        └── auth.ts                          # save/get/clear do JWT em localStorage
```

---

## Padrões seguidos do projeto Kotlin

- **Pages thin**: cada página delega o estado a um hook do domínio.
- **Hooks por domínio**: trio `xxxReducer.ts` + `useXxxActions.ts`
  (+ `useXxxSubscription.ts` quando há streaming/polling) + `useXxx.ts` que
  combina tudo. Mesmo desenho do `useGame` / `useLobbyRoom` do trabalho original.
- **Services**: métodos puros que recebem inputs tipados e devolvem
  `Promise<XxxResponse>`. Erros do backend (Problem Details RFC 7807) são
  normalizados em `ApiError` por `services/request.ts`.

## Diferenças face ao projeto Kotlin

- Autenticação por **Bearer JWT**, não cookie de sessão (backend stateless).
- Login só por **Google OAuth** — não há registo manual.
- Em vez de SSE há **polling** em `useGenerationSubscription` (não usado por agora).

---

## Troubleshooting

**Em modo Docker, o frontend abre mas os pedidos /api/* dão 502/504.**
O nginx do container `frontend` faz proxy para o hostname `backend` (rede
Docker `music_ai_network`). Confirma que o serviço `backend` está saudável:
`docker compose ps`. Se reiniciaste só o backend, o nginx pode estar com
DNS em cache: `docker compose restart frontend`.

**Em modo dev nativo, “CORS error” / pedidos não chegam ao backend.**
Verifica `vite.config.ts`: o proxy aponta para `http://localhost:8000`. Se
o backend está noutra porta ou host, ajusta aí. O frontend só faz pedidos
a `/api/...`, que o Vite reescreve para `/api/v1/...`.

**Login não funciona / “redirect_uri_mismatch”.**
O *Authorized redirect URI* na Google Cloud Console tem de bater certo com o
configurado no backend (ex.: `http://localhost:8000/api/v1/users/auth/google/callback`).
Se quiseres usar a app em produção, regista também o redirect público.

**“Not authenticated” mesmo depois de login.**
Confirma o JWT em DevTools → Application → Local Storage
(`music_ai.access_token`). O `request.ts` envia esse token em
`Authorization: Bearer <token>`. Se o backend reiniciou e a chave HMAC
mudou, faz logout e volta a entrar.

**Mudei o código e não vejo nada.**
- Em **Docker**: o container serve um build estático. Tens de o reconstruir:
  `docker compose up --build frontend` (ou `docker compose build frontend`
  + restart).
- Em **dev nativo**: HMR é automático. Se não actualizar, reinicia
  `npm run dev`.
