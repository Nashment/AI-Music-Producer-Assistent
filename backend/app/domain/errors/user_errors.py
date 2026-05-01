"""
Erros de dominio de utilizador.

Valores que descrevem o que correu mal em linguagem de negocio.
A traducao para HTTP status codes e Problem Details acontece
exclusivamente no endpoint.
"""

from dataclasses import dataclass
from typing import Any


class UtilizadorErro:
    """Classe base para todos os erros de dominio de utilizador."""


@dataclass(frozen=True)
class UtilizadorNaoEncontrado(UtilizadorErro):
    """O utilizador nao existe."""
    user_id: Any = None


@dataclass(frozen=True)
class UsernameInvalido(UtilizadorErro):
    """O username esta vazio ou invalido."""


@dataclass(frozen=True)
class UsernameDuplicado(UtilizadorErro):
    """O username ja esta em uso por outro utilizador."""
    username: str = ""


@dataclass(frozen=True)
class FalhaAutenticacaoGoogle(UtilizadorErro):
    """A autenticacao com o Google falhou."""
    detalhe: str = ""
