"""Testes da captura de comentários sem chamadas de rede reais."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "instagram"))

import raspar_comentarios


class ClienteFake:
    def media_pk_from_url(self, url):
        return "123"

    def media_comments(self, media_pk, amount=0):
        return [SimpleNamespace(user=SimpleNamespace(username="user1"), text="Oi")]


def test_captura_grava_json_atomico(tmp_path, monkeypatch):
    monkeypatch.setattr(raspar_comentarios, "PASTA_COMENTARIOS", tmp_path)
    monkeypatch.setattr(raspar_comentarios, "carregar_sessao", lambda: ClienteFake())

    saida = raspar_comentarios.raspar_comentarios("https://www.instagram.com/p/ABC/")

    dados = json.loads(saida.read_text(encoding="utf-8"))
    assert dados["comentarios"] == [{"username": "user1", "texto": "Oi"}]
    assert list(tmp_path.glob(".*.tmp")) == []


def test_falha_na_substituicao_preserva_captura_anterior(tmp_path, monkeypatch):
    saida = tmp_path / "captura.json"
    estado_anterior = '{"comentarios": [{"username": "anterior"}]}'
    saida.write_text(estado_anterior, encoding="utf-8")

    def falhar_substituicao(*args):
        raise OSError("disco indisponível")

    monkeypatch.setattr(raspar_comentarios.os, "replace", falhar_substituicao)

    with pytest.raises(OSError, match="disco indisponível"):
        raspar_comentarios._salvar_json_atomico(saida, {"comentarios": []})

    assert saida.read_text(encoding="utf-8") == estado_anterior
    assert list(tmp_path.glob(f".{saida.name}.*.tmp")) == []
