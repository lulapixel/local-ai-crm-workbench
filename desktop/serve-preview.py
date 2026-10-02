"""Offline browser fixture, isolated data and scheduler disabled; never a production launcher."""
import os
from pathlib import Path
import sys

repo = Path(__file__).resolve().parent.parent
data = repo / "desktop/local-validation/browser-demo-data"
os.environ.update(PROSPECTOS_TEST_MODE="1", PROSPECTOS_TEST_DATA_DIR=str(data),
    PROSPECTOS_AUTOMATION_DISABLED="1", PROSPECTOS_BOT_LIVE_SENDS="0", PROSPECCAO_DEBUG="false")
sys.path.insert(0, str(repo / "backend"))
import app
import db
from waitress import serve

with db.conectar() as connection:
    samples = [
        ("demo-response", "DEMO · Estúdio Aurora", "11900000001", "respondeu", None, "Recife", "Design"),
        ("demo-followup", "DEMO · Oficina Horizonte", "11900000002", "contatado", "2026-09-01T09:00:00-03:00", "Recife", "Automotivo"),
        ("demo-opportunity", "DEMO · Café Alameda", "11900000003", "novo", None, "Olinda", "Alimentação"),
        ("demo-missing", "DEMO · Contato incompleto", None, "novo", None, "Recife", "Design"),
    ]
    connection.executemany("""INSERT OR IGNORE INTO leads(place_id,nome,telefone,status,proximo_followup,cidade,nicho,site_status,nota,num_avaliacoes)
        VALUES(?,?,?,?,?,?,?,'sem_site',5,100)""", samples)
print("OFFLINE_DEMO=http://127.0.0.1:5004/operacao", flush=True)
serve(app.app, host="127.0.0.1", port=5004, threads=4)
