"""
API do CRM local da ferramenta de prospecção.

Uso:
    py app.py
A API sobe em http://localhost:5000. A interface (React) roda em
http://localhost:5173 - use o iniciar.bat na raiz pra subir os dois juntos.

O código está dividido por responsabilidade:
    rotas_leads.py      - CRM dos leads do Google Maps + disparo da busca
    rotas_instagram.py  - CRM dos leads do Instagram + disparo da análise
    rotas_analytics.py  - métricas, funis, meta semanal, follow-ups do dia
    rotas_config.py     - chaves de IA, proxies, templates de mensagem
    ia.py               - provedores de IA e fallback unificado
    jobs.py             - jobs de background (scraper/análise) + persistência
    db.py               - conexão, configurações e backup do banco
    processar.py        - pipeline do CSV do scraper + schema/migrações
"""

import logging
import hmac
import os
import secrets
import sqlite3
import threading
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

import paths

load_dotenv()

paths.garantir_pastas_de_dados()

APP_DIR = paths.DIR_RECURSOS
PASTA_LOGS = paths.DIR_DADOS / "logs"


def _novo_handler_log(pasta_logs):
    """Cria log em arquivo, mas não derruba o app por ACL/arquivo bloqueado.

    Em hosts Windows, um log legado pode estar aberto por outra instância ou
    ter ACL temporariamente restritiva. O fallback para stderr mantém o app
    observável e permite que o operador corrija a pasta sem perder a inicialização.
    """
    try:
        pasta_logs.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            pasta_logs / "prospeccao.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        fallback = False
    except OSError as erro:
        handler = logging.StreamHandler()
        fallback = True
        handler._prospectos_log_error = str(erro)  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler._prospectos_managed = True  # type: ignore[attr-defined]
    return handler, fallback


_handler_log, _log_fallback = _novo_handler_log(PASTA_LOGS)
logging.getLogger().addHandler(_handler_log)
# nível configurável via .env: PROSPECCAO_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
_nivel_log = os.environ.get("PROSPECCAO_LOG_LEVEL", "INFO").upper()
logging.getLogger().setLevel(getattr(logging, _nivel_log, logging.INFO))
logger = logging.getLogger(__name__)
if _log_fallback:
    logger.warning(
        "log em arquivo indisponível; usando stderr temporariamente (%s)",
        getattr(_handler_log, "_prospectos_log_error", "erro não especificado"),
    )

import db
import jobs
import lp
import outreach
import processar
import rotas_analytics
import rotas_config
import rotas_instagram
import rotas_leads

app = Flask(__name__)
# Every route currently accepts structured JSON; no endpoint needs an upload
# larger than a few megabytes. A global cap prevents a local caller from making
# Flask materialize an unbounded request before a route-specific validator runs.
# The environment override is bounded as well, so a typo cannot silently turn
# this defense off.
_DEFAULT_MAX_CONTENT_LENGTH = 16 * 1024 * 1024
_MAX_CONTENT_LENGTH_HARD_CAP = 64 * 1024 * 1024
_MAX_FORM_MEMORY_SIZE = 1 * 1024 * 1024
_MAX_FORM_PARTS = 100


def _limite_corpo_requisicao():
    bruto = os.environ.get("PROSPECCAO_MAX_CONTENT_LENGTH")
    if bruto is None or not bruto.strip():
        return _DEFAULT_MAX_CONTENT_LENGTH
    try:
        valor = int(bruto)
    except (TypeError, ValueError):
        logger.warning(
            "PROSPECCAO_MAX_CONTENT_LENGTH inválido; usando o limite padrão de %s bytes",
            _DEFAULT_MAX_CONTENT_LENGTH,
        )
        return _DEFAULT_MAX_CONTENT_LENGTH
    if not 1 <= valor <= _MAX_CONTENT_LENGTH_HARD_CAP:
        logger.warning(
            "PROSPECCAO_MAX_CONTENT_LENGTH fora de 1..%s; usando o limite padrão",
            _MAX_CONTENT_LENGTH_HARD_CAP,
        )
        return _DEFAULT_MAX_CONTENT_LENGTH
    return valor


