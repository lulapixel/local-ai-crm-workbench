"""Códigos e tratamento de erros padronizados para o MCP do ProspectOS."""

from typing import Any, Dict


class MCPError(Exception):
    """Exceção base para erros traduzidos no servidor MCP."""

    def __init__(self, codigo: str, mensagem: str, detalhes: Any = None):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "codigo": self.codigo,
            "mensagem": self.mensagem,
        }
        if self.detalhes is not None:
            res["detalhes"] = self.detalhes
        return res


def format_error_response(codigo: str, mensagem: str, detalhes: Any = None) -> Dict[str, Any]:
    """Retorna uma resposta estruturada de erro padronizada."""
    err: Dict[str, Any] = {
        "codigo": codigo,
        "mensagem": mensagem,
    }
    if detalhes is not None:
        err["detalhes"] = detalhes
    return {
        "ok": False,
        "erro": err,
    }
