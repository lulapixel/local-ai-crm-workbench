"""Localizador do backend do ProspectOS."""

import ipaddress
import os
import socket
from typing import Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests
import paths


DEFAULT_BACKEND_URL = "http://127.0.0.1:5000"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _enderecos_loopback(host: str) -> tuple[str, ...]:
    """Resolve um alias local e retorna apenas endereços comprovadamente locais.

    O cliente ainda usa uma URL textual e a resolução pode mudar depois desta
    consulta (TOCTOU); por isso isto reduz, mas não substitui, uma política de
    egress do SO ou um transporte que fixe o endereço do peer.
    """
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return ()

    enderecos = set()
    for info in infos:
        try:
            bruto = str(info[4][0]).split("%", 1)[0]
            endereco = ipaddress.ip_address(bruto)
        except (IndexError, ValueError):
            continue
        if endereco.version == 6 and endereco.ipv4_mapped is not None:
            endereco = endereco.ipv4_mapped
        if not endereco.is_loopback:
            return ()
        enderecos.add(str(endereco))
    return tuple(sorted(enderecos))


def _normalizar_url_local(valor: object) -> Optional[str]:
    """Aceita somente um endpoint HTTP(S) de loopback, sem credenciais."""
    if not isinstance(valor, str):
        return None
    bruto = valor.strip()
    if not bruto or len(bruto) > 2048:
        return None
    try:
        partes = urlsplit(bruto)
        porta = partes.port
    except ValueError:
        return None

    if partes.scheme.lower() not in {"http", "https"}:
        return None
    if partes.username is not None or partes.password is not None:
        return None
    if partes.query or partes.fragment:
        return None
    host = (partes.hostname or "").lower().rstrip(".")
    if host not in LOOPBACK_HOSTS:
        return None
    if host == "localhost":
        enderecos = _enderecos_loopback(host)
        if not enderecos:
            return None
        # O backend do ProspectOS usa HTTP loopback. Canonicalizar o alias para
        # um IP antes da chamada elimina a segunda resolução DNS (janela TOCTOU)
        # no fluxo real. Para HTTPS, preserve o hostname para não quebrar SNI e
        # validação de certificado; essa variante continua exigindo egress/peer
        # pinning adicional se for habilitada pelo operador.
        if partes.scheme.lower() == "http":
            host = next((item for item in enderecos if ":" not in item), enderecos[0])
    if porta is not None and not 1 <= porta <= 65535:
        return None

    netloc = f"[{host}]" if ":" in host else host
    if porta is not None:
        netloc = f"{netloc}:{porta}"
    return urlunsplit((partes.scheme.lower(), netloc, partes.path.rstrip("/"), "", ""))


class BackendLocator:
    """Descobre e valida se o backend HTTP local do ProspectOS está operacional."""

    def __init__(self, override_url: Optional[str] = None):
        self._override_url = override_url
        # O health probe só deve alcançar o backend loopback. Uma sessão
        # dedicada sem trust_env impede proxy, netrc e variáveis ambientais de
        # desviar esta verificação antes da chamada real do MCP.
        self.session = requests.Session()
        self.session.trust_env = False

    def get_base_url(self) -> str:
        """Resolve a URL do backend na ordem de prioridade definida."""
        # 1. Parâmetro explícito / variável de ambiente
        env_url = self._override_url or os.environ.get("PROSPECTOS_API_URL")
        if env_url:
            normalizada = _normalizar_url_local(env_url)
            if normalizada:
                return normalizada

        # 2. Leitura de porta.txt gravado pelo app.py em paths.caminho_dados
        arquivo_porta = paths.caminho_dados("porta.txt")
        if arquivo_porta.exists():
            try:
                conteudo = arquivo_porta.read_text(encoding="utf-8").strip()
                if conteudo.isdigit():
                    porta = int(conteudo)
                    if 1 <= porta <= 65535:
                        return f"http://127.0.0.1:{porta}"
            except Exception:
                pass

        # 3. Fallback padrão
        return DEFAULT_BACKEND_URL

    def check_health(self, timeout_sec: float = 2.0) -> Tuple[bool, str, Optional[dict]]:
        """Realiza um health check curto no backend.

        Retorna (online, base_url, resposta_health_dict).
        """
        base_url = self.get_base_url()
        health_url = f"{base_url}/api/health"
        try:
            resp = self.session.get(health_url, timeout=timeout_sec, allow_redirects=False)
            if resp.status_code == 200:
                dados = resp.json()
                if isinstance(dados, dict) and dados.get("ok") is True:
                    return True, base_url, dados
        except Exception:
            pass

        return False, base_url, None
