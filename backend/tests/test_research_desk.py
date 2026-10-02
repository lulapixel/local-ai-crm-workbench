import json
import sqlite3

import pytest
from flask import Flask

import bot
import bot_delivery
import bot_strategy
import db
import paths
import processar
import research_desk as desk
import local_workbench


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "research.db")
    monkeypatch.setattr(paths, "DIR_DADOS", tmp_path)
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c)
        bot.preparar_banco(c)
        bot_strategy.preparar_banco(c)
        bot_delivery.preparar_banco(c)
        desk.preparar_banco(c)
    def forbidden(*args, **kwargs):
        pytest.fail("Research workflow must never call a provider, capture or model")
    monkeypatch.setattr(bot, "capturar", forbidden)
    monkeypatch.setattr(bot_strategy, "chamar_modelo", forbidden)
    monkeypatch.setattr(bot_delivery.requests, "post", forbidden)
    file = tmp_path / "pilots" / "fixture" / "pilot.json"
    file.parent.mkdir(parents=True)
    pilot = {"id": "fixture", "city": "Caruaru", "researched_on": "2026-09-30", "prospects": [
        {"id": "S1", "name": "Synthetic", "segment": "moda", "published_phone": "+5581999999999",
         "source_url": "https://example.com/business", "evidence": "Public source; need unknown", "draft": "Hello synthetic"}]}
    file.write_text(json.dumps(pilot), encoding="utf-8")
    return pilot, file


def candidate():
    desk.importar("fixture")
    with bot.conectar() as c:
        return dict(c.execute("SELECT * FROM research_candidates").fetchone())


def update(row, action="edit", **kwargs):
    return desk.change(row["id"], {"revision": row["revision"], "action": action, **kwargs})


def approved():
    row = update(candidate(), notes="Need discussed with owner", contact_verified=True)
    row = update(row, "qualify", human_confirmed=True)
    return update(row, "approve", human_confirmed=True)


def test_import_idempotent_preserves_edits_and_provenance(isolated):
    pilot, file = isolated
    assert desk.importar("fixture") == {"added": 1, "existing": 0}
    with bot.conectar() as c:
        row = dict(c.execute("SELECT * FROM research_candidates").fetchone())
        assert c.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 0
    update(row, notes="Operator observation")
    pilot["prospects"][0]["draft"] = "Changed source"
    file.write_text(json.dumps(pilot))
    assert desk.importar("fixture") == {"added": 0, "existing": 1}
    with bot.conectar() as c:
        row = dict(c.execute("SELECT * FROM research_candidates").fetchone())
        assert row["draft"] == "Hello synthetic" and row["notes"] == "Operator observation"
        assert row["state"] == "research" and row["approved_at"] is None


def test_bad_pilot_atomic_and_traversal_rejected(isolated):
    pilot, file = isolated
    pilot["prospects"].append(dict(pilot["prospects"][0], id="S2", source_url="javascript:alert(1)"))
    file.write_text(json.dumps(pilot))
    with pytest.raises(ValueError):
        desk.importar("fixture")
    with pytest.raises(ValueError):
        desk.importar("../../other")
    with bot.conectar() as c:
        assert c.execute("SELECT COUNT(*) FROM research_candidates").fetchone()[0] == 0


@pytest.mark.parametrize("field,value", [("draft", "Different exact text"), ("phone", "+5581999999998"), ("contact_verified", False)])
def test_approval_revoked_after_relevant_edit(field, value):
    row = approved()
    assert row["approval_valid"]
    row = update(row, **{field: value})
    assert not row["approval_valid"] and row["state"] == ("qualified" if field == "draft" else "research")
    with pytest.raises(ValueError):
        update(row, "sent", human_confirmed=True)


def test_stale_write_returns_conflict_without_losing_saved_values():
    row = candidate()
    saved = update(row, notes="First writer")
    with pytest.raises(desk.Conflict):
        update(row, notes="Stale writer")
    app = Flask(__name__)
    app.register_blueprint(desk.bp)
    response = app.test_client().patch(f"/api/research/{row['id']}", json={"revision": row["revision"], "notes": "Stale"})
    assert response.status_code == 409
    with bot.conectar() as c:
        assert c.execute("SELECT notes FROM research_candidates").fetchone()[0] == saved["notes"]


def test_manual_send_requires_exact_approval_and_human_declaration():
    row = candidate()
    with pytest.raises(ValueError):
        update(row, "sent", human_confirmed=True)
    row = approved()
    with pytest.raises(ValueError):
        update(row, "sent", human_confirmed=False)
    row = update(row, "sent", human_confirmed=True)
    assert row["state"] == "contacted" and row["sent_at"]
    assert any(e["action"] == "sent" and "Hello synthetic" in e["detail"] for e in row["events"])
    with pytest.raises(ValueError):
        update(row, "sent", human_confirmed=True)
    row = update(row, "reply", human_confirmed=True)
    row = update(row, "win", human_confirmed=True)
    assert row["state"] == "won" and not row["approval_valid"]


