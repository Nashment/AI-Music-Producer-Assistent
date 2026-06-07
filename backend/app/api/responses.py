"""
Helpers partilhados para respostas HTTP nos endpoints.

Evita duplicação de _problem_json e _handle_result em cada ficheiro de endpoint.
"""

from typing import Callable

from fastapi.responses import JSONResponse, Response

from app.domain.result import Sucesso, Falha


def problem_json(
    status_code: int,
    type_slug: str,
    title: str,
    detail: str,
    instance: str,
) -> JSONResponse:
    """Constrói uma resposta Problem Details (RFC 7807)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "type":     f"/errors/{type_slug}",
            "title":    title,
            "status":   status_code,
            "detail":   detail,
            "instance": instance,
        },
        media_type="application/problem+json",
    )


def handle_result(
    resultado: Sucesso | Falha,
    instance: str,
    on_error: Callable,
    success_factory: Callable,
) -> Response:
    """Despacha um Resultado para o handler de erro ou para a factory de sucesso.

    Args:
        resultado:       Sucesso ou Falha devolvido pelo serviço.
        instance:        Path do endpoint (para o campo "instance" do Problem Details).
        on_error:        Função (erro, instance) -> JSONResponse para tratar falhas.
        success_factory: Função (valor) -> Response para construir a resposta de sucesso.
    """
    match resultado:
        case Falha(erro=erro):
            return on_error(erro, instance)
        case Sucesso(valor=valor):
            return success_factory(valor)
