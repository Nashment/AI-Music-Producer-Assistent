"""
Handlers globais de erro — RFC 7807 Problem Details.

Registados uma única vez em main.py via configure_error_handlers(app).
Todos os endpoints ficam sem try/except: qualquer exceção é apanhada aqui,
convertida para o formato Problem Details e registada em log com um trace_id.

Formato da resposta (Content-Type: application/problem+json):
    {
        "type":     "/errors/<slug>",          # URI que identifica o tipo de erro
        "title":    "Recurso Não Encontrado",  # Descrição legível (não muda entre pedidos)
        "status":   404,                       # Idêntico ao HTTP status code
        "detail":   "Áudio '...' não encontrado.", # Mensagem específica deste pedido
        "instance": "/api/v1/audio/...",       # Path do endpoint que originou o erro
        "trace_id": "a1b2c3d4"                 # ID para correlacionar com os logs
    }

Para erros 5xx o "detail" público é propositadamente vago para não expor
informação interna — o traceback completo fica nos logs com o mesmo trace_id.
"""

import logging
import traceback
import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger("music_ai.errors")

# ---------------------------------------------------------------------------
# Mapeamento de títulos e type URIs para HTTPExceptions nativas do FastAPI
# ---------------------------------------------------------------------------
_STATUS_TITLES: dict[int, str] = {
    400: "Requisição Inválida",
    401: "Não Autenticado",
    403: "Acesso Negado",
    404: "Recurso Não Encontrado",
    405: "Método Não Permitido",
    409: "Conflito",
    415: "Tipo de Media Não Suportado",
    422: "Erro de Validação",
    429: "Demasiados Pedidos",
    500: "Erro Interno do Servidor",
    501: "Funcionalidade Não Implementada",
    503: "Serviço Indisponível",
}

_STATUS_TYPE_URIS: dict[int, str] = {
    400: "/errors/requisicao-invalida",
    401: "/errors/nao-autenticado",
    403: "/errors/acesso-negado",
    404: "/errors/recurso-nao-encontrado",
    409: "/errors/conflito",
    422: "/errors/validacao",
    500: "/errors/erro-interno",
    501: "/errors/nao-implementado",
    503: "/errors/servico-indisponivel",
}

# ---------------------------------------------------------------------------
# Mapeamento de exceções nativas do Python para HTTP status
# (camada de compatibilidade — serviços antigos continuam a funcionar)
# ---------------------------------------------------------------------------
_BUILTIN_EXCEPTION_MAP: dict[type, tuple[int, str, str]] = {
    # (status_code, type_uri, title)
    #
    # NOTA DE SEGURANÇA — PermissionError → 404 (não 403):
    # Devolver 403 numa operação sobre um recurso específico confirma ao cliente
    # que esse recurso *existe*, permitindo enumeração de IDs válidos.
    # Ao devolver 404 tanto para "não existe" como para "existe mas não tens acesso",
    # não se vaza informação sobre a existência do recurso.
    # Os logs internos preservam a distinção real para debugging.
    ValueError:         (400, "/errors/requisicao-invalida",     "Requisição Inválida"),
    PermissionError:    (404, "/errors/recurso-nao-encontrado",  "Recurso Não Encontrado"),
    FileNotFoundError:  (404, "/errors/recurso-nao-encontrado",  "Recurso Não Encontrado"),
    NotImplementedError:(501, "/errors/nao-implementado",        "Funcionalidade Não Implementada"),
}

# ---------------------------------------------------------------------------
# Padrões de mensagem que podem conter informação interna sensível.
# Quando detetados no detail de uma exceção, o detalhe é sanitizado antes
# de ser enviado ao cliente (o original fica apenas nos logs).
# ---------------------------------------------------------------------------
import re as _re
_INTERNAL_PATTERNS = [
    _re.compile(r"/[a-zA-Z0-9_\-\.]+(?:/[a-zA-Z0-9_\-\.]+){2,}"),  # file paths (/app/worker/...)
    _re.compile(r"\b(?:[a-zA-Z]:\\[^\s]+)"),                          # Windows paths (C:\...)
    _re.compile(r"\btoken[=:\s]+\S+", _re.IGNORECASE),                # tokens
    _re.compile(r"\bapi[_-]?key[=:\s]+\S+", _re.IGNORECASE),         # api keys
    _re.compile(r"\b[a-f0-9]{32,}\b"),                                # hashes longas
]

def _sanitize_detail(detail: str) -> tuple[str, bool]:
    """Verifica se o detail contém informação interna e sanitiza se necessário.

    Returns:
        (detail_seguro, foi_sanitizado) — o detail a enviar ao cliente e
        um flag indicando se o original foi ocultado.
    """
    for pattern in _INTERNAL_PATTERNS:
        if pattern.search(detail):
            return "[detalhe omitido por segurança]", True
    return detail, False


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_trace_id(request: Request) -> str:
    """Reutiliza X-Request-ID do cliente ou gera um novo."""
    return request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]