def test_late_global_suppression_blocks_previously_approved_send():
    row = approved()
    with bot.conectar() as c:
        c.execute("INSERT INTO bot_suppressions VALUES(?,?,?)", (desk._contact(row["phone"]), "fixture", desk.now()))
    with pytest.raises(ValueError, match="bloqueado"):
        update(row, "sent", human_confirmed=True)
    assert not local_workbench.planejar(15)["actions"]
    with bot.conectar() as c:
        current=desk._public(c,c.execute("SELECT * FROM research_candidates WHERE id=?",(row["id"],)).fetchone())
        assert current["next_action"]["kind"] == "blocked" and not current["approval_valid"]


def test_suppression_shared_with_maps_and_future_imports():
    row = update(candidate(), "suppress", human_confirmed=True)
    assert row["state"] == "suppressed"
    with bot.conectar() as c:
        assert desk._contact(row["phone"]) in bot._contatos_bloqueados(c)
    desk.importar("fixture")
    with pytest.raises(ValueError):
        update(row, "approve", human_confirmed=True)


def test_duplicate_maps_contact_blocks_qualification():
    row = update(candidate(), notes="Checked", contact_verified=True)
    with bot.conectar() as c:
        c.execute("INSERT INTO leads(place_id,nome,telefone) VALUES('fixture','Synthetic', '81999999999')")
    with pytest.raises(ValueError, match="Maps"):
        update(row, "qualify", human_confirmed=True)


def test_invalid_body_dates_and_missing_notes_not_qualified():
    row = candidate()
    for body in (None, {"revision": True}, {"revision": 1, "state": "approved"}, {"revision": 1, "followup_on": "2026-99-99"}):
        with pytest.raises(ValueError):
            desk.change(row["id"], body)
    with pytest.raises(ValueError):
        update(row, "qualify", human_confirmed=True)


def test_session_planning_respects_time_city_and_preserves_data():
    row = candidate()
    with bot.conectar() as c:
        before = list(c.iterdump())
    plan = local_workbench.planejar(15, city="Caruaru")
    assert plan["actions"][0]["href"] == f"/pesquisa?candidate={row['id']}"
    assert plan["estimated_minutes"] <= 15 and plan["model_calls"] == 0
    assert not local_workbench.planejar(15, city="Recife")["actions"]
    with bot.conectar() as c:
        assert list(c.iterdump()) == before


def test_session_tracks_current_stage_without_calls():
    row = approved()
    plan = local_workbench.planejar(15)
    assert plan["actions"][0]["kind"] == "manual_contact"
    row = update(row, "sent", human_confirmed=True)
    row = update(row, followup_on="2026-09-01")
    assert local_workbench.planejar(15)["actions"][0]["kind"] == "followup"
    update(row, "reply", human_confirmed=True)
    assert local_workbench.planejar(15)["actions"][0]["kind"] == "conversation"


def test_export_is_json_not_spreadsheet_and_cache_disabled():
    candidate()
    app = Flask(__name__)
    app.register_blueprint(desk.bp)
    response = app.test_client().get("/api/research/export")
    assert response.status_code == 200 and response.is_json
    assert response.headers["Cache-Control"] == "no-store"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "approval_hash" not in response.get_json()["candidates"][0]


def test_two_simultaneous_writers_only_one_revision_is_accepted():
    from concurrent.futures import ThreadPoolExecutor
    row = candidate()
    def writer(note):
        try:
            update(row, notes=note)
            return "saved"
        except desk.Conflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(writer, ("Writer A", "Writer B"))) == ["conflict", "saved"]
    with bot.conectar() as c:
        saved = dict(c.execute("SELECT * FROM research_candidates").fetchone())
        assert saved["revision"] == 2 and saved["notes"] in ("Writer A", "Writer B")


def test_pilot_metadata_counts_full_pilot_not_review_subset(monkeypatch):
    monkeypatch.setattr(desk.pilot_review, "listar", lambda: {"pilots": [{"id": "fixture", "title": "Subset title"}, {"id": "missing", "title": "Missing"}]})
    app = Flask(__name__)
    app.register_blueprint(desk.bp)
    response = app.test_client().get("/api/research")
    assert response.get_json()["pilots"] == [{"id": "fixture", "title": "Caruaru · pesquisa local", "count": 1}]


def test_import_api_rejects_unexpected_or_invalid_payload():
    app = Flask(__name__)
    app.register_blueprint(desk.bp)
    client = app.test_client()
    for body in (None, [], {"pilot_id": "fixture", "state": "approved"}, {"pilot_id": "../fixture"}):
        assert client.post("/api/research/import", json=body).status_code == 400


