"""O transporte MCP nunca pode cair por ACL de arquivo de log."""

import logging
import sys

import mcp_server.__main__ as mcp_main


def _limpar_handlers_mcp():
    raiz = logging.getLogger()
    for handler in list(raiz.handlers):
        if getattr(handler, "_prospectos_mcp_managed", False):
            raiz.removeHandler(handler)
            handler.close()


def test_setup_logging_faz_fallback_para_stderr_se_log_estiver_bloqueado(tmp_path, monkeypatch):
    def falhar_handler(*args, **kwargs):
        raise PermissionError("mcp.log bloqueado")

    monkeypatch.setattr(mcp_main.paths, "DIR_DADOS", tmp_path / "dados")
    monkeypatch.setattr(mcp_main, "RotatingFileHandler", falhar_handler)
    try:
        mcp_main.setup_logging()
        handlers = [
            handler
            for handler in logging.getLogger().handlers
            if getattr(handler, "_prospectos_mcp_managed", False)
        ]
        assert len(handlers) == 1
        assert isinstance(handlers[0], logging.StreamHandler)
        assert handlers[0].stream is sys.stderr
        assert not (tmp_path / "dados" / "logs" / "mcp.log").exists()
    finally:
        _limpar_handlers_mcp()


def test_setup_logging_escreve_arquivo_quando_destino_esta_disponivel(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_main.paths, "DIR_DADOS", tmp_path / "dados")
    try:
        mcp_main.setup_logging()
        assert (tmp_path / "dados" / "logs" / "mcp.log").exists()
        managed = [
            handler
            for handler in logging.getLogger().handlers
            if getattr(handler, "_prospectos_mcp_managed", False)
        ]
        assert len(managed) == 2
    finally:
        _limpar_handlers_mcp()
