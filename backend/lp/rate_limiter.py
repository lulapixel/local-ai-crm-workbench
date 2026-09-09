"""Proteção contra abuso e rate limiting para os endpoints públicos de Landing Pages.
"""

import time
from functools import wraps
from typing import Dict, List
from flask import jsonify, request

_REQUISICOES_IP: Dict[str, List[float]] = {}
_JANELA_SEGUNDOS = 60
_MAX_REQUISICOES = 60


def rate_limit_publico(max_req: int = _MAX_REQUISICOES, janela: int = _JANELA_SEGUNDOS):
    """Decorator de rate limiting em memória por IP para rotas públicas."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or "127.0.0.1"
            agora = time.time()
            historico = _REQUISICOES_IP.get(ip, [])

            # Filtra requisições dentro da janela temporal
            historico = [t for t in historico if agora - t < janela]

            if len(historico) >= max_req:
                return (
                    jsonify(
                        {
                            "erro": "Muitas requisições enviadas. Por favor, aguarde alguns instantes."
                        }
                    ),
                    429,
                )

            historico.append(agora)
            _REQUISICOES_IP[ip] = historico
            return f(*args, **kwargs)

        return wrapper

    return decorator
