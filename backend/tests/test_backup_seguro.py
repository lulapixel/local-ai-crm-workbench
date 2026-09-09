"""Testes do formato de backup criptografado e do restore verificável."""

import io
import json
import sqlite3
import tarfile
from pathlib import Path

import pytest

import backup_seguro


def _criar_fonte(tmp_path: Path) -> Path:
    fonte = tmp_path / "dados"
    (fonte / "backups").mkdir(parents=True)
    (fonte / "saidas").mkdir()
    (fonte / "instagram" / "comentarios").mkdir(parents=True)
    (fonte / "instagram" / "sessao").mkdir(parents=True)
    (fonte / "logs").mkdir()
    conexao = sqlite3.connect(fonte / "leads.db")
    try:
        conexao.execute("CREATE TABLE leads (id INTEGER PRIMARY KEY, nome TEXT)")
        conexao.execute("INSERT INTO leads (nome) VALUES ('fixture')")
        conexao.commit()
    finally:
        conexao.close()
    (fonte / "backups" / "leads_old.db").write_bytes(b"backup antigo")
    (fonte / "saidas" / "resultado.csv").write_text("id,nome\n1,fixture\n", encoding="utf-8")
    (fonte / "instagram" / "comentarios" / "captura.json").write_text("{}", encoding="utf-8")
    (fonte / "instagram" / "sessao" / "cookies.json").write_text("nao copiar", encoding="utf-8")
    (fonte / "logs" / "app.log").write_text("nao copiar", encoding="utf-8")
    (fonte / ".env").write_text("TOKEN=nao copiar", encoding="utf-8")
    return fonte


def test_cria_verifica_e_restaura_sem_vazar_sessao_ou_logs(tmp_path):
    fonte = _criar_fonte(tmp_path)
    backup = tmp_path / "externo" / "prospectos.pob"

    criado = backup_seguro.create_backup(fonte, backup, "senha-forte")
    assert criado["encrypted"] is True
    assert criado["cipher"] == "AES-256-GCM"
    assert criado["file_count"] == 4
    assert backup.exists()
    assert b"TOKEN=nao copiar" not in backup.read_bytes()

    verificado = backup_seguro.verify_backup(backup, "senha-forte")
    assert verificado["file_count"] == 4
    assert set(verificado["files"]) == {
        "leads.db",
        "backups/leads_old.db",
        "saidas/resultado.csv",
        "instagram/comentarios/captura.json",
    }

    destino = tmp_path / "restaurado"
    restaurado = backup_seguro.restore_backup(backup, destino, "senha-forte")
    assert restaurado["verified"] is True
    assert (destino / "leads.db").exists()
    assert (destino / "saidas" / "resultado.csv").read_text(encoding="utf-8").startswith("id,nome")
    assert not (destino / "instagram" / "sessao").exists()
    assert not (destino / "logs").exists()


def test_senha_incorreta_e_destino_existente_falham_sem_extrair(tmp_path):
    fonte = _criar_fonte(tmp_path)
    backup = tmp_path / "backup.pob"
    backup_seguro.create_backup(fonte, backup, "senha-forte")

    with pytest.raises(backup_seguro.BackupError, match="senha incorreta"):
        backup_seguro.verify_backup(backup, "senha-errada")

    destino = tmp_path / "destino"
    destino.mkdir()
    (destino / "preservar.txt").write_text("intacto", encoding="utf-8")
    with pytest.raises(backup_seguro.BackupError, match="deve ser novo"):
        backup_seguro.restore_backup(backup, destino, "senha-forte")
    assert (destino / "preservar.txt").read_text(encoding="utf-8") == "intacto"


def test_caminhos_absolutos_e_traversal_sao_rejeitados():
    for caminho in ("C:/fora.txt", "C:\\fora.txt", "../fora.txt", "/fora.txt"):
        with pytest.raises(backup_seguro.BackupError):
            backup_seguro._safe_relative(caminho)


def test_destino_na_raiz_de_dados_e_rejeitado(tmp_path):
    fonte = _criar_fonte(tmp_path)
    with pytest.raises(backup_seguro.BackupError, match="dentro da raiz"):
        backup_seguro.create_backup(fonte, fonte / "backup.pob", "senha-forte")


def test_destino_independente_falha_fechado_no_mesmo_dispositivo(tmp_path):
    fonte = _criar_fonte(tmp_path)
    destino = tmp_path / "externo" / "backup.pob"

    with pytest.raises(backup_seguro.BackupError, match="volume/dispositivo independente"):
        backup_seguro.create_backup(
            fonte,
            destino,
            "senha-forte",
            require_independent_destination=True,
        )

    assert not destino.exists()


def test_falha_de_replace_preserva_backup_anterior_e_temporario(tmp_path, monkeypatch):
    fonte = _criar_fonte(tmp_path)
    destino = tmp_path / "backup.pob"
    anterior = b"backup anterior"
    destino.write_bytes(anterior)

    def falhar_replace(*args):
        raise OSError("volume indisponível")

    monkeypatch.setattr(backup_seguro.os, "replace", falhar_replace)
    with pytest.raises(OSError, match="volume indisponível"):
        backup_seguro.create_backup(fonte, destino, "senha-forte", overwrite=True)

    assert destino.read_bytes() == anterior
    assert list(tmp_path.glob(f".{destino.name}.*.tmp")) == []


def _archive_com_manifest(paths: list[str], sizes: list[int]) -> bytes:
    manifest = {
        "schema": backup_seguro.SCHEMA,
        "created_at": "2026-01-01T00:00:00+00:00",
        "scope": "fixture",
        "files": [
            {"path": path, "bytes": size, "sha256": "0" * 64}
            for path, size in zip(paths, sizes, strict=True)
        ],
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        manifest_bytes = json.dumps(manifest).encode("utf-8")
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))
        for path, size in zip(paths, sizes, strict=True):
            info = tarfile.TarInfo(path)
            info.size = size
            tar.addfile(info, io.BytesIO(b"x" * size))
    return buffer.getvalue()


def test_manifest_rejeita_colisao_de_caminho_no_windows():
    archive = _archive_com_manifest(["dados/A.txt", "dados/a.txt"], [1, 1])
    with pytest.raises(backup_seguro.BackupError, match="colidem"):
        backup_seguro._read_manifest(archive)


def test_manifest_rejeita_tar_bomb_por_tamanho_total():
    archive = _archive_com_manifest(["a.bin", "b.bin"], [8, 8])
    with pytest.raises(backup_seguro.BackupError, match="tamanho total"):
        backup_seguro._read_manifest(archive, max_total_bytes=15)


def test_manifest_rejeita_tamanho_real_diferente_do_declarado():
    manifest = {
        "schema": backup_seguro.SCHEMA,
        "created_at": "2026-01-01T00:00:00+00:00",
        "scope": "fixture",
        "files": [{"path": "payload.bin", "bytes": 1, "sha256": "0" * 64}],
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        manifest_bytes = json.dumps(manifest).encode("utf-8")
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))
        payload_info = tarfile.TarInfo("payload.bin")
        payload_info.size = 1024
        tar.addfile(payload_info, io.BytesIO(b"x" * 1024))
    with pytest.raises(backup_seguro.BackupError, match="tamanho real"):
        backup_seguro._read_manifest(buffer.getvalue())
