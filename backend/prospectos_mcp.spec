# -*- mode: python ; coding: utf-8 -*-
"""Build do servidor MCP empacotado do ProspectOS (PyInstaller, --onedir).

Uso:
    py -m PyInstaller prospectos_mcp.spec
"""

import os
from pathlib import Path

RAIZ = Path(SPECPATH)

datas = [
    (str(RAIZ / "instagram" / "raspar_comentarios.py"), "instagram"),
    (str(RAIZ / "instagram" / "enriquecer_perfis.py"), "instagram"),
]

a = Analysis(
    ["mcp_server/__main__.py"],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "keyring.backends.Windows",
        "mcp",
        "mcp.server.fastmcp",
        "requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "waitress"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ProspectOS-MCP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(RAIZ / "prospectos.ico") if (RAIZ / "prospectos.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ProspectOS-MCP",
)
