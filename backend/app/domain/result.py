"""
Tipo genérico Result — equivalente ao Either<E, T> do Kotlin.

Permite que serviços comuniquem sucesso ou falha de negócio como valores
explícitos no tipo de retorno, em vez de exceções.

Uso:
    # No serviço:
    async def criar_algo(...) -> Resultado[MeuErro, MeuValor]:
        if condicao_de_erro:
            return Falha(MeuErro.NaoEncontrado())
        return Sucesso(valor)

    # No endpoint:
    match await servico.criar_algo(...):
        case Falha(erro=erro):
            return _handle_meu_erro(erro, instance)
        case Sucesso(valor=resultado):
            return JSONResponse(status_code=201, content=resultado.model_dump())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Sucesso(Generic[T]):
    """Representa uma operação bem-sucedida com o seu valor resultante."""
    valor: T


@dataclass(frozen=True)
class Falha(Generic[E]):
    """Representa uma falha de negócio com o seu erro descritivo."""
    erro: E


# Alias de tipo — usar como anotação de retorno nos serviços:
#   async def submit(...) -> Resultado[GeneracaoErro, Generation]
Resultado = Union[Sucesso[T], Falha[E]]
