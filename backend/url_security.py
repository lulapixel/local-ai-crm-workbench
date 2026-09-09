"""Validação de destinos HTTP(S) externos controlados por dados de leads.

A consulta só admite destinos públicos, portas web usuais e um corpo limitado.
Redirects são seguidos manualmente para validar cada destino antes do próximo
request. O resolvedor é injetável nos testes.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit


class URLNaoPublicaError(ValueError):
    """URL ausente, malformada ou apontando para uma rede não pública."""


SCHEMES_PERMITIDOS = frozenset({"http", "https"})
PORTAS_WEB_PERMITIDAS = frozenset({80, 443})
REDIRECTS = frozenset({301, 302, 303, 307, 308})
MAX_REDIRECTS = 3
MAX_URL_CHARS = 2048
MAX_RESPONSE_BYTES = 2_000_000
HOSTS_LOCAIS = frozenset({"localhost", "localhost.localdomain"})
SUFIXOS_LOCAIS = (".localhost", ".local", ".internal", ".lan")


def _host_ascii(host: str) -> str:
    try:
        return host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as erro:
        raise URLNaoPublicaError("hostname inválido") from erro


def resolver_enderecos_publicos(host: str) -> tuple[str, ...]:
    """Resolve um host e recusa qualquer endereço que não seja global."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as erro:
        raise URLNaoPublicaError("hostname não resolve") from erro

    enderecos: set[str] = set()
    for info in infos:
        try:
            texto = str(info[4][0]).split("%", 1)[0]
            ip = ipaddress.ip_address(texto)
        except (IndexError, ValueError):
            continue
        if ip.version == 6 and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise URLNaoPublicaError("destino não público")
        enderecos.add(str(ip))

    if not enderecos:
        raise URLNaoPublicaError("hostname sem endereço utilizável")
    return tuple(sorted(enderecos))


def validar_url_publica(
    url: str,
    *,
    resolver: Callable[[str], object] | None = None,
) -> str:
    """Valida e normaliza uma URL destinada a uma requisição externa."""
    if not isinstance(url, str) or not url.strip() or len(url.strip()) > MAX_URL_CHARS:
        raise URLNaoPublicaError("URL ausente ou grande demais")

    bruto = url.strip()
    try:
        partes = urlsplit(bruto)
        porta = partes.port
    except ValueError as erro:
        raise URLNaoPublicaError("URL malformada") from erro

    esquema = partes.scheme.lower()
    if esquema not in SCHEMES_PERMITIDOS:
        raise URLNaoPublicaError("somente HTTP e HTTPS são permitidos")
    if partes.username is not None or partes.password is not None:
        raise URLNaoPublicaError("credenciais na URL não são permitidas")

    host = partes.hostname
    if not host:
        raise URLNaoPublicaError("hostname ausente")
    host = _host_ascii(host)
    if host in HOSTS_LOCAIS or host.endswith(SUFIXOS_LOCAIS):
        raise URLNaoPublicaError("hostname local não é permitido")
    if porta is not None and porta not in PORTAS_WEB_PERMITIDAS:
        raise URLNaoPublicaError("porta não permitida")

    (resolver or resolver_enderecos_publicos)(host)

    netloc = host
    if porta is not None:
        netloc = f"[{host}]" if ":" in host else host
        netloc = f"{netloc}:{porta}"
    elif ":" in host:
        netloc = f"[{host}]"
    return urlunsplit((esquema, netloc, partes.path, partes.query, ""))


def carregar_corpo_limitado(
    resposta: object,
    limite: int = MAX_RESPONSE_BYTES,
):
    """Materializa o corpo sem permitir respostas maiores que o limite."""
    fechar = getattr(resposta, "close", None)
    iterar = getattr(resposta, "iter_content", None)
    if callable(iterar):
        dados = bytearray()
        try:
            for bloco in iterar(chunk_size=64 * 1024):
                if not bloco:
                    continue
                if isinstance(bloco, str):
                    bloco = bloco.encode()
                if len(dados) + len(bloco) > limite:
                    if callable(fechar):
                        fechar()
                    raise URLNaoPublicaError("resposta grande demais")
                dados.extend(bloco)
        except URLNaoPublicaError:
            raise
        setattr(resposta, "_content", bytes(dados))
        setattr(resposta, "_content_consumed", True)
        return resposta

    conteudo = getattr(resposta, "content", b"") or b""
    if isinstance(conteudo, str):
        conteudo = conteudo.encode()
    if len(conteudo) > limite:
        if callable(fechar):
            fechar()
        raise URLNaoPublicaError("resposta grande demais")
    if hasattr(resposta, "_content"):
        setattr(resposta, "_content", bytes(conteudo))
        setattr(resposta, "_content_consumed", True)
    return resposta


def requisitar_url_publica(
    url: str,
    requisicao: Callable[..., object],
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    verify: bool = True,
    max_redirects: int = MAX_REDIRECTS,
    resolver: Callable[[str], object] | None = None,
):
    """Executa requests sem delegar redirects a destinos não validados.

    O destino é resolvido novamente imediatamente antes de cada chamada. Isso
    reduz a janela entre a validação e a conexão (TOCTOU/DNS rebinding) e deixa
    o resolvedor injetável para testes controlados. A proteção não substitui
    uma política de egress no sistema operacional ou na rede.
    """
    atual = validar_url_publica(url, resolver=resolver)
    for salto in range(max_redirects + 1):
        # Não reutilizar apenas a decisão do passo anterior: o DNS pode mudar
        # enquanto a requisição está sendo preparada.
        atual = validar_url_publica(atual, resolver=resolver)
        resposta = requisicao(
            atual,
            timeout=timeout,
            headers=headers,
            allow_redirects=False,
            verify=verify,
            stream=True,
        )
        cabecalhos = getattr(resposta, "headers", {}) or {}
        try:
            tamanho_declarado = int(cabecalhos.get("Content-Length", "0") or 0)
        except (TypeError, ValueError):
            tamanho_declarado = 0
        if tamanho_declarado > MAX_RESPONSE_BYTES:
            if callable(getattr(resposta, "close", None)):
                resposta.close()
            raise URLNaoPublicaError("resposta grande demais")

        carregar_corpo_limitado(resposta)
        status = getattr(resposta, "status_code", None)
        if status not in REDIRECTS:
            return resposta
        if salto >= max_redirects:
            raise URLNaoPublicaError("redirecionamentos demais")
        destino = cabecalhos.get("Location")
        if not destino:
            if callable(getattr(resposta, "close", None)):
                resposta.close()
            raise URLNaoPublicaError("redirect sem destino")
        if callable(getattr(resposta, "close", None)):
            resposta.close()
        atual = validar_url_publica(urljoin(atual, destino), resolver=resolver)
    raise URLNaoPublicaError("redirecionamento inválido")
