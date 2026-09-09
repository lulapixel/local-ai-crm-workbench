"""Testes unitários da exportação ProspectOS -> Obsidian."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from obsidian_sync import _atomic_write, export_lead, export_project, normalize_context, safe_slug  # noqa: E402


class ObsidianSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        (self.vault / ".obsidian").mkdir(parents=True)
        (self.vault / "02-Projects").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_safe_slug_remove_separadores_e_acentos(self):
        self.assertEqual(safe_slug("GAP Barber & Studio / Centro"), "gap-barber-studio-centro")
        self.assertEqual(safe_slug(""), "sem-identificador")

    def test_export_project_planeja_sem_escrever(self):
        result = export_project(self.vault, self.root / "repo", write=False, updated="2026-08-18T00:00:00Z")

        self.assertFalse(result["write"])
        self.assertEqual({item["status"] for item in result["items"]}, {"would_create"})
        self.assertFalse((self.vault / "02-Projects" / "prospectos").exists())

    def test_export_project_e_idempotente(self):
        first = export_project(self.vault, self.root / "repo", write=True, updated="2026-08-18T00:00:00Z")
        second = export_project(self.vault, self.root / "repo", write=True, updated="2026-08-18T00:00:00Z")
        third = export_project(self.vault, self.root / "repo", write=True, updated="2026-08-19T00:00:00Z")

        self.assertEqual({item["status"] for item in first["items"]}, {"created"})
        self.assertEqual({item["status"] for item in second["items"]}, {"unchanged"})
        self.assertEqual({item["status"] for item in third["items"]}, {"updated"})
        self.assertTrue((self.vault / "02-Projects" / "prospectos" / "PROJECT.md").exists())
        manifest = json.loads(
            (self.vault / "02-Projects" / "prospectos" / ".prospectos-sync.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["managed_by"], "prospectos-obsidian-sync:v1")

    def test_export_project_preserva_nota_existente_nao_gerenciada(self):
        target = self.vault / "02-Projects" / "prospectos"
        target.mkdir()
        (target / "STATUS.md").write_text("nota humana\n", encoding="utf-8")

        result = export_project(self.vault, self.root / "repo", write=True, updated="2026-08-18T00:00:00Z")
        status_item = next(item for item in result["items"] if item["path"].endswith("STATUS.md"))

        self.assertEqual(status_item["status"], "conflict")
        self.assertEqual((target / "STATUS.md").read_text(encoding="utf-8"), "nota humana\n")

    def test_escrita_atomica_preserva_nota_se_substituicao_falhar(self):
        target = self.vault / "02-Projects" / "prospectos" / "STATUS.md"
        target.parent.mkdir(parents=True)
        estado_anterior = "nota anterior\n"
        target.write_text(estado_anterior, encoding="utf-8")

        with patch("obsidian_sync.os.replace", side_effect=OSError("disco indisponível")):
            with self.assertRaisesRegex(OSError, "disco indisponível"):
                _atomic_write(target, "nota nova\n")

        self.assertEqual(target.read_text(encoding="utf-8"), estado_anterior)
        self.assertEqual(list(target.parent.glob(f".{target.name}.*.tmp")), [])

    def test_export_lead_aplica_allowlist_e_remove_segredos(self):
        context = {
            "data": {
                "contract_version": "site-opportunity/v1",
                "lead": {
                    "place_id": "abc-123",
                    "name": "GAP Barber & Studio",
                    "status": "novo",
                    "site_status": "sem_site",
                    "api_key": "nao-deve-sair",
                },
                "conversion_pack": {"status": "draft", "version": 2},
                "investment": {"eligible": False, "blockers": ["human_sales_signal_missing"]},
            }
        }

        result = export_lead(self.vault, context, write=True, updated="2026-08-18T00:00:00Z")
        note = Path(result["path"]).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "created")
        self.assertIn("GAP Barber", note)
        self.assertIn("human_sales_signal_missing", note)
        self.assertNotIn("api_key", note)
        self.assertNotIn("nao-deve-sair", note)

    def test_export_lead_aceita_json_serializavel(self):
        raw = {"lead": {"place_id": "x", "name": "X"}}
        path = self.root / "context.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        result = export_lead(self.vault, json.loads(path.read_text(encoding="utf-8")), write=False)
        self.assertEqual(result["status"], "would_create")

    def test_normalize_contexto_site_opportunity_mapeia_blocos_sanitizados(self):
        context = {
            "data": {
                "contract_version": "site-opportunity/v1",
                "place_id": "ChIJ123",
                "company": {"name": "Clínica Alpha", "category": "saúde", "city": "Recife"},
                "crm": {"status": "respondeu", "score": 91},
                "current_website": {"url": "", "status": "sem_site"},
                "contact": {"phone": "5581999999999", "whatsapp_link": "https://wa.me/1"},
                "reputation": {"rating": 4.8, "review_count": 42},
                "conversion_pack": {
                    "status": "approved",
                    "version": 1,
                    "strategy": {"commercialAngle": "Prova social", "evidence": ["42 avaliações"]},
                },
                "investment": {"eligible": True, "blockers": []},
            }
        }

        clean = normalize_context(context)
        self.assertEqual(clean["lead"]["name"], "Clínica Alpha")
        self.assertEqual(clean["lead"]["status"], "respondeu")
        self.assertEqual(clean["lead"]["rating"], "4.8")
        self.assertEqual(clean["conversion_pack"]["strategy"]["commercialAngle"], "Prova social")


if __name__ == "__main__":
    unittest.main()
