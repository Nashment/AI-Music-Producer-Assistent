"""
Erros de dominio da geracao de musica.

Estes nao sao excecoes HTTP -- sao valores que descrevem o que correu
mal em linguagem de negocio. A traducao para HTTP status codes e
Problem Details acontece exclusivamente no endpoint.

Equivalente ao sealed class do Kotlin:
    sealed class GeneracaoErro
    data class AudioNaoEncontrado(val audioId: UUID) : GeneracaoErro()
    ...
"""

from dataclasses import dataclass
from typing import Any


class GeneracaoErro:
    """Classe base para todos os erros de dominio da geracao."""


@dataclass(frozen=True)
class AudioNaoEncontrado(GeneracaoErro):
    """O audio referenciado nao existe ou nao pertence ao utilizador."""
    audio_id: Any = None


@dataclass(frozen=True)
class GeracaoNaoEncontrada(GeneracaoErro):
    """A geracao pedida nao existe ou nao pertence ao utilizador."""
    generation_id: str = ""


@dataclass(frozen=True)
class CoverUrlInvalido(GeneracaoErro):
    """O upload_url fornecido para cover nao e uma URL publica (http/https)."""
    url_recebido: str = ""


@dataclass(frozen=True)
class PesoAudioInvalido(GeneracaoErro):
    """O audio_weight esta fora do intervalo [0.0, 1.0]."""
    valor: float = 0.0


@dataclass(frozen=True)
class WorkerIndisponivel(GeneracaoErro):
    """O modulo de worker Celery nao esta disponivel neste ambiente."""
    detalhe: str = ""


@dataclass(frozen=True)
class FilaIndisponivel(GeneracaoErro):
    """Nao foi possivel enfileirar a tarefa no Celery/Redis."""
    detalhe: str = ""


@dataclass(frozen=True)
class FalhaProcessamentoAudio(GeneracaoErro):
    """A operacao de processamento de audio falhou (ex: extracao MIDI, compilacao PDF)."""
    operacao: str = ""
