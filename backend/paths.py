"""Caminhos centrais do app: onde ficam os recursos (read-only) e os dados (graváveis).

Dois modos de execução:

- **Fonte** (clone do repo, `py app.py`): tudo fica na pasta do projeto, como sempre
  foi — nada muda para quem desenvolve ou roda o app. O executor oficial de testes
  pode ativar explicitamente um diretório de dados temporário, sem alterar este
  padrão.
- **Empacotado** (PyInstaller, `sys.frozen`): o código e os recursos viram um bundle
  read-only (possivelmente em Program Files), então os dados do usuário (banco,
  backups, saídas, sessão do Instagram) PRECISAM ir para uma pasta gravável —
  `%APPDATA%\\ProspectOS`. Sem essa separação, o app instalado não consegue gravar
  nada e um update apagaria os leads.

Regra prática para os outros módulos:
- arquivo que o app só LÊ e vem junto do código (scraper .exe, os .py do instagram,
  o build do frontend) → `caminho_recurso(...)`
- arquivo que o app ESCREVE (leads.db, backups/, saidas/, queries.txt, logs/,
  instagram/sessao/, instagram/comentarios/) → `caminho_dados(...)`
"""

import os
import sys
import tempfile
from pathlib import Path

# PyInstaller define sys.frozen no executável gerado
EMPACOTADO = bool(getattr(sys, "frozen", False))

_DIR_FONTE = Path(__file__).parent

if EMPACOTADO:
    # --onedir: recursos adicionados via --add-data ficam em sys._MEIPASS
    # (na prática a pasta _internal ao lado do .exe)
    DIR_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    DIR_DADOS = Path(os.environ.get("APPDATA", str(Path.home()))) / "ProspectOS"
else:
    DIR_RECURSOS = _DIR_FONTE
    _modo_teste = os.environ.get("PROSPECTOS_TEST_MODE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    _dados_teste = os.environ.get("PROSPECTOS_TEST_DATA_DIR")
    _dados_teste_path = Path(_dados_teste).expanduser() if _dados_teste else None
    # O override exige as duas marcas: evita que uma variável solta redirecione
    # dados reais de uma execução normal do aplicativo.
    if _modo_teste and _dados_teste_path and _dados_teste_path.is_absolute():
        DIR_DADOS = _dados_teste_path
    else:
        DIR_DADOS = _DIR_FONTE


def caminho_recurso(*partes):
    """Caminho de um recurso read-only distribuído junto com o app."""
    return DIR_RECURSOS.joinpath(*partes)


def caminho_dados(*partes, criar_pai=False):
    """Caminho de um arquivo/pasta de dados do usuário (sempre gravável).

    Com criar_pai=True, garante que o diretório pai exista antes de devolver —
    útil pra quem vai abrir o arquivo pra escrita logo em seguida.
    """
    caminho = DIR_DADOS.joinpath(*partes)
    if criar_pai:
        caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


def escrever_texto_atomico(caminho, conteudo, *, encoding="utf-8"):
    """Substitui um arquivo de texto sem truncar a versão anterior em falhas."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline="",
            dir=str(caminho.parent),
            prefix=f".{caminho.name}.",
            suffix=".tmp",
            delete=False,
        ) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
        temporario = None
    finally:
        if temporario is not None:
            try:
                temporario.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def garantir_pastas_de_dados():
    """Cria a estrutura de pastas graváveis (chamado no startup do app)."""
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    for sub in ("backups", "saidas", "logs", Path("instagram") / "sessao", Path("instagram") / "comentarios"):
        (DIR_DADOS / sub).mkdir(parents=True, exist_ok=True)
