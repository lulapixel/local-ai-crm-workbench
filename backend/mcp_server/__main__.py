"""Ponto de entrada do servidor MCP do ProspectOS (python -m mcp_server)."""

import logging
import sys
from logging.handlers import RotatingFileHandler
import paths
from mcp_server.server import create_mcp_server


def setup_logging() -> None:
    """Configura o sistema de logs para que NENHUM log vá para o stdout (reservado ao protocolo stdio MCP)."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # setup_logging pode ser chamado novamente por harnesses/embutidores. Não
    # acumular handlers evita mensagens duplicadas e locks desnecessários.
    for handler in list(root_logger.handlers):
        if getattr(handler, "_prospectos_mcp_managed", False):
            root_logger.removeHandler(handler)
            handler.close()

    try:
        paths.garantir_pastas_de_dados()
        pasta_logs = paths.DIR_DADOS / "logs"
        pasta_logs.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        pasta_logs = None
        erro_log = erro
    else:
        erro_log = None

    file_handler = None
    if pasta_logs is not None:
        try:
            # Handler para arquivo rotativo
            file_handler = RotatingFileHandler(
                pasta_logs / "mcp.log",
                maxBytes=2_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        except OSError as erro:
            erro_log = erro

    if file_handler is not None:
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        file_handler._prospectos_mcp_managed = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)

    # Handler para stderr (diagnóstico sem corromper stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s]: %(message)s"))
    stderr_handler._prospectos_mcp_managed = True  # type: ignore[attr-defined]
    root_logger.addHandler(stderr_handler)
    if erro_log is not None:
        root_logger.warning("log MCP em arquivo indisponível; usando stderr temporariamente (%s)", erro_log)


def main() -> None:
    """Inicializa o servidor MCP em transporte stdio."""
    setup_logging()
    logger = logging.getLogger("prospectos.mcp")
    logger.info("Iniciando servidor MCP ProspectOS no transporte stdio...")

    try:
        mcp_app = create_mcp_server()
        mcp_app.run(transport="stdio")
    except Exception as exc:
        logger.critical("Encerrando servidor MCP devido a erro crítico: %s", str(exc), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
