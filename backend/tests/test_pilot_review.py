import json

import pytest
from flask import Flask

import pilot_review
import local_workbench


@pytest.fixture
def material(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot_review.paths, "DIR_DADOS", tmp_path)
    row = dict(id="CAR-test", name="Synthetic business", segment="Moda", phone="+5581999999999",
               evidence="Public directory", hypothesis="Need unknown", question="How are requests handled?",
               draft="Synthetic draft for testing", contact_check="Published, not contacted",
               source_url="https://example.com/business", secret="must not be returned")
    data = dict(id="fixture", title="Synthetic pilot", checked_on="2026-09-30", prospects=[row], secret="private")
    file = tmp_path / "pilots" / "fixture" / "review.json"
    file.parent.mkdir(parents=True)
    def save():
        file.write_text(json.dumps(data), encoding="utf-8")
    save()
    return data, file, save


def test_read_only_api_keeps_file_and_never_opens_crm(material, monkeypatch):
    _, file, _ = material
    before = file.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Research review must not open CRM, run captures, models or sends")
    for module, name in [(local_workbench.bot, "conectar"), (local_workbench.bot, "capturar"),
                         (local_workbench.bot_strategy, "chamar_modelo"), (local_workbench.bot_delivery.requests, "post")]:
        monkeypatch.setattr(module, name, forbidden)
    app = Flask(__name__)
    app.register_blueprint(local_workbench.bp)
    response = app.test_client().get("/api/workbench/pilots")
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    payload = response.get_json()
    assert payload["pilots"][0]["prospects"][0]["name"] == "Synthetic business"
    assert "secret" not in json.dumps(payload)
    assert file.read_bytes() == before


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:password@example.com", "https://example.com/bad path"])
def test_unsafe_source_rejects_entire_pilot(material, url):
    data, _, save = material
    data["prospects"][0]["source_url"] = url
    save()
    assert pilot_review.listar() == {"pilots": [], "unavailable": 1}


def test_invalid_file_does_not_hide_other_valid_pilot(material):
    _, file, _ = material
    invalid = file.parent.parent / "invalid" / "review.json"
    invalid.parent.mkdir()
    invalid.write_text("{", encoding="utf-8")
    result = pilot_review.listar()
    assert len(result["pilots"]) == 1 and result["unavailable"] == 1


def test_oversized_file_rejected(material):
    _, file, _ = material
    file.write_bytes(b" " * (pilot_review.MAX_BYTES + 1))
    assert pilot_review.listar() == {"pilots": [], "unavailable": 1}


def test_path_outside_configured_data_never_read(material, monkeypatch, tmp_path):
    _, file, _ = material
    monkeypatch.setattr(pilot_review.paths, "DIR_DADOS", tmp_path / "other")
    monkeypatch.setattr(pilot_review.paths, "caminho_dados", lambda *args: file.parent.parent)
    assert pilot_review.listar() == {"pilots": [], "unavailable": 0}


def test_duplicate_identity_not_shown_twice(material):
    data, _, save = material
    data["prospects"].append(dict(data["prospects"][0]))
    save()
    assert pilot_review.listar() == {"pilots": [], "unavailable": 1}