app.config["MAX_CONTENT_LENGTH"] = _limite_corpo_requisicao()
# Nenhuma rota atual usa upload multipart, mas limites explícitos impedem que
# uma futura rota de formulário aceite campos/partes ilimitados por acidente.
app.config["MAX_FORM_MEMORY_SIZE"] = _MAX_FORM_MEMORY_SIZE
app.config["MAX_FORM_PARTS"] = _MAX_FORM_PARTS
app.register_blueprint(rotas_leads.bp)
app.register_blueprint(rotas_instagram.bp)
app.register_blueprint(rotas_analytics.bp)
app.register_blueprint(rotas_config.bp)
app.register_blueprint(lp.bp)
app.register_blueprint(outreach.bp)


_METODOS_MUTAVEIS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_HOSTS_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
_CSRF_COOKIE = "prospectos_csrf"
_CSRF_HEADER = "X-CSRF-Token"
# Token process-local: the browser obtains it over the same-origin endpoint and
# must echo it in a non-simple header. CLI/MCP callers remain headerless and do
# not receive a cookie, preserving their explicit non-browser contract.
_CSRF_TOKEN = secrets.token_urlsafe(32)

# Política inicial em Report-Only: registra violações sem quebrar o bundle
# existente. A lista evita eval/objetos/plugins e mantém as integrações web
# observadas; o enforcement deve ocorrer no ponto de publicação após revisar
# os relatórios do navegador e os domínios realmente necessários.
_CSP_REPORT_ONLY = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; "
    "form-action 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https://images.unsplash.com https://*.tile.openstreetmap.org; "
    "font-src 'self' data:; media-src 'self' blob:; worker-src 'self' blob:; "
    "connect-src 'self' http://localhost:* http://127.0.0.1:* "
    "ws://localhost:* ws://127.0.0.1:* https://nominatim.openstreetmap.org"
)


