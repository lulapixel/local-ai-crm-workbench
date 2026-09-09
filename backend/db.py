"""Acesso ao banco (SQLite), configurações persistidas e backup.

Os módulos de rotas devem sempre acessar CAMINHO_BANCO via `db.CAMINHO_BANCO`
(atributo do módulo, não import direto do nome) - é isso que permite aos testes
apontarem tudo para um banco temporário com um único monkeypatch.
"""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from paths import DIR_DADOS, DIR_RECURSOS

logger = logging.getLogger(__name__)

# APP_DIR aponta pros RECURSOS (código, scraper .exe) - continua exportado porque
# jobs.py e outros o usam. Dados graváveis (banco, backups) vêm de DIR_DADOS:
# na fonte é a mesma pasta de sempre; empacotado vira %APPDATA%\ProspectOS.
APP_DIR = DIR_RECURSOS
CAMINHO_BANCO = DIR_DADOS / "leads.db"
PASTA_BACKUPS = DIR_DADOS / "backups"
MAX_BACKUPS_MANTIDOS = 20

CHAVES_CONFIG_VALIDAS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "pagespeed": "PAGESPEED_API_KEY",
    "places": "PLACES_API_KEY",
}

# Chaves que são segredo de verdade: ficam no cofre de credenciais do sistema
# (Windows Credential Manager, via keyring/DPAPI), nunca em plaintext no
# leads.db - o banco entra nos backups automáticos, o cofre não.
CHAVES_SECRETAS = set(CHAVES_CONFIG_VALIDAS)
_SERVICO_KEYRING = "ProspectOS"


class ConfigSecretStorageError(RuntimeError):
    """Indica que um segredo não pôde ser gravado no cofre do sistema.

    O banco SQLite pode ser copiado junto com backups e, por isso, nunca é um
    fallback aceitável para credenciais. As rotas transformam este erro em 503
    para deixar claro que a operação não foi concluída e não vazar detalhes.
    """


def _keyring_obter(chave):
    try:
        import keyring
        return keyring.get_password(_SERVICO_KEYRING, chave)
    except Exception:
        logger.debug("keyring indisponível ao ler a chave %s", chave)
        return None


def _keyring_salvar(chave, valor):
    try:
        import keyring
        keyring.set_password(_SERVICO_KEYRING, chave, valor)
        return True
    except Exception:
        logger.exception("keyring indisponível ao salvar a chave %s - fallback plaintext recusado", chave)
        return False


def _keyring_apagar(chave):
    try:
        import keyring
        keyring.delete_password(_SERVICO_KEYRING, chave)
    except Exception:
        pass  # a chave pode simplesmente não existir no cofre


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.execute("PRAGMA busy_timeout=10000")
    conexao.execute("PRAGMA foreign_keys=ON")
    return conexao


def linha_para_dict(linha):
    return dict(linha)


def obter_config(chave, default=None):
    """Lê uma configuração. Ordem de prioridade:
    1. cofre de credenciais (só chaves secretas, gravadas pela UI)
    2. tabela `configuracoes` (somente configs comuns; segredos legados não são retornados)
    3. variável de ambiente / .env"""
    if chave in CHAVES_SECRETAS:
        valor = _keyring_obter(chave)
        if valor:
            return valor

    conexao = conectar()
    try:
        linha = conexao.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
        ).fetchone()
    finally:
        conexao.close()

    if linha and linha["valor"]:
        if chave in CHAVES_SECRETAS:
            logger.error("segredo legado %s encontrado no banco; keyring indisponível ou não migrado", chave)
            chave_env = CHAVES_CONFIG_VALIDAS[chave]
            return os.environ.get(chave_env, default)
        return linha["valor"]

    chave_env = CHAVES_CONFIG_VALIDAS.get(chave, chave)
    return os.environ.get(chave_env, default)


def _apagar_config_db(chave):
    conexao = conectar()
    try:
        conexao.execute("DELETE FROM configuracoes WHERE chave = ?", (chave,))
        conexao.commit()
    finally:
        conexao.close()


def salvar_config(chave, valor):
    # chave secreta vai pro cofre; qualquer cópia plaintext antiga sai do banco.
    # Se o keyring estiver indisponível, falha fechado: não gravar segredo no banco.
    if chave in CHAVES_SECRETAS:
        if not _keyring_salvar(chave, valor):
            raise ConfigSecretStorageError(
                "cofre de credenciais indisponível; a chave não foi salva"
            )
        _apagar_config_db(chave)
        return

    conexao = conectar()
    try:
        conexao.execute(
            """
            INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES (?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor, atualizado_em = excluded.atualizado_em
            """,
            (chave, valor, datetime.now().isoformat(timespec="seconds")),
        )
        conexao.commit()
    finally:
        conexao.close()


def migrar_chaves_para_keyring():
    """Migração de segurança (roda no startup): move chaves de API que ficaram
    em plaintext na tabela `configuracoes` para o cofre de credenciais do sistema
    e apaga a cópia do banco. Idempotente; se o keyring estiver indisponível,
    preserva o legado para migração posterior, mas a leitura fail-closed não o retorna."""
    conexao = conectar()
    try:
        linhas = conexao.execute(
            "SELECT chave, valor FROM configuracoes WHERE chave IN ({}) AND valor IS NOT NULL AND valor != ''".format(
                ",".join("?" for _ in CHAVES_SECRETAS)
            ),
            sorted(CHAVES_SECRETAS),
        ).fetchall()
    finally:
        conexao.close()

    for linha in linhas:
        if _keyring_salvar(linha["chave"], linha["valor"]):
            _apagar_config_db(linha["chave"])
            logger.info("chave %s migrada do banco para o cofre de credenciais", linha["chave"])


def fazer_backup_banco():
    """Cria snapshot consistente do SQLite e mantém só os N mais recentes.

    O banco usa WAL; por isso uma cópia de arquivo simples pode deixar dados
    confirmados apenas no ``-wal``. A API ``backup`` do SQLite consolida uma
    visão consistente em arquivo temporário, valida a integridade e só então
    publica o destino com replace atômico.
    """
    if not CAMINHO_BANCO.exists():
        return

    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
    destino = PASTA_BACKUPS / f"leads_{carimbo}.db"
    temporario = PASTA_BACKUPS / f".{destino.name}.{os.getpid()}.tmp"
    try:
        origem = sqlite3.connect(CAMINHO_BANCO, timeout=10)
        try:
            origem.execute("PRAGMA busy_timeout=10000")
            copia = sqlite3.connect(temporario)
            try:
                origem.backup(copia, sleep=0.25)
                integridade = copia.execute("PRAGMA integrity_check").fetchone()
                if not integridade or integridade[0] != "ok":
                    raise sqlite3.DatabaseError("integrity_check do backup não retornou ok")
                copia.commit()
            finally:
                copia.close()
        finally:
            origem.close()
        os.replace(temporario, destino)
        logger.info("backup do banco criado em %s", destino)
    except (OSError, sqlite3.Error):
        logger.exception("não foi possível criar backup do banco")
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            logger.warning("não foi possível remover temporário de backup %s", temporario)
        return

    arquivos = sorted(PASTA_BACKUPS.glob("leads_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for antigo in arquivos[MAX_BACKUPS_MANTIDOS:]:
        try:
            antigo.unlink(missing_ok=True)
        except OSError:
            # A retenção não pode transformar um backup recém-validado em
            # falha de job só porque um snapshot antigo está bloqueado ou tem
            # ACL restritiva. Ele será tentado novamente na próxima rodada.
            logger.warning("não foi possível remover backup antigo %s", antigo)
