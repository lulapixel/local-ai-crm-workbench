"""Testes do armazenamento de configurações (db.py), em especial o cofre de
credenciais - o keyring real nunca é tocado: os wrappers são substituídos por
um dicionário em memória."""

import os
import sqlite3
from pathlib import Path

import pytest

import db
import processar


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho)
    conexao = sqlite3.connect(caminho)
    processar.preparar_banco(conexao)
    conexao.close()
    return caminho


@pytest.fixture
def cofre_fake(monkeypatch):
    """Substitui o keyring real por um dict em memória."""
    cofre = {}
    monkeypatch.setattr(db, "_keyring_obter", cofre.get)
    monkeypatch.setattr(db, "_keyring_salvar", lambda chave, valor: cofre.update({chave: valor}) or True)
    monkeypatch.setattr(db, "_keyring_apagar", lambda chave: cofre.pop(chave, None))
    return cofre


def _valor_no_banco(caminho, chave):
    conexao = sqlite3.connect(caminho)
    linha = conexao.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
    conexao.close()
    return linha[0] if linha else None


class TestChavesSecretas:
    def test_salvar_chave_secreta_vai_pro_cofre_nao_pro_banco(self, banco, cofre_fake):
        db.salvar_config("gemini", "chave-super-secreta")

        assert cofre_fake["gemini"] == "chave-super-secreta"
        assert _valor_no_banco(banco, "gemini") is None

    def test_salvar_chave_secreta_apaga_copia_legada_do_banco(self, banco, cofre_fake):
        conexao = sqlite3.connect(banco)
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('gemini', 'plaintext-antiga', '2026-01-01')"
        )
        conexao.commit()
        conexao.close()

        db.salvar_config("gemini", "chave-nova")

        assert cofre_fake["gemini"] == "chave-nova"
        assert _valor_no_banco(banco, "gemini") is None

    def test_obter_prioriza_cofre_sobre_banco_e_env(self, banco, cofre_fake, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "do-env")
        conexao = sqlite3.connect(banco)
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('gemini', 'do-banco', '2026-01-01')"
        )
        conexao.commit()
        conexao.close()
        cofre_fake["gemini"] = "do-cofre"

        assert db.obter_config("gemini") == "do-cofre"

    def test_obter_nao_retorna_segredo_legado_do_banco(self, banco, cofre_fake, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "do-env")
        assert db.obter_config("gemini") == "do-env"

        conexao = sqlite3.connect(banco)
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('gemini', 'do-banco', '2026-01-01')"
        )
        conexao.commit()
        conexao.close()
        assert db.obter_config("gemini") == "do-env"

    def test_keyring_indisponivel_falha_fechado_sem_gravar_no_banco(self, banco, cofre_fake, monkeypatch):
        monkeypatch.setattr(db, "_keyring_salvar", lambda chave, valor: False)

        with pytest.raises(db.ConfigSecretStorageError, match="cofre de credenciais indisponível"):
            db.salvar_config("groq", "chave-groq")
        assert _valor_no_banco(banco, "groq") is None


class TestMigracaoParaKeyring:
    def test_move_chaves_do_banco_pro_cofre(self, banco, cofre_fake):
        conexao = sqlite3.connect(banco)
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('gemini', 'g-123', '2026-01-01')"
        )
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('groq', 'q-456', '2026-01-01')"
        )
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES ('scraper_proxies', 'http://p:1', '2026-01-01')"
        )
        conexao.commit()
        conexao.close()

        db.migrar_chaves_para_keyring()

        assert cofre_fake == {"gemini": "g-123", "groq": "q-456"}
        assert _valor_no_banco(banco, "gemini") is None
        assert _valor_no_banco(banco, "groq") is None
        # configs comuns (não secretas) continuam no banco
        assert _valor_no_banco(banco, "scraper_proxies") == "http://p:1"

    def test_migracao_e_idempotente(self, banco, cofre_fake):
        db.migrar_chaves_para_keyring()
        db.migrar_chaves_para_keyring()
        assert cofre_fake == {}


