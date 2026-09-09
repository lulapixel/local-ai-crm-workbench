"""Testes determinísticos da fronteira de requisições HTTP externas."""

import socket
from types import SimpleNamespace

import pytest

import url_security


def test_normaliza_url_e_remove_fragmento():
    assert url_security.validar_url_publica(
        " HTTPS://Example.COM/rota#nao-enviar ",
        resolver=lambda host: ("93.184.216.34",),
    ) == "https://example.com/rota"


@pytest.mark.parametrize(
    "url",
    [
        "file:///C:/segredo.txt",
        "http://usuario:senha@example.com/",
        "http://localhost/",
        "http://servico.internal/",
        "https://example.com:8443/",
        "https:///sem-host",
    ],
)
def test_rejeita_formas_de_url_nao_publicas(url):
    with pytest.raises(url_security.URLNaoPublicaError):
        url_security.validar_url_publica(
            url,
            resolver=lambda host: ("93.184.216.34",),
        )


def test_resolvedor_rejeita_endereco_privado(monkeypatch):
    monkeypatch.setattr(
        url_security.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 0)),
        ],
    )

    with pytest.raises(url_security.URLNaoPublicaError, match="não público"):
        url_security.resolver_enderecos_publicos("intranet.exemplo")


def test_resolvedor_rejeita_mistura_de_enderecos(monkeypatch):
    monkeypatch.setattr(
        url_security.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ],
    )

    with pytest.raises(url_security.URLNaoPublicaError, match="não público"):
        url_security.resolver_enderecos_publicos("rebinding.exemplo")


def test_redirect_publico_e_validado_sem_follow_automatico(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "resolver_enderecos_publicos",
        lambda host: ("93.184.216.34",),
    )
    respostas = iter(
        [
            SimpleNamespace(
                status_code=302,
                headers={"Location": "https://final.exemplo/pagina"},
            ),
            SimpleNamespace(status_code=200, headers={}),
        ]
    )
    chamadas = []

    def requisicao(*args, **kwargs):
        chamadas.append((args, kwargs))
        return next(respostas)

    resposta = url_security.requisitar_url_publica(
        "https://origem.exemplo",
        requisicao,
        timeout=3,
    )

    assert resposta.status_code == 200
    assert [chamada[0][0] for chamada in chamadas] == [
        "https://origem.exemplo",
        "https://final.exemplo/pagina",
    ]
    assert all(chamada[1]["allow_redirects"] is False for chamada in chamadas)


def test_redirect_privado_e_bloqueado_antes_do_segundo_request(monkeypatch):
    def resolver(host):
        if host == "origem.exemplo":
            return ("93.184.216.34",)
        raise url_security.URLNaoPublicaError("destino não público")

    monkeypatch.setattr(url_security, "resolver_enderecos_publicos", resolver)
    chamadas = []

    def requisicao(*args, **kwargs):
        chamadas.append((args, kwargs))
        return SimpleNamespace(
            status_code=302,
            headers={"Location": "http://127.0.0.1/admin"},
        )

    with pytest.raises(url_security.URLNaoPublicaError, match="não público"):
        url_security.requisitar_url_publica(
            "https://origem.exemplo",
            requisicao,
            timeout=3,
        )

    assert len(chamadas) == 1


def test_revalida_dns_imediatamente_antes_da_conexao(monkeypatch):
    resolucoes = []
    chamadas = []

    def resolver(host):
        resolucoes.append(host)
        if len(resolucoes) == 1:
            return ("93.184.216.34",)
        raise url_security.URLNaoPublicaError("destino não público")

    def requisicao(*args, **kwargs):
        chamadas.append((args, kwargs))
        return SimpleNamespace(status_code=200, headers={})

    with pytest.raises(url_security.URLNaoPublicaError, match="não público"):
        url_security.requisitar_url_publica(
            "https://origem.exemplo",
            requisicao,
            timeout=3,
            resolver=resolver,
        )

    assert resolucoes == ["origem.exemplo", "origem.exemplo"]
    assert chamadas == []


def test_resposta_com_content_length_excessivo_e_bloqueada(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "resolver_enderecos_publicos",
        lambda host: ("93.184.216.34",),
    )
    fechada = []

    resposta = SimpleNamespace(
        status_code=200,
        headers={"Content-Length": str(url_security.MAX_RESPONSE_BYTES + 1)},
        close=lambda: fechada.append(True),
    )

    with pytest.raises(url_security.URLNaoPublicaError, match="grande demais"):
        url_security.requisitar_url_publica(
            "https://origem.exemplo",
            lambda *args, **kwargs: resposta,
            timeout=3,
        )

    assert fechada == [True]


def test_resposta_chunked_sem_tamanho_declarado_tambem_e_limitada(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "resolver_enderecos_publicos",
        lambda host: ("93.184.216.34",),
    )
    fechada = []

    class RespostaChunked:
        status_code = 200
        headers = {}

        def iter_content(self, chunk_size):
            yield b"x" * (url_security.MAX_RESPONSE_BYTES - 10)
            yield b"y" * 11

        def close(self):
            fechada.append(True)

    with pytest.raises(url_security.URLNaoPublicaError, match="grande demais"):
        url_security.requisitar_url_publica(
            "https://origem.exemplo",
            lambda *args, **kwargs: RespostaChunked(),
            timeout=3,
        )

    assert fechada == [True]


def test_resposta_chunked_dentro_do_limite_fica_reutilizavel(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "resolver_enderecos_publicos",
        lambda host: ("93.184.216.34",),
    )

    class RespostaChunked:
        status_code = 200
        headers = {}

        def iter_content(self, chunk_size):
            yield b"ola"
            yield b" mundo"

    resposta = url_security.requisitar_url_publica(
        "https://origem.exemplo",
        lambda *args, **kwargs: RespostaChunked(),
        timeout=3,
    )

    assert resposta._content == b"ola mundo"
