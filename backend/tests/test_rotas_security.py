"""Testes de não exposição de credenciais de proxy na API."""

import sqlite3

import app as app_module
import db
import processar
import rotas_config


def test_rota_de_proxies_nao_expoe_credenciais(tmp_path, monkeypatch):
    caminho_banco = tmp_path / "proxies.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)
    conexao = sqlite3.connect(caminho_banco)
    processar.preparar_banco(conexao)
    conexao.close()
    db.salvar_config(
        "scraper_proxies",
        "http://usuario:senha@proxy.exemplo:8080, "
        "https://proxy-publico.exemplo:443?token=nao-exibir",
    )

    with app_module.app.app_context():
        dados = rotas_config.obter_proxies_scraper().get_json()

    assert dados["configurado"] is True
    assert "usuario" not in dados["proxies"]
    assert "senha" not in dados["proxies"]
    assert "nao-exibir" not in dados["proxies"]
    assert "proxy.exemplo:8080" in dados["proxies"]
    assert "proxy-publico.exemplo:443" in dados["proxies"]
