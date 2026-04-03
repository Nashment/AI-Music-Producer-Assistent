# 🔐 OAuth Configuration Guide

## Overview

O projeto agora usa **OAuth 2.0** para autenticação, eliminando a necessidade de guardar passwords na base de dados. Utilizadores fazem login via Google, GitHub ou Microsoft.

**Benefícios:**
- ✅ Sem passwords guardadas na DB
- ✅ Segurança gerida pelos provedores OAuth
- ✅ Login com 1-click
- ✅ Dados de utilizador sincronizados com provedores

---

## 🔧 Configuração de Cada Provider

### 1️⃣ **Google OAuth**

#### Passar 1: Criar Project no Google Cloud Console

1. Vai para [Google Cloud Console](https://console.cloud.google.com/)
2. Cria um novo project ou seleciona existente
3. Ativa a "Google+ API"
4. Em "Credentials", cria "OAuth 2.0 Client ID"
5. Choose "Web application"
6. Adiciona URIs autorizadas:
   ```
   http://localhost:3000
   http://localhost:3000/auth/google/callback
   ```

#### Passo 2: Guardar Credenciais

No `.env`:
```
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxx_xxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

---

### 2️⃣ **GitHub OAuth**

#### Passo 1: Registar OAuth App

1. Vai para [GitHub Settings → Developer Settings → OAuth Apps](https://github.com/settings/developers)
2. Clica "New OAuth App"
3. Preenche o formulário:
   - **Application name**: Musical AI Producer
   - **Homepage URL**: http://localhost:3000
   - **Authorization callback URL**: http://localhost:3000/auth/github/callback

#### Passo 2: Guardar Credenciais

No `.env`:
```
GITHUB_CLIENT_ID=xxxxxxxxxxxxx
GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REDIRECT_URI=http://localhost:3000/auth/github/callback
```

---

### 3️⃣ **Microsoft OAuth**

#### Passo 1: Registar App no Azure

1. Vai para [Azure Portal](https://portal.azure.com/)
2. "Azure Active Directory" → "App registrations"
3. "New registration"
4. Preenche o nome: "Musical AI Producer"
5. Em "Redirect URI", adiciona:
   ```
   http://localhost:3000/auth/microsoft/callback
   ```

#### Passo 2: Criar Client Secret

1. Em "Certificates & secrets", cria novo client secret
2. Copia o valor (só aparece uma vez!)

#### Passo 3: Guardar Credenciais

No `.env`:
```
MICROSOFT_CLIENT_ID=xxxxx-xxxxx-xxxxx-xxxxx
MICROSOFT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback
```

---

## 🔑 JWT Secret Key

**IMPORTANTE**: Muda isto em produção!

```bash
# Gerar uma chave segura:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Coloca em `.env`:
```
JWT_SECRET_KEY=your_generated_secret_key_here
```

---

## 📱 Fluxo de Login no Frontend

### Exemplo com React:

```jsx
// 1. Utilizador clica "Login with Google"
const loginWithGoogle = async () => {
  // Obtem authorization URL
  const response = await fetch('http://localhost:8000/api/v1/users/auth/google/login');
  const { authorization_url } = await response.json();
  
  // Redireciona para Google
  window.location.href = authorization_url;
};

// 2. Google redireciona back para callback com code
// (Frontend já está em /auth/google/callback?code=xxx)

// 3. Frontend envia code para backend
const handleGoogleCallback = async (code) => {
  const response = await fetch(
    'http://localhost:8000/api/v1/users/auth/google/callback',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    }
  );
  
  const { access_token, user } = await response.json();
  
  // Guarda token no localStorage
  localStorage.setItem('accessToken', access_token);
  
  // Redireciona para dashboard
  window.location.href = '/dashboard';
};

// 4. Usa token em chamadas à API
const fetchUserProfile = async () => {
  const token = localStorage.getItem('accessToken');
  
  const response = await fetch(
    'http://localhost:8000/api/v1/users/me',
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
};
```

---

## 🧪 Testar OAuth Localmente

### Via Curl:

```bash
# 1. Start Google OAuth flow
curl http://localhost:8000/api/v1/users/auth/google/login

# Response:
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "provider": "google"
}

# 2. (Manualmente) acessa authorization_url
# 3. Google redireciona com authorization code

# 3. Enviar authorization code para callback
curl -X POST http://localhost:8000/api/v1/users/auth/google/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "xxx"}'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "full_name": "User Name",
    "profile_picture_url": "https://..."
  }
}
```

---

## 📊 Database Schema

Utilizadores agora guardados assim:

```sql
SELECT 
  id, email, username,
  oauth_provider,      -- 'google', 'github', 'microsoft'
  oauth_id,            -- provider's user ID
  oauth_access_token,  -- for future API calls
  profile_picture_url,
  full_name
FROM users;
```

**Sem passwords!**

---

## 🔄 Exemplo Completo: Google Login

### 1. Frontend Inicia Login

```javascript
// Button click
const handleGoogleLogin = async () => {
  const res = await fetch('http://localhost:8000/api/v1/users/auth/google/login');
  const { authorization_url } = await res.json();
  window.location.href = authorization_url;
};
```

### 2. Utilizador Autentica no Google

(Google handles this)

### 3. Frontend Recebe Authorization Code

```javascript
// Callback page gets URL: ?code=4/0AY...
const code = new URLSearchParams(window.location.search).get('code');
```

### 4. Frontend Envia Code para Backend

```javascript
const res = await fetch(
  'http://localhost:8000/api/v1/users/auth/google/callback',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  }
);

const { access_token, user } = await res.json();
localStorage.setItem('token', access_token);
```

### 5. Backend

**app/api/endpoints/user.py:**
- `POST /auth/google/callback` recebe o code
- Chama `AuthService.oauth_login_google(code)`
- Troca code por token com Google API
- Cria/atualiza user na DB
- Retorna user info + JWT token

---

## 🛡️ Security Best Practices

1. **JWT Secret**: Muda em produção (já feito acima)
2. **HTTPS Only**: Em produção, força HTTPS
3. **Token Expiration**: Default é 24h (configure se necessário)
4. **Refresh Tokens**: (Optional) implementar para renovação

```python
# Em app/core/config.py
JWT_EXPIRATION_HOURS = 24  # Muda como necessário
```

5. **CORS**: Configura domains permitidos

```python
# Em app/core/config.py
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com"  # Production domain
]
```

---

## 🐛 Troubleshooting

### "Google CLIENT_ID not configured"

```bash
# Verifica se .env está carregado
echo $GOOGLE_CLIENT_ID

# Se em vazio, copia de .env.example e preenche
cp .env.example .env
# Edita .env com tuas credenciais
```

### "Invalid redirect URI"

- Verifica que Firebase/Azure registada os mesmos URIs
- Exemplo: `http://localhost:3000/auth/google/callback`
- CORS origins podem bloquear

### Token Expirado

```javascript
// Implementa refresh no frontend
if (error.status === 401) {
  // Token expirado, user faz login novamente
  handleLogout();
}
```

---

## 📚 Resources

- [Google OAuth Docs](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Docs](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [Microsoft OAuth Docs](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [JWT.io](https://jwt.io/)
- [Authlib Docs](https://authlib.org/)

---

## ✅ Checklist de Setup

- [ ] Google OAuth configured
- [ ] GitHub OAuth configured (optional)
- [ ] Microsoft OAuth configured (optional)
- [ ] `.env` preenchido com todas as chaves
- [ ] JWT_SECRET_KEY definido
- [ ] Frontend OAuth callback pages criadas
- [ ] Testou login end-to-end
- [ ] Verificou que user é guardado corretamente na DB
- [ ] Configurou HTTPS em produção

---

**Status**: OAuth pronto para usar! 🚀
