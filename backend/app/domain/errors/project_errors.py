"""
Erros de dominio de projetos.

Valores que descrevem o que correu mal em linguagem de negocio.
A traducao para HTTP status codes e Problem Details acontece
exclusivamente no endpoint.
"""

from dataclasses import dataclass
from typing import Any


class ProjetoErro:
    """Classe base para todos os erros de dominio de projeto."""


@dataclass(frozen=True)
class ProjetoNaoEncontrado(ProjetoErro):
    """O projeto nao existe ou nao pertence ao utilizador."""
    project_id: Any = None


@dataclass(frozen=True)
class TituloProjetoInvalido(ProjetoErro):
    """O titulo do projeto esta vazio ou invalido."""


@dataclass(frozen=True)
class TituloProjetoDuplicado(ProjetoErro):
    """Ja existe um projeto com este titulo para este utilizador."""
    titulo: str = ""
