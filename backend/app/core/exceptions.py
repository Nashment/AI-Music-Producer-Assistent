"""
Hierarquia de exceções de domínio da aplicação.

Cada exceção carrega toda a informação necessária para gerar uma resposta
RFC 7807 Problem Details sem lógica adicional no endpoint.

Uso nos serviços/endpoints:
    raise RecursoNaoEncontrado("áudio", audio_id)
    raise AcessoNegado()
    raise RequisicaoInvalida("audio_weight deve estar entre 0.0 e 1.0.")
    raise ErroProcessamento("Falha na extração MIDI.")
"""

from typing import Any, Optional


class AppException(Exception):
    """Exceção base — todas as exceções de domínio herdam daqui."""

    status_code: int = 500
    error_type: str = "erro-interno"
    title: str = "Erro Interno do Servidor"

    def __init__(self, detail: str, **extra: Any):
        self.detail = detail
        # Campos adicionais opcionais incluídos no body da resposta
        # (ex: recurso="áudio", identificador="abc-123")
        self.extra: dict[str, Any] = {k: v for k, v in extra.items() if v is not None}
        super().__init__(detail)

    @property
    def type_uri(self) -> str:
        return f"/errors/{self.error_type}"


# ---------------------------------------------------------------------------
# 4xx — Erros do cliente
# ---------------------------------------------------------------------------

class RecursoNaoEncontrado(AppException):
    """404 — O recurso pedido não existe ou não é visível pelo utilizador."""

    status_code = 404
    error_type = "recurso-nao-encontrado"
    title = "Recurso Não Encontrado"

    def __init__(self, recurso: str, identificador: Any = None):
        if identificador is not None:
            detail = f"'{recurso}' com identificador '{identificador}' não foi encontrado."
        else:
            detail = f"'{recurso}' não foi encontrado."
        super().__init__(detail, recurso=recurso, identificador=str(identificador) if identificador else None)


class AcessoNegado(AppException):
    """404 (público) / 403 (interno) — Recurso inexistente ou sem permissão.

    Devolve 404 ao cliente para não confirmar a existência do recurso a quem
    não tem acesso (previne enumeração de IDs válidos).
    O log interno regista o tipo real do erro para debugging.
    """

    # Público: 404 para não vazar existência do recurso
    status_code = 404
    error_type = "recurso-nao-encontrado"
    title = "Recurso Não Encontrado"

    def __init__(self, detail: str = "O recurso não foi encontrado ou não tem permissão para aceder."):
        super().__init__(detail)


class RequisicaoInvalida(AppException):
    """400 — O pedido contém dados inválidos detetados pela lógica de negócio."""

    status_code = 400
    error_type = "requisicao-invalida"
    title = "Requisição Inválida"


class RecursoJaExiste(AppException):
    """409 — Tentativa de criar um recurso que já existe."""

    status_code = 409
    error_type = "recurso-ja-existe"
    title = "Recurso Já Existe"

    def __init__(self, recurso: str, detalhe: Optional[str] = None):
        detail = detalhe or f"'{recurso}' já existe."
        super().__init__(detail, recurso=recurso)


class ServicoIndisponivel(AppException):
    """501 — Funcionalidade não disponível neste ambiente (módulo opcional em falta)."""

    status_code = 501
    error_type = "servico-indisponivel"
    title = "Funcionalidade Não Disponível"


# ---------------------------------------------------------------------------
# 4xx/5xx — Erros de processamento
# ---------------------------------------------------------------------------

class ErroProcessamento(AppException):
    """422 — A operação falhou por um problema no conteúdo fornecido (ex: áudio inválido)."""

    status_code = 422
    error_type = "erro-processamento"
    title = "Erro de Processamento"


class ErroInterno(AppException):
    """500 — Erro interno deliberado (ex: dependência indisponível, estado inesperado)."""

    status_code = 500
    error_type = "erro-interno"
    title = "Erro Interno do Servidor"
