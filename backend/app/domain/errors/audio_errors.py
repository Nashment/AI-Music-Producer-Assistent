"""
Erros de dominio de audio.

Valores que descrevem o que correu mal em linguagem de negocio.
A traducao para HTTP status codes e Problem Details acontece
exclusivamente no endpoint.
"""

from dataclasses import dataclass
from typing import Any


class AudioErro:
    """Classe base para todos os erros de dominio de audio."""


@dataclass(frozen=True)
class AudioNaoEncontrado(AudioErro):
    """O audio nao existe ou nao pertence ao utilizador."""
    audio_id: Any = None


@dataclass(frozen=True)
class ProjetoNaoEncontrado(AudioErro):
    """O projeto nao existe ou nao pertence ao utilizador."""
    project_id: Any = None


@dataclass(frozen=True)
class FormatoAudioInvalido(AudioErro):
    """A extensao do ficheiro nao e suportada."""
    extensao: str = ""


@dataclass(frozen=True)
class FicheiroAudioGrande(AudioErro):
    """O ficheiro excede o limite de tamanho permitido."""
    tamanho_mb: float = 0.0


@dataclass(frozen=True)
class FicheiroFisicoNaoEncontrado(AudioErro):
    """O registo existe na BD mas o ficheiro fisico foi eliminado."""
    audio_id: Any = None


@dataclass(frozen=True)
class ModuloAudioIndisponivel(AudioErro):
    """O modulo de processamento nao esta disponivel neste ambiente."""
    modulo: str = ""


@dataclass(frozen=True)
class FalhaProcessamento(AudioErro):
    """Operacao de processamento de audio falhou."""
    operacao: str = ""


@dataclass(frozen=True)
class IntervaloInvalido(AudioErro):
    """Os parametros de intervalo temporal sao invalidos."""
    detalhe: str = ""
