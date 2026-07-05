"""
Testes para UserService e UserQueries.

Cobre:
  JWT — criação e verificação de tokens
  get_user — por UUID, utilizador inexistente
  update_username — sucesso, vazio, duplicado, utilizador inexistente
  delete_user — sucesso, utilizador inexistente
  UserQueries — create, get_by_id, get_by_username, update, delete
"""

import uuid
import os
import pytest

# JWT_SECRET_KEY é definido em tests/conftest.py (antes de qualquer import de
# app.core.config) — ver o comentário lá para o porquê de não poder estar
# só aqui.

from app.services.user_service import UserService
from app.domain.result import Sucesso, Falha
from app.domain.errors.user_errors import (
    UtilizadorNaoEncontrado,
    UsernameInvalido,
    UsernameDuplicado,
)


# ---------------------------------------------------------------------------
# UserService — JWT (sem DB, funções puras)
# ---------------------------------------------------------------------------

class TestJWT:

    def _service(self):
        return UserService(db_session=None)

    def test_create_access_token_returns_string(self):
        """Assert: token é uma string não-vazia."""
        svc = self._service()
        token = svc.create_access_token("user-001")
        assert isinstance(token, str) and len(token) > 0

    def test_verify_token_returns_payload(self):
        """Assert: payload contém sub correcto."""
        svc = self._service()
        user_id = str(uuid.uuid4())
        token = svc.create_access_token(user_id)
        payload = svc.verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id

    def test_verify_token_invalid_returns_none(self):
        """Assert: token adulterado devolve None."""
        svc = self._service()
        assert svc.verify_token("not.a.valid.token") is None

    def test_verify_token_wrong_secret_returns_none(self):
        """Assert: token assinado com chave diferente é rejeitado.

        Nota: mudar `os.environ["JWT_SECRET_KEY"]` aqui não teria efeito --
        `settings` é um singleton com `@lru_cache` (app/core/config.py), já
        construído no import do módulo, por isso `UserService.__init__` leria
        sempre o mesmo valor independentemente do que a env var passasse a
        ter depois. Por isso simulamos a chave diferente diretamente na
        instância, que é o que `verify_token` de facto usa para validar a
        assinatura.
        """
        svc = self._service()
        token = svc.create_access_token("user-001")

        # Instância com uma chave secreta diferente da que assinou o token.
        svc2 = self._service()
        svc2.secret_key = "different-secret"

        assert svc2.verify_token(token) is None


# ---------------------------------------------------------------------------
# UserService — operações com DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUserServiceDB:

    async def test_get_user_returns_sucesso(self, async_db_session, db_user):
        """Assert: utilizador existente devolve Sucesso com o utilizador."""
        svc = UserService(db_session=async_db_session)
        result = await svc.get_user(db_user.id)
        assert isinstance(result, Sucesso)
        assert result.valor.id == db_user.id

    async def test_get_user_nonexistent_returns_falha(self, async_db_session):
        """Assert: UUID inexistente devolve Falha(UtilizadorNaoEncontrado)."""
        svc = UserService(db_session=async_db_session)
        result = await svc.get_user(uuid.uuid4())
        assert isinstance(result, Falha)
        assert isinstance(result.erro, UtilizadorNaoEncontrado)

    async def test_update_username_success(self, async_db_session, db_user):
        """Assert: username válido e único é persistido."""
        svc = UserService(db_session=async_db_session)
        result = await svc.update_username(db_user.id, "novousername")
        assert isinstance(result, Sucesso)
        assert result.valor.username == "novousername"

    async def test_update_username_strips_whitespace(self, async_db_session, db_user):
        """Assert: espaços em volta do username são removidos."""
        svc = UserService(db_session=async_db_session)
        result = await svc.update_username(db_user.id, "  limpo  ")
        assert isinstance(result, Sucesso)
        assert result.valor.username == "limpo"

    async def test_update_username_empty_returns_falha(self, async_db_session, db_user):
        """Assert: username vazio devolve Falha(UsernameInvalido)."""
        svc = UserService(db_session=async_db_session)
        result = await svc.update_username(db_user.id, "   ")
        assert isinstance(result, Falha)
        assert isinstance(result.erro, UsernameInvalido)

    async def test_update_username_duplicate_returns_falha(self, async_db_session, db_user):
        """Assert: username já em uso por outro utilizador → Falha(UsernameDuplicado)."""
        from app.data.queries import UserQueries
        # Criar segundo utilizador com username diferente
        outro = await UserQueries.create_user(
            db=async_db_session,
            username="outrouser",
            oauth_provider="google",
            oauth_id="google_outro_001",
        )

        svc = UserService(db_session=async_db_session)
        # Tentar dar ao db_user o username do outro
        result = await svc.update_username(db_user.id, "outrouser")
        assert isinstance(result, Falha)
        assert isinstance(result.erro, UsernameDuplicado)

    async def test_update_username_same_user_no_conflict(self, async_db_session, db_user):
        """Assert: utilizador pode re-submeter o seu próprio username sem conflito."""
        svc = UserService(db_session=async_db_session)
        result = await svc.update_username(db_user.id, db_user.username)
        assert isinstance(result, Sucesso)

    async def test_update_username_nonexistent_user(self, async_db_session):
        """Assert: UUID inexistente devolve Falha(UtilizadorNaoEncontrado)."""
        svc = UserService(db_session=async_db_session)
        result = await svc.update_username(uuid.uuid4(), "qualquer")
        assert isinstance(result, Falha)
        assert isinstance(result.erro, UtilizadorNaoEncontrado)

    async def test_delete_user_success(self, async_db_session, db_user):
        """Assert: utilizador eliminado não existe mais na DB."""
        svc = UserService(db_session=async_db_session)
        result = await svc.delete_user(db_user.id)
        assert isinstance(result, Sucesso)

        # Confirmar remoção
        get_result = await svc.get_user(db_user.id)
        assert isinstance(get_result, Falha)

    async def test_delete_user_nonexistent_returns_falha(self, async_db_session):
        """Assert: apagar UUID inexistente devolve Falha(UtilizadorNaoEncontrado)."""
        svc = UserService(db_session=async_db_session)
        result = await svc.delete_user(uuid.uuid4())
        assert isinstance(result, Falha)
        assert isinstance(result.erro, UtilizadorNaoEncontrado)