def _problem_response(
    *,
    type_uri: str,
    title: str,
    status_code: int,
    detail: str,
    instance: Optional[str],
    trace_id: str,
    extra: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    """Constrói uma JSONResponse conforme RFC 7807."""
    body: dict[str, Any] = {
        "type":     type_uri,
        "title":    title,
        "status":   status_code,
        "detail":   detail,
        "instance": instance,
        "trace_id": trace_id,
    }
    if extra:
        body.update(extra)

    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """Trata as exceções de domínio definidas em app.core.exceptions."""
    trace_id = _get_trace_id(request)

    # Para erros de processamento (422/500) o detail pode vir de uma exceção interna
    # com paths ou outros dados sensíveis — sanitizar antes de enviar ao cliente.
    safe_detail, foi_sanitizado = _sanitize_detail(exc.detail)

    if exc.status_code >= 500:
        logger.error(
            "[%s] AppException %s em %s %s: %s",
            trace_id, exc.error_type, request.method, request.url.path, exc.detail,
            exc_info=True,
        )
        # Em 5xx nunca devolvemos o detail original, mesmo sem padrões sensíveis
        safe_detail = f"Ocorreu um erro inesperado. Referência: {trace_id}"
    elif foi_sanitizado:
        logger.warning(
            "[%s] Detail sanitizado em AppException %s: %s",
            trace_id, exc.error_type, exc.detail,
        )
    else:
        logger.info(
            "[%s] %s (%d) em %s: %s",
            trace_id, exc.error_type, exc.status_code, request.url.path, exc.detail,
        )

    return _problem_response(
        type_uri=exc.type_uri,
        title=exc.title,
        status_code=exc.status_code,
        detail=safe_detail,
        instance=str(request.url.path),
        trace_id=trace_id,
        extra=exc.extra or None,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Converte HTTPException do FastAPI/Starlette para Problem Details."""
    trace_id = _get_trace_id(request)
    title    = _STATUS_TITLES.get(exc.status_code, "Erro")
    type_uri = _STATUS_TYPE_URIS.get(exc.status_code, f"/errors/{exc.status_code}")
    detail   = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    if exc.status_code >= 500:
        logger.error(
            "[%s] HTTPException %d em %s %s: %s",
            trace_id, exc.status_code, request.method, request.url.path, detail,
        )
        detail = f"Ocorreu um erro inesperado. Referência: {trace_id}"
    else:
        logger.info(
            "[%s] HTTP %d em %s: %s",
            trace_id, exc.status_code, request.url.path, detail,
        )

    return _problem_response(
        type_uri=type_uri,
        title=title,
        status_code=exc.status_code,
        detail=detail,
        instance=str(request.url.path),
        trace_id=trace_id,
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Transforma erros de validação Pydantic em Problem Details com detalhe por campo."""
    trace_id = _get_trace_id(request)

    erros = []
    for error in exc.errors():
        # Remove "body" do início do path para não expor detalhes de serialização
        partes = [str(p) for p in error["loc"] if p != "body"]
        erros.append({
            "campo":    " → ".join(partes) if partes else "(raiz)",
            "mensagem": error["msg"],
            "tipo":     error["type"],
        })

    logger.info(
        "[%s] Erro de validação em %s: %s",
        trace_id, request.url.path, erros,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type":     "/errors/validacao",
            "title":    "Erro de Validação",
            "status":   422,
            "detail":   "O corpo do pedido contém campos inválidos ou em falta.",
            "instance": str(request.url.path),
            "trace_id": trace_id,
            "erros":    erros,
        },
        media_type="application/problem+json",
    )


async def _handle_builtin_exception(request: Request, exc: Exception) -> JSONResponse:
    """Camada de compatibilidade: mapeia exceções nativas do Python para Problem Details.

    Permite que serviços existentes continuem a usar ValueError, PermissionError, etc.
    sem alterações, enquanto a resposta ao cliente segue o formato Problem Details.
    """
    trace_id = _get_trace_id(request)
    exc_type = type(exc)
    mapping  = _BUILTIN_EXCEPTION_MAP.get(exc_type)

    if mapping:
        status_code, type_uri, title = mapping
        raw_detail = str(exc)

        # Sanitizar o detail antes de enviar ao cliente —
        # o serviço pode incluir paths, tokens ou outros dados internos na mensagem.
        safe_detail, foi_sanitizado = _sanitize_detail(raw_detail)
        if foi_sanitizado:
            logger.warning(
                "[%s] Detail sanitizado em %s (continha informação interna): %s",
                trace_id, request.url.path, raw_detail,
            )
        else:
            logger.info(
                "[%s] %s (%d) em %s: %s",
                trace_id, exc_type.__name__, status_code, request.url.path, raw_detail,
            )

        return _problem_response(
            type_uri=type_uri,
            title=title,
            status_code=status_code,
            detail=safe_detail,
            instance=str(request.url.path),
            trace_id=trace_id,
        )

    # Exceção não reconhecida → 500 sem expor detalhes internos
    logger.error(
        "[%s] Exceção não tratada em %s %s:\n%s",
        trace_id, request.method, request.url.path,
        traceback.format_exc(),
    )
    return _problem_response(
        type_uri="/errors/erro-interno",
        title="Erro Interno do Servidor",
        status_code=500,
        detail=f"Ocorreu um erro inesperado. Referência: {trace_id}",
        instance=str(request.url.path),
        trace_id=trace_id,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def configure_error_handlers(app: FastAPI) -> None:
    """Regista todos os handlers na aplicação FastAPI.

    Chamar uma única vez em main.py, após criar a instância da app:
        configure_error_handlers(app)

    Ordem de registo é importante: handlers mais específicos primeiro.
    """
    app.add_exception_handler(AppException,            _handle_app_exception)     # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException,  _handle_http_exception)    # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError,  _handle_validation_error)  # type: ignore[arg-type]
    # Compatibilidade com serviços que usam exceções nativas do Python
    app.add_exception_handler(ValueError,              _handle_builtin_exception) # type: ignore[arg-type]
    app.add_exception_handler(PermissionError,         _handle_builtin_exception) # type: ignore[arg-type]
    app.add_exception_handler(FileNotFoundError,       _handle_builtin_exception) # type: ignore[arg-type]
    app.add_exception_handler(NotImplementedError,     _handle_builtin_exception) # type: ignore[arg-type]
    # Catch-all para tudo o resto
    app.add_exception_handler(Exception,               _handle_builtin_exception) # type: ignore[arg-type]