def _origens_permitidas():
    """Retorna origens HTTP locais aceitas para mutações feitas no navegador.

    A API continua compatível com o MCP/CLI, que não enviam Origin nem Referer.
    Quando um cliente se identifica como navegador, só a própria origem local,
    o Vite de desenvolvimento e origens explicitamente adicionadas pelo
    operador passam. Isso reduz CSRF sem fingir que existe autenticação de
    usuário.
    """
    permitidas = {
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
    extras = os.environ.get("PROSPECCAO_ALLOWED_ORIGINS", "")
    permitidas.update(item.strip().rstrip("/") for item in extras.split(",") if item.strip())
    return permitidas


def _normalizar_origem(origem):
    """Normaliza e valida uma origem sem aceitar credenciais ou host externo."""
    try:
        partes = urlsplit(origem)
        if partes.scheme not in {"http", "https"} or partes.username or partes.password:
            return None
        if partes.hostname not in _HOSTS_LOOPBACK:
            return None
        # urlsplit().port lança ValueError para portas malformadas.
        porta = partes.port
        if porta is None:
            porta = 443 if partes.scheme == "https" else 80
        if not 1 <= porta <= 65535:
            return None
        return f"{partes.scheme}://{partes.hostname}:{porta}"
    except (TypeError, ValueError):
        return None


def _origem_de_cabecalho(origem):
    if not origem or origem == "null":
        return None
    normalizada = _normalizar_origem(origem.rstrip("/"))
    return normalizada


@app.before_request
def bloquear_origem_externa_em_mutacoes():
    """Impede que um site externo dispare mutações na API local.

    Ausência de Origin/Referer permanece permitida para clientes não-browser
    (MCP, CLI e testes). Navegadores modernos enviam ao menos um desses
    cabeçalhos em requests cross-origin de escrita; origem inválida é recusada
    antes de qualquer rota tocar no banco ou iniciar um job.
    """
    if not request.path.startswith("/api/") or request.method not in _METODOS_MUTAVEIS:
        return None

    cabecalho = request.headers.get("Origin")
    if cabecalho is None:
        cabecalho = request.headers.get("Referer")
        if cabecalho:
            try:
                cabecalho = f"{urlsplit(cabecalho).scheme}://{urlsplit(cabecalho).netloc}"
            except (TypeError, ValueError):
                cabecalho = "null"

    # Fetch Metadata catches a cross-site browser request even when the
    # browser omits Origin/Referer due to a restrictive referrer policy. CLI
    # and MCP clients do not send this header and retain their compatibility.
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site.strip().lower() not in {"same-origin", "same-site", "none"}:
        return jsonify({"erro": "Origem não permitida para esta operação."}), 403

    cliente_browser = bool(
        cabecalho
        or fetch_site
        or request.cookies.get(_CSRF_COOKIE)
    )

    if cabecalho is None and not cliente_browser:
        return None

    if cabecalho is not None:
        origem = _origem_de_cabecalho(cabecalho)
        permitidas = _origens_permitidas()
        permitidas_normalizadas = {item.rstrip("/") for item in permitidas}

        # A própria porta/host loopback da requisição pode ser dinâmica no modo
        # empacotado; derive-a apenas depois de validar que o host é local.
        origem_requisicao = _normalizar_origem(request.host_url.rstrip("/"))
        if origem_requisicao:
            permitidas_normalizadas.add(origem_requisicao)

        if origem is None or origem not in permitidas_normalizadas:
            return jsonify({"erro": "Origem não permitida para esta operação."}), 403

    # Origin/Fetch Metadata stop cross-site requests; the synchronizer token
    # adds a per-process proof for same-origin browser mutations. A caller
    # without browser signals (MCP/CLI) remains compatible and is intentionally
    # outside this browser-CSRF contract.
    if cliente_browser:
        cookie_token = request.cookies.get(_CSRF_COOKIE, "")
        header_token = request.headers.get(_CSRF_HEADER, "")
        if not cookie_token or not header_token:
            return jsonify({"erro": "Token anti-CSRF ausente ou inválido."}), 403
        try:
            token_ok = hmac.compare_digest(cookie_token, _CSRF_TOKEN) and hmac.compare_digest(
                header_token,
                _CSRF_TOKEN,
            )
        except TypeError:
            token_ok = False
        if not token_ok:
            return jsonify({"erro": "Token anti-CSRF ausente ou inválido."}), 403
    return None


@app.after_request
def adicionar_headers_de_seguranca(resposta):
    """Endurece respostas HTTP sem bloquear o bundle durante a migração."""
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resposta.headers.setdefault("Referrer-Policy", "no-referrer")
    resposta.headers.setdefault("Content-Security-Policy-Report-Only", _CSP_REPORT_ONLY)
    resposta.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    if request.path.startswith("/api/"):
        resposta.headers.setdefault("Cache-Control", "no-store")
    return resposta


@app.errorhandler(Exception)
def tratar_erro_generico(erro):
    if isinstance(erro, HTTPException):
        return erro  # 404, 405 etc. devem chegar como são, não virar erro interno
    logger.exception("erro não tratado numa rota")
    return jsonify({"erro": "Ocorreu um erro interno. Veja detalhes em logs/prospeccao.log."}), 500


@app.errorhandler(RequestEntityTooLarge)
def tratar_corpo_grande(erro):
    """Mantém o erro de limite consistente com o contrato JSON da API."""
    return (
        jsonify({
            "erro": "O corpo da requisição excede o limite permitido.",
            "limite_bytes": app.config["MAX_CONTENT_LENGTH"],
        }),
        413,
    )


@app.errorhandler(db.ConfigSecretStorageError)
def tratar_cofre_indisponivel(erro):
    """Não transformar falha de cofre em sucesso nem expor a exceção ao cliente."""
    logger.warning("operação de configuração recusada: %s", erro)
    return jsonify({"erro": "Cofre de credenciais indisponível; a chave não foi salva."}), 503


@app.route("/api/health")
def health_check():
    """Endpoint de verificação de integridade operacional do backend."""
    db_pronto = False
    try:
        if db.CAMINHO_BANCO.exists():
            conexao = db.conectar()
            try:
                conexao.execute("SELECT 1 FROM leads LIMIT 1")
                db_pronto = True
            finally:
                conexao.close()
        else:
            db_pronto = True
    except Exception:
        db_pronto = False

    return jsonify({
        "ok": True,
        "app": "ProspectOS",
        "api_version": "1",
        "database_ready": db_pronto,
    })


@app.route("/api/csrf-token")
def csrf_token():
    """Entrega o token anti-CSRF somente por leitura same-origin.

    O valor fica em memória no processo, não é persistido nem registrado. O
    cookie HttpOnly/SameSite=Strict marca o navegador que iniciou o handshake;
    mutações precisam reenviar o mesmo valor no header não simples.
    """
    resposta = jsonify({"csrf_token": _CSRF_TOKEN})
    resposta.set_cookie(
        _CSRF_COOKIE,
        _CSRF_TOKEN,
        secure=request.is_secure,
        httponly=True,
        samesite="Strict",
        path="/",
    )
    resposta.headers["Cache-Control"] = "no-store"
    return resposta



# ---------------------------------------------------------------------------
# Servir o frontend buildado (produção/empacotado)
#
# Em dev o Vite (porta 5173) continua sendo a interface, com proxy pra cá.
# Empacotado (ou rodando só o backend com o build feito), o próprio Flask serve
# o dist/ na MESMA origem da API - como o frontend chama tudo por /api/*
# relativo, nenhuma configuração de URL é necessária.
# ---------------------------------------------------------------------------

DIR_FRONTEND_DIST = (
    paths.caminho_recurso("frontend_dist")
    if paths.EMPACOTADO
    else Path(__file__).parent.parent / "frontend" / "dist"
)


@app.route("/", defaults={"caminho": "index.html"})
@app.route("/<path:caminho>")
def servir_frontend(caminho):
    if caminho.startswith("api/"):
        abort(404)  # rota de API inexistente não deve devolver HTML
    if not DIR_FRONTEND_DIST.exists():
        return (
            jsonify({"erro": "Interface não encontrada. Em dev, use http://localhost:5173 (iniciar.bat)."}),
            404,
        )
    if (DIR_FRONTEND_DIST / caminho).is_file():
        return send_from_directory(DIR_FRONTEND_DIST, caminho)
    # SPA fallback: qualquer rota do React Router devolve o index.html
    return send_from_directory(DIR_FRONTEND_DIST, "index.html")


def preparar_banco_no_startup():
    """Garante que o schema esteja atualizado assim que o app sobe, mesmo que o
    usuário ainda não tenha rodado nenhuma busca nesta instalação."""
    conexao = sqlite3.connect(db.CAMINHO_BANCO, timeout=10)
    try:
        processar.preparar_banco(conexao)
    finally:
        conexao.close()


preparar_banco_no_startup()
jobs.marcar_jobs_interrompidos()
db.migrar_chaves_para_keyring()


def escolher_porta(preferida=5000):
    """Usa a porta preferida se estiver livre; senão pede uma porta livre ao SO."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferida))
            return preferida
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _abrir_navegador(porta):
    webbrowser.open(f"http://127.0.0.1:{porta}")


if __name__ == "__main__":
    modo_dev = os.environ.get("PROSPECCAO_DEBUG", "false").lower() == "true"
    if modo_dev and paths.EMPACOTADO:
        # The Werkzeug debugger is an interactive code-execution surface. A
        # packaged binary is never a development environment, so fail closed
        # instead of trusting a leaked or stale environment variable.
        logger.error("PROSPECCAO_DEBUG=true não é permitido no modo empacotado.")
        raise SystemExit(2)
    if modo_dev:
        # dev com auto-reload do Flask, comportamento de sempre
        app.run(debug=True, port=5000)
    else:
        porta = escolher_porta(5000)
        # anuncia a porta pra quem iniciou o processo (shell do app de desktop lê
        # o stdout; o arquivo cobre quem preferir ler do disco). Empacotado sem
        # console, sys.stdout pode ser None - o arquivo vira a fonte da verdade.
        try:
            print(f"LISTENING_ON={porta}", flush=True)
        except Exception:
            pass
        paths.escrever_texto_atomico(
            paths.caminho_dados("porta.txt", criar_pai=True), str(porta)
        )
        logger.info("servindo em http://127.0.0.1:%s", porta)

        # empacotado não tem iniciar.bat: o próprio app abre a interface - exceto
        # quando quem subiu o backend foi o shell de desktop (Electron), que tem
        # janela própria e seta PROSPECTOS_NO_BROWSER=1
        if paths.EMPACOTADO and os.environ.get("PROSPECTOS_NO_BROWSER") != "1":
            threading.Timer(1.0, _abrir_navegador, args=(porta,)).start()

        # waitress: servidor WSGI de produção (o dev server do Flask não é pra isso)
        from waitress import serve

        serve(app, host="127.0.0.1", port=porta, threads=8)