def test_atomic_qualification_does_not_require_draft_or_approve_text():
    row = candidate()
    result = update(row, "qualify", human_confirmed=True, notes="Need confirmed in fixture",
                    contact_verified=True, draft="")
    assert result["state"] == "qualified" and result["revision"] == row["revision"] + 1
    assert result["qualification_ready"] and not result["approval_valid"]
    assert result["next_action"]["kind"] == "prepare_text"
    assert result["events"][0]["action"] == "qualify"
    with pytest.raises(ValueError, match="texto"):
        update(result, "approve", human_confirmed=True)
    plan = local_workbench.planejar(15)
    assert plan["actions"][0]["kind"] == "research"
    assert "qualificação permanece" in plan["actions"][0]["reason"].lower()


@pytest.mark.parametrize("failure", ["missing_confirmation", "invalid_phone", "missing_notes", "duplicate", "suppressed"])
def test_atomic_qualification_failure_does_not_leave_partial_edits(failure):
    row = candidate()
    body = {"revision": row["revision"], "action": "qualify", "human_confirmed": True,
            "contact_verified": True, "notes": "Would overwrite notes", "draft": "Would overwrite draft"}
    if failure == "missing_confirmation":body.pop("human_confirmed")
    if failure == "invalid_phone":body["phone"] = "not a phone"
    if failure == "missing_notes":body["notes"] = " "
    with bot.conectar() as c:
        if failure == "duplicate":
            c.execute("INSERT INTO leads(place_id,nome,telefone) VALUES('other','Fixture','81999999999')")
        if failure == "suppressed":
            c.execute("INSERT INTO bot_suppressions(contact,reason,created_at) VALUES(?,'fixture','now')", (desk._contact(row["phone"]),))
        before = list(c.iterdump())
    with pytest.raises(ValueError):desk.change(row["id"], body)
    with bot.conectar() as c:assert list(c.iterdump()) == before


def test_qualification_notes_removed_revokes_approval_and_contact_gate():
    result = update(approved(), notes="")
    assert result["state"] == "research" and not result["approval_valid"] and not result["qualification_ready"]


def test_batch_serialization_preserves_full_blockers_and_recent_history():
    row = candidate()
    for n in range(25):row = update(row, notes=f"Synthetic edit {n}")
    with bot.conectar() as c:
        rows = c.execute("SELECT * FROM research_candidates ORDER BY id").fetchall()
        legacy = [desk._public(c, raw) for raw in rows]
        batched = desk.public_candidates(c, rows)
    assert batched == legacy and len(batched[0]["events"]) == 20


@pytest.mark.parametrize("count", [10,100,500])
def test_batch_query_count_is_constant_in_candidate_count(count):
    row = candidate()
    with bot.conectar() as c:
        for n in range(count - 1):
            c.execute("""INSERT INTO research_candidates(origin,external_id,name,city,segment,source_url,
                evidence,hypothesis,source_fingerprint,researched_on,phone,updated_at)
                VALUES('synthetic',?,'Fixture','Caruaru','Services','https://example.com','Fixture','Unknown',?,'2026-10-01',?,'now')""",
                (str(n),'a'*64,f"+55819{n:08d}"))
        rows = c.execute("SELECT * FROM research_candidates ORDER BY id").fetchall()
        queries=[]
        c.set_trace_callback(lambda sql:queries.append(sql) if sql.lstrip().upper().startswith("SELECT") else None)
        result=desk.public_candidates(c,rows)
        c.set_trace_callback(None)
    assert len(result)==count and len(queries)==4


def test_waiting_suppressed_and_terminal_candidates_do_not_enter_active_work():
    row=approved()
    row=update(row,"sent",human_confirmed=True)
    row=update(row,followup_on="2999-01-01")
    assert not row["next_action"]["actionable"]
    assert not local_workbench.planejar(15)["actions"]
    row=update(row,"suppress",human_confirmed=True)
    assert row["next_action"]["kind"] == "none"


def test_new_global_suppression_is_observed_in_next_list_not_cached():
    row=approved()
    with bot.conectar() as c:
        first=desk.public_candidates(c,c.execute("SELECT * FROM research_candidates").fetchall())
        assert first[0]["approval_valid"]
        c.execute("INSERT INTO bot_suppressions(contact,reason,created_at) VALUES(?,'fixture','now')", (desk._contact(row["phone"]),))
    with bot.conectar() as c:
        second=desk.public_candidates(c,c.execute("SELECT * FROM research_candidates").fetchall())
        assert not second[0]["approval_valid"] and second[0]["next_action"]["kind"] == "blocked"