# ---------------------------------------------------------------------------
# UserQueries directas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUserQueries:

    async def test_create_user(self, async_db_session):
        """Assert: utilizador criado tem os campos corretos."""
        from app.data.queries import UserQueries
        user = await UserQueries.create_user(
            db=async_db_session,
            username="queryuser",
            oauth_provider="github",
            oauth_id="github_001",
        )
        assert user.username == "queryuser"
        assert user.oauth_provider == "github"
        assert user.id is not None

    async def test_get_user_by_id(self, async_db_session, db_user):
        """Assert: get_user_by_id devolve o utilizador correcto."""
        from app.data.queries import UserQueries
        found = await UserQueries.get_user_by_id(db=async_db_session, user_id=db_user.id)
        assert found is not None
        assert found.id == db_user.id

    async def test_get_user_by_id_missing(self, async_db_session):
        """Assert: UUID inexistente devolve None."""
        from app.data.queries import UserQueries
        found = await UserQueries.get_user_by_id(db=async_db_session, user_id=uuid.uuid4())
        assert found is None

    async def test_get_user_by_username(self, async_db_session, db_user):
        """Assert: pesquisa por username exacto devolve o utilizador."""
        from app.data.queries import UserQueries
        found = await UserQueries.get_user_by_username(
            db=async_db_session, username=db_user.username
        )
        assert found is not None
        assert found.username == db_user.username

    async def test_get_user_by_oauth(self, async_db_session, db_user):
        """Assert: pesquisa por OAuth provider+id devolve o utilizador."""
        from app.data.queries import UserQueries
        found = await UserQueries.get_user_by_oauth(
            db=async_db_session,
            oauth_provider="google",
            oauth_id="google_test_001",
        )
        assert found is not None
        assert found.id == db_user.id

    async def test_update_user_username(self, async_db_session, db_user):
        """Assert: update_user persiste o novo username."""
        from app.data.queries import UserQueries
        updated = await UserQueries.update_user(
            db=async_db_session,
            user_id=db_user.id,
            username="updatedname",
        )
        assert updated.username == "updatedname"

    async def test_delete_user(self, async_db_session, db_user):
        """Assert: delete_user devolve True e o utilizador desaparece da DB."""
        from app.data.queries import UserQueries
        ok = await UserQueries.delete_user(db=async_db_session, user_id=db_user.id)
        assert ok is True
        found = await UserQueries.get_user_by_id(db=async_db_session, user_id=db_user.id)
        assert found is None
