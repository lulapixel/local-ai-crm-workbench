"""Backup criptografado e restauração verificável dos dados do ProspectOS.

O utilitário é deliberadamente explícito: a senha nunca é persistida, o destino
precisa ser informado pelo operador e sessões/segredos ficam fora do escopo
 padrão. O arquivo resultante pode ser copiado para um destino externo escolhido
 pelo usuário, mas este módulo não faz upload nem decide retenção por conta
 própria. O modo opcional ``require_independent_destination`` falha fechado
 quando não consegue provar que o destino está em outro dispositivo/volume;
 essa verificação não substitui a escolha de host, provedor, retenção ou RPO/RTO.

Formato do arquivo:

    MAGIC + tamanho(JSON de metadados) + metadados + AES-256-GCM( tar.gz )

O JSON e o cabeçalho são autenticados como AAD. O ``manifest.json`` interno
contém hash e tamanho de cada arquivo incluído. A restauração sempre extrai para
um diretório novo e falha antes de tocar em um diretório existente.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import secrets
import shutil
import sqlite3
import struct
import sys
import tarfile
import tempfile
import unicodedata
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Mapping, Sequence
from urllib.parse import quote

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

try:
    from paths import DIR_DADOS
except ImportError:  # pragma: no cover - permite execução como módulo isolado
    DIR_DADOS = Path(__file__).resolve().parent


SCHEMA = "prospectos-secure-backup/v1"
MAGIC = b"PROSPECTOS-SECURE-BACKUP\x01\n"
MAX_METADATA_BYTES = 64 * 1024
DEFAULT_MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_RESTORED_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_FILES = 10_000
DEFAULT_SCOPE = (
    "leads.db",
    "backups",
    "saidas",
    "queries.txt",
    "porta.txt",
    "instagram/comentarios",
)

# O escopo padrão nunca deve atravessar estas áreas. ``sessao`` contém cookies
# e tokens; logs podem conter dados operacionais; caches/testes não são dados de
# negócio e só aumentariam o blast radius do backup.
_EXCLUDED_PARTS = {
    ".git",
    ".codex",
    ".agents",
    "__pycache__",
    ".pytest_cache",
    ".playwright-mcp",
    "logs",
    "sessao",
    "venv",
    ".venv",
}
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class BackupError(RuntimeError):
    """Erro seguro e acionável para criação, verificação ou restauração."""


def _password_bytes(password: str | bytes) -> bytes:
    if isinstance(password, str):
        password = password.encode("utf-8")
    if not isinstance(password, bytes) or not password:
        raise BackupError("a senha do backup não pode ser vazia")
    return password


def _resolve_directory(path: str | os.PathLike[str]) -> Path:
    directory = Path(path).expanduser()
    if not directory.exists() or not directory.is_dir():
        raise BackupError(f"diretório de dados inexistente: {directory}")
    return directory.resolve()


def _existing_ancestor(path: Path) -> Path:
    """Encontra o primeiro ancestral existente para consultar o dispositivo."""
    candidate = path
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return candidate


def _device_id(path: Path) -> int | None:
    """Retorna o identificador do dispositivo sem criar o destino."""
    try:
        return int(os.stat(_existing_ancestor(path)).st_dev)
    except OSError:
        return None


def _require_independent_destination(source: Path, destination: Path) -> None:
    """Recusa destino no mesmo dispositivo e falha fechado se não puder comparar."""
    source_device = _device_id(source)
    destination_device = _device_id(destination)
    if source_device is None or destination_device is None:
        raise BackupError("não foi possível verificar o volume do destino independente")
    if source_device == destination_device:
        raise BackupError("destino deve estar em volume/dispositivo independente")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_relative(path: str | os.PathLike[str]) -> str:
    """Normaliza caminho de arquivo para o formato POSIX do tar."""
    raw = str(path).replace("\\", "/")
    candidate = PurePosixPath(raw)
    windows_candidate = PureWindowsPath(raw)
    if (
        candidate.is_absolute()
        or windows_candidate.is_absolute()
        or windows_candidate.drive
        or ".." in candidate.parts
        or not candidate.parts
        or any(":" in part for part in candidate.parts)
    ):
        raise BackupError(f"caminho relativo inválido: {path}")
    for part in candidate.parts:
        if not part or part in {".", ".."} or part[-1] in {".", " "}:
            raise BackupError(f"componente de caminho incompatível com Windows: {path}")
        normalized = unicodedata.normalize("NFKC", part).split(".", 1)[0].rstrip(" .").upper()
        if normalized in _WINDOWS_RESERVED_NAMES:
            raise BackupError(f"nome reservado do Windows não é aceito: {path}")
    return candidate.as_posix()


def _windows_collision_key(relative: str) -> tuple[str, ...]:
    """Chave aproximada de colisão para o sistema de arquivos Windows."""
    return tuple(
        unicodedata.normalize("NFKC", part).rstrip(" .").casefold()
        for part in PureWindowsPath(relative).parts
    )


def _is_excluded(relative: PurePosixPath) -> bool:
    parts = {part.casefold() for part in relative.parts}
    if any(part.casefold() in _EXCLUDED_PARTS for part in parts):
        return True
    if any(part.casefold().startswith(".pytest-tmp") for part in relative.parts):
        return True
    name = relative.name.lower()
    if (
        name == ".env"
        or name.startswith(".env.")
        or name.endswith((".tmp", ".temp", ".key", ".pem", ".p12", ".pfx"))
        or any(token in name for token in ("credential", "password", "secret", "cookie", "token"))
    ):
        return True
    return False


def _iter_scope_files(root: Path, scope: Sequence[str]) -> tuple[list[tuple[str, Path]], list[str]]:
    selected: dict[str, Path] = {}
    missing: list[str] = []
    for raw_relative in scope:
        relative = _safe_relative(raw_relative)
        source = root / Path(*PurePosixPath(relative).parts)
        if not source.exists():
            missing.append(relative)
            continue
        if source.is_symlink():
            raise BackupError(f"links simbólicos não são aceitos no escopo: {relative}")
        if source.is_file():
            if not _is_excluded(PurePosixPath(relative)):
                selected[relative] = source
            continue
        if not source.is_dir():
            raise BackupError(f"entrada de backup não é arquivo nem diretório: {relative}")
        for candidate in sorted(source.rglob("*")):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if not _is_within(resolved, root):
                raise BackupError(f"arquivo fora da raiz do backup: {candidate}")
            candidate_relative = PurePosixPath(candidate.relative_to(root).as_posix())
            if _is_excluded(candidate_relative):
                continue
            selected[candidate_relative.as_posix()] = candidate
    if not selected:
        raise BackupError("nenhum arquivo de dados encontrado no escopo informado")
    collision_keys: dict[tuple[str, ...], str] = {}
    for relative in selected:
        key = _windows_collision_key(relative)
        previous = collision_keys.setdefault(key, relative)
        if previous != relative:
            raise BackupError(f"caminhos colidem no Windows: {previous} e {relative}")
    return sorted(selected.items()), sorted(set(missing))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _snapshot_sqlite(source: Path, destination: Path) -> None:
    """Consolida um SQLite possivelmente em WAL sem copiar o arquivo cru."""
    # ``mode=ro`` é importante no drill e no app instalado: o backup não deve
    # criar journal, alterar pragmas persistentes ou exigir ACL de escrita na
    # pasta de dados original.
    uri_base = f"file:{quote(source.as_posix(), safe='/:')}"
    wal = source.with_name(source.name + "-wal")
    journal = source.with_name(source.name + "-journal")
    if not wal.exists() and not journal.exists():
        # Sem WAL/journal, immutable evita que o SQLite tente criar arquivos
        # auxiliares na pasta original e funciona mesmo sob ACL de leitura
        # estrita.
        origem = sqlite3.connect(f"{uri_base}?immutable=1", uri=True, timeout=10)
    else:
        try:
            origem = sqlite3.connect(f"{uri_base}?mode=ro", uri=True, timeout=10)
        except sqlite3.OperationalError as exc:
            # Com WAL pendente, immutable ignoraria transações confirmadas;
            # portanto falhamos fechado em vez de gerar um snapshot incompleto.
            raise BackupError("não foi possível abrir SQLite somente leitura com WAL pendente") from exc
    try:
        origem.execute("PRAGMA busy_timeout=10000")
        copia = sqlite3.connect(str(destination), timeout=10)
        try:
            origem.backup(copia, sleep=0.05)
            integrity = copia.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise BackupError("integrity_check do SQLite falhou durante o backup")
            copia.commit()
        finally:
            copia.close()
    finally:
        origem.close()


def _sqlite_metadata(path: Path) -> Mapping[str, object]:
    connection = sqlite3.connect(str(path), timeout=10)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        tables = connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()
    finally:
        connection.close()
    return {
        "integrity_check": integrity[0] if integrity else None,
        "table_count": int(tables[0]) if tables else 0,
    }


def _stage_files(root: Path, files: Iterable[tuple[str, Path]], stage: Path) -> list[dict[str, object]]:
    manifest_files: list[dict[str, object]] = []
    for relative, source in files:
        staged = stage / Path(*PurePosixPath(relative).parts)
        staged.parent.mkdir(parents=True, exist_ok=True)
        if relative == "leads.db":
            _snapshot_sqlite(source, staged)
        else:
            shutil.copy2(source, staged)
        entry: dict[str, object] = {
            "path": relative,
            "bytes": staged.stat().st_size,
            "sha256": _sha256_file(staged),
        }
        if relative == "leads.db":
            entry["sqlite"] = dict(_sqlite_metadata(staged))
        manifest_files.append(entry)
    return manifest_files


def _tar_add_regular(tar: tarfile.TarFile, source: Path, arcname: str) -> None:
    info = tar.gettarinfo(str(source), arcname=arcname)
    if not info.isfile():
        raise BackupError(f"somente arquivos regulares podem entrar no backup: {arcname}")
    with source.open("rb") as stream:
        tar.addfile(info, stream)


def _build_archive(stage: Path, manifest: Mapping[str, object]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        manifest_info.mode = 0o600
        manifest_info.mtime = int(datetime.now(timezone.utc).timestamp())
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))
        for item in manifest["files"]:
            relative = str(item["path"])
            _tar_add_regular(tar, stage / Path(*PurePosixPath(relative).parts), relative)
    return buffer.getvalue()


def _derive_key(password: str | bytes, salt: bytes, parameters: Mapping[str, object]) -> bytes:
    try:
        n = int(parameters["n"])
        r = int(parameters["r"])
        p = int(parameters["p"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BackupError("parâmetros de KDF inválidos") from exc
    # Limites evitam que um arquivo adulterado force consumo arbitrário de
    # memória/CPU durante a verificação.
    if n < 2**14 or n > 2**20 or n & (n - 1) or not 1 <= r <= 32 or not 1 <= p <= 16:
        raise BackupError("parâmetros de KDF fora dos limites permitidos")
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(_password_bytes(password))


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except (FileNotFoundError, OSError):
                pass


def _pack_encrypted(archive: bytes, password: str | bytes, file_count: int) -> tuple[bytes, dict[str, object]]:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    kdf_parameters = {"name": "scrypt", "n": 2**14, "r": 8, "p": 1}
    metadata: dict[str, object] = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cipher": "AES-256-GCM",
        "kdf": kdf_parameters,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest().upper(),
        "file_count": file_count,
    }
    metadata_bytes = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(metadata_bytes) > MAX_METADATA_BYTES:
        raise BackupError("metadados do backup excedem o limite")
    metadata_length = struct.pack(">I", len(metadata_bytes))
    aad = MAGIC + metadata_length + metadata_bytes
    key = _derive_key(password, salt, kdf_parameters)
    ciphertext = AESGCM(key).encrypt(nonce, archive, aad)
    return aad + ciphertext, metadata


def _unpack_encrypted(path: Path, password: str | bytes, max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES) -> tuple[dict[str, object], bytes]:
    if max_archive_bytes < 1:
        raise BackupError("limite de tamanho inválido")
    if not path.exists() or not path.is_file():
        raise BackupError(f"backup inexistente: {path}")
    maximum_file_bytes = max_archive_bytes + MAX_METADATA_BYTES + len(MAGIC) + 4 + 16
    if path.stat().st_size > maximum_file_bytes:
        raise BackupError("arquivo de backup excede o limite configurado")
    raw = path.read_bytes()
    if not raw.startswith(MAGIC):
        raise BackupError("formato de backup desconhecido")
    offset = len(MAGIC)
    if len(raw) < offset + 4:
        raise BackupError("backup truncado antes dos metadados")
    metadata_length = struct.unpack(">I", raw[offset : offset + 4])[0]
    if not 1 <= metadata_length <= MAX_METADATA_BYTES:
        raise BackupError("tamanho de metadados inválido")
    metadata_start = offset + 4
    metadata_end = metadata_start + metadata_length
    if metadata_end >= len(raw):
        raise BackupError("backup truncado antes do payload criptografado")
    try:
        metadata = json.loads(raw[metadata_start:metadata_end].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError("metadados inválidos") from exc
    if not isinstance(metadata, dict) or metadata.get("schema") != SCHEMA:
        raise BackupError("schema de backup não suportado")
    try:
        salt = base64.b64decode(str(metadata["salt"]), validate=True)
        nonce = base64.b64decode(str(metadata["nonce"]), validate=True)
        expected_hash = str(metadata["archive_sha256"]).upper()
        expected_bytes = int(metadata["archive_bytes"])
        kdf_parameters = metadata["kdf"]
    except (KeyError, TypeError, ValueError) as exc:
        raise BackupError("metadados criptográficos incompletos") from exc
    if len(salt) != 16 or len(nonce) != 12 or expected_bytes < 1 or expected_bytes > max_archive_bytes:
        raise BackupError("parâmetros de backup fora dos limites")
    aad = raw[:metadata_end]
    try:
        key = _derive_key(password, salt, kdf_parameters)
        archive = AESGCM(key).decrypt(nonce, raw[metadata_end:], aad)
    except InvalidTag as exc:
        raise BackupError("senha incorreta ou backup adulterado") from exc
    if len(archive) != expected_bytes or hashlib.sha256(archive).hexdigest().upper() != expected_hash:
        raise BackupError("hash do payload não confere")
    return metadata, archive


def _validate_member_name(name: str) -> str:
    if "\\" in name:
        raise BackupError(f"nome de membro inválido no tar: {name}")
    return _safe_relative(name)


def _read_manifest(
    archive: bytes,
    *,
    max_total_bytes: int = DEFAULT_MAX_RESTORED_BYTES,
) -> dict[str, object]:
    if max_total_bytes < 1:
        raise BackupError("limite total de restauração inválido")
    try:
        tar = tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise BackupError("payload não é um tar.gz válido") from exc
    try:
        members = tar.getmembers()
        manifests = [member for member in members if member.name == "manifest.json"]
        if len(manifests) != 1 or not manifests[0].isfile():
            raise BackupError("manifest.json ausente ou duplicado")
        stream = tar.extractfile(manifests[0])
        if stream is None:
            raise BackupError("manifest.json não pôde ser lido")
        try:
            manifest = json.loads(stream.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackupError("manifest.json inválido") from exc
        finally:
            stream.close()
    finally:
        tar.close()
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise BackupError("schema do manifest não suportado")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise BackupError("manifest sem arquivos")
    if len(files) > MAX_MANIFEST_FILES:
        raise BackupError("manifest excede o número máximo de arquivos")
    seen: set[str] = set()
    collision_keys: dict[tuple[str, ...], str] = {}
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise BackupError("entrada de arquivo inválida no manifest")
        relative = _validate_member_name(item["path"])
        if relative == "manifest.json" or relative in seen:
            raise BackupError("arquivo duplicado ou reservado no manifest")
        collision_key = _windows_collision_key(relative)
        previous = collision_keys.setdefault(collision_key, relative)
        if previous != relative:
            raise BackupError(f"caminhos colidem no Windows: {previous} e {relative}")
        if type(item.get("bytes")) is not int or item["bytes"] < 0:
            raise BackupError(f"tamanho inválido no manifest: {relative}")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise BackupError(f"hash inválido no manifest: {relative}")
        if item["bytes"] > max_total_bytes - total_bytes:
            raise BackupError("manifest excede o tamanho total restaurável")
        total_bytes += item["bytes"]
        seen.add(relative)
    # Rejeita membros ocultos, duplicados ou links inseridos fora do manifest.
    # Assim a verificação sem extração e a restauração cobrem exatamente o
    # mesmo conjunto de arquivos.
    try:
        tar = tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise BackupError("payload não pôde ser reaberto para validar membros") from exc
    try:
        archive_members: set[str] = set()
        expected_by_path = {str(item["path"]): item for item in files}
        archive_total_bytes = 0
        for member in tar.getmembers():
            if member.name == "manifest.json":
                continue
            relative = _validate_member_name(member.name)
            if relative in archive_members or relative not in seen or not member.isfile():
                raise BackupError(f"membro não permitido no backup: {relative}")
            expected = expected_by_path[relative]
            member_size = int(member.size)
            if member_size < 0 or member_size != int(expected["bytes"]):
                raise BackupError(f"tamanho real divergente no backup: {relative}")
            if member_size > max_total_bytes - archive_total_bytes:
                raise BackupError("membros do backup excedem o tamanho total restaurável")
            archive_total_bytes += member_size
            archive_members.add(relative)
        if archive_members != seen:
            raise BackupError("manifest não corresponde aos membros do backup")
    finally:
        tar.close()
    return manifest


def create_backup(
    source: str | os.PathLike[str] = DIR_DADOS,
    output: str | os.PathLike[str] | None = None,
    password: str | bytes = b"",
    *,
    scope: Sequence[str] = DEFAULT_SCOPE,
    overwrite: bool = False,
    require_independent_destination: bool = False,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
    max_restored_bytes: int = DEFAULT_MAX_RESTORED_BYTES,
) -> dict[str, object]:
    """Cria backup criptografado; retorna apenas metadados não sensíveis.

    ``require_independent_destination`` é uma trava opt-in para operações de
    recuperação: origem e destino precisam estar em dispositivos diferentes.
    Host, provedor, retenção e RPO/RTO continuam decisões do operador.
    """
    root = _resolve_directory(source)
    if output is None:
        raise BackupError("destino do backup é obrigatório")
    destination = Path(output).expanduser()
    if destination.exists() and not overwrite:
        raise BackupError(f"destino já existe; use overwrite explicitamente: {destination}")
    try:
        if _is_within(destination.resolve(), root):
            raise BackupError("destino do backup não pode ficar dentro da raiz de dados")
    except FileNotFoundError:
        pass
    if require_independent_destination:
        _require_independent_destination(root, destination)
    if max_archive_bytes < 1:
        raise BackupError("limite de tamanho inválido")
    if max_restored_bytes < 1:
        raise BackupError("limite total de restauração inválido")
    files, missing = _iter_scope_files(root, scope)
    with tempfile.TemporaryDirectory(prefix="prospectos-backup-stage-") as temporary:
        stage = Path(temporary)
        manifest_files = _stage_files(root, files, stage)
        manifest: dict[str, object] = {
            "schema": SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scope": "ProspectOS user data; credentials, sessions and logs excluded",
            "files": manifest_files,
            "missing_scope_entries": missing,
        }
        archive = _build_archive(stage, manifest)
        _read_manifest(archive, max_total_bytes=max_restored_bytes)
    if len(archive) > max_archive_bytes:
        raise BackupError(f"arquivo de backup excede o limite de {max_archive_bytes} bytes")
    payload, metadata = _pack_encrypted(archive, password, len(manifest_files))
    _atomic_write(destination, payload)
    return {
        "schema": SCHEMA,
        "output": str(destination),
        "encrypted": True,
        "cipher": metadata["cipher"],
        "file_count": len(manifest_files),
        "archive_bytes": len(archive),
        "backup_bytes": len(payload),
        "archive_sha256": metadata["archive_sha256"],
        "missing_scope_entries": missing,
    }


def verify_backup(
    backup: str | os.PathLike[str],
    password: str | bytes,
    *,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
    max_restored_bytes: int = DEFAULT_MAX_RESTORED_BYTES,
) -> dict[str, object]:
    """Autentica, descriptografa e valida o manifest sem extrair arquivos."""
    path = Path(backup).expanduser()
    metadata, archive = _unpack_encrypted(path, password, max_archive_bytes)
    manifest = _read_manifest(archive, max_total_bytes=max_restored_bytes)
    files = manifest["files"]
    if int(metadata.get("file_count", -1)) != len(files):
        raise BackupError("quantidade de arquivos não confere com os metadados")
    return {
        "schema": SCHEMA,
        "backup": str(path),
        "encrypted": True,
        "cipher": metadata["cipher"],
        "file_count": len(files),
        "archive_bytes": len(archive),
        "archive_sha256": metadata["archive_sha256"],
        "manifest_created_at": manifest.get("created_at"),
        "missing_scope_entries": manifest.get("missing_scope_entries", []),
        "files": [item["path"] for item in files],
    }


def restore_backup(
    backup: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    password: str | bytes,
    *,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
    max_restored_bytes: int = DEFAULT_MAX_RESTORED_BYTES,
) -> dict[str, object]:
    """Restaura para um diretório novo, verificando tamanho e hash por arquivo."""
    target = Path(destination).expanduser()
    if target.exists():
        raise BackupError("o destino de restauração deve ser novo e inexistente")
    target.parent.mkdir(parents=True, exist_ok=True)
    metadata, archive = _unpack_encrypted(Path(backup).expanduser(), password, max_archive_bytes)
    manifest = _read_manifest(archive, max_total_bytes=max_restored_bytes)
    expected = {str(item["path"]): item for item in manifest["files"]}
    restored: set[str] = set()
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.restore-", dir=str(target.parent)))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "manifest.json":
                    continue
                relative = _validate_member_name(member.name)
                item = expected.get(relative)
                if item is None or not member.isfile():
                    raise BackupError(f"membro não permitido no backup: {relative}")
                output = temporary / Path(*PurePosixPath(relative).parts)
                resolved = output.resolve()
                if not _is_within(resolved, temporary.resolve()):
                    raise BackupError(f"tentativa de path traversal: {relative}")
                output.parent.mkdir(parents=True, exist_ok=True)
                stream = tar.extractfile(member)
                if stream is None:
                    raise BackupError(f"membro não pôde ser lido: {relative}")
                try:
                    with output.open("wb") as destination_stream:
                        shutil.copyfileobj(stream, destination_stream)
                finally:
                    stream.close()
                if output.stat().st_size != int(item["bytes"]) or _sha256_file(output) != str(item["sha256"]).upper():
                    raise BackupError(f"hash/tamanho divergente após restauração: {relative}")
                restored.add(relative)
        if restored != set(expected):
            raise BackupError("nem todos os arquivos do manifest foram restaurados")
        # O destino inexistente foi validado antes do trabalho. O rename mantém
        # o resultado inteiro ou inexistente para consumidores que observam a
        # mesma unidade, sem substituir dados existentes.
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)
    return {
        "schema": SCHEMA,
        "backup": str(backup),
        "destination": str(target),
        "encrypted": True,
        "cipher": metadata["cipher"],
        "file_count": len(expected),
        "archive_sha256": metadata["archive_sha256"],
        "verified": True,
    }


def _read_password(confirm: bool = False) -> str:
    password = getpass("Senha do backup: ")
    if confirm:
        repeated = getpass("Repita a senha: ")
        if password != repeated:
            raise BackupError("as senhas não conferem")
    return password


def _password_from_args(password_stdin: bool, confirm: bool = False) -> str:
    if password_stdin:
        value = sys.stdin.readline().rstrip("\r\n")
        if not value:
            raise BackupError("senha vazia recebida em stdin")
        return value
    return _read_password(confirm=confirm)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup criptografado do ProspectOS")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="cria um backup criptografado")
    create.add_argument("--source", default=str(DIR_DADOS))
    create.add_argument("--output", required=True)
    create.add_argument("--overwrite", action="store_true")
    create.add_argument(
        "--require-independent-destination",
        action="store_true",
        help="falha se origem e destino estiverem no mesmo dispositivo/volume",
    )
    create.add_argument("--password-stdin", action="store_true", help="lê a senha de uma linha de stdin")
    verify = subparsers.add_parser("verify", help="verifica um backup sem extrair")
    verify.add_argument("--backup", required=True)
    verify.add_argument("--password-stdin", action="store_true")
    restore = subparsers.add_parser("restore", help="restaura para um diretório novo")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--destination", required=True)
    restore.add_argument("--password-stdin", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create":
            result = create_backup(
                source=args.source,
                output=args.output,
                password=_password_from_args(args.password_stdin, confirm=not args.password_stdin),
                overwrite=args.overwrite,
                require_independent_destination=args.require_independent_destination,
            )
        elif args.command == "verify":
            result = verify_backup(args.backup, _password_from_args(args.password_stdin))
        else:
            result = restore_backup(args.backup, args.destination, _password_from_args(args.password_stdin))
    except BackupError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercitado pelo entrypoint
    raise SystemExit(main())