class TestConfigsComuns:
    def test_config_comum_continua_no_banco(self, banco, cofre_fake):
        db.salvar_config("scraper_proxies", "http://proxy:8080")

        assert "scraper_proxies" not in cofre_fake
        assert _valor_no_banco(banco, "scraper_proxies") == "http://proxy:8080"
        assert db.obter_config("scraper_proxies") == "http://proxy:8080"


class TestBackupBanco:
    def test_backup_wal_e_consistente_e_tem_integridade(self, banco, tmp_path, monkeypatch):
        pasta_backups = tmp_path / "backups"
        monkeypatch.setattr(db, "PASTA_BACKUPS", pasta_backups)

        conexao = sqlite3.connect(banco)
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("CREATE TABLE wal_probe (valor TEXT NOT NULL)")
        conexao.execute("INSERT INTO wal_probe (valor) VALUES ('confirmado-no-wal')")
        conexao.commit()
        # O writer continua aberto: a implementação precisa capturar o WAL,
        # não apenas copiar o arquivo principal.
        db.fazer_backup_banco()
        conexao.close()

        arquivos = list(pasta_backups.glob("leads_*.db"))
        assert len(arquivos) == 1
        copia = sqlite3.connect(arquivos[0])
        try:
            assert copia.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert copia.execute("SELECT valor FROM wal_probe").fetchone()[0] == "confirmado-no-wal"
        finally:
            copia.close()
        assert not list(pasta_backups.glob(".*.tmp"))

    def test_falha_na_retentao_nao_invalida_backup_novo(self, banco, tmp_path, monkeypatch):
        pasta_backups = tmp_path / "backups"
        pasta_backups.mkdir()
        antigo = pasta_backups / "leads_antigo.db"
        antigo.write_bytes(b"snapshot legado")
        os.utime(antigo, (1, 1))
        monkeypatch.setattr(db, "PASTA_BACKUPS", pasta_backups)
        monkeypatch.setattr(db, "MAX_BACKUPS_MANTIDOS", 1)

        unlink_original = Path.unlink

        def unlink_com_falha(caminho, *args, **kwargs):
            if caminho == antigo:
                raise PermissionError("snapshot em uso")
            return unlink_original(caminho, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", unlink_com_falha)
        db.fazer_backup_banco()

        novos = list(pasta_backups.glob("leads_*.db"))
        assert any(caminho != antigo and caminho.stat().st_size > 0 for caminho in novos)
        assert antigo.exists()


class TestPerfilVendedor:
    @pytest.fixture
    def cliente(self, banco):
        import app as app_module
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as cliente_teste:
            yield cliente_teste

    def test_salva_e_retorna_perfil(self, cliente):
        resposta = cliente.post("/api/configuracoes/perfil-vendedor", json={
            "nome": "Fernando",
            "apresentacao": "crio sites para negócios locais",
            "diferencial": "entrego em 7 dias",
        })
        assert resposta.status_code == 200

        dados = cliente.get("/api/configuracoes/perfil-vendedor").get_json()
        assert dados == {
            "nome": "Fernando",
            "apresentacao": "crio sites para negócios locais",
            "diferencial": "entrego em 7 dias",
        }

    def test_perfil_vazio_por_padrao(self, cliente):
        dados = cliente.get("/api/configuracoes/perfil-vendedor").get_json()
        assert dados == {"nome": "", "apresentacao": "", "diferencial": ""}

    def test_campo_muito_longo_retorna_400(self, cliente):
        resposta = cliente.post("/api/configuracoes/perfil-vendedor", json={
            "nome": "a" * 81, "apresentacao": "", "diferencial": "",
        })
        assert resposta.status_code == 400


class TestRotasConfigSeguras:
    @pytest.fixture
    def cliente(self, banco):
        import app as app_module
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as cliente_teste:
            yield cliente_teste

    def test_api_de_configuracao_retorna_503_sem_fallback_plaintext(self, cliente, monkeypatch, banco):
        monkeypatch.setattr(db, "_keyring_salvar", lambda chave, valor: False)

        resposta = cliente.post("/api/configuracoes", json={"chave": "gemini", "valor": "segredo"})

        assert resposta.status_code == 503
        assert resposta.get_json() == {
            "erro": "Cofre de credenciais indisponível; a chave não foi salva."
        }
        assert _valor_no_banco(banco, "gemini") is None
