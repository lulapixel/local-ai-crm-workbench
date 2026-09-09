@echo off
chcp 65001 > NUL
echo =======================================================
echo  Iniciando Servidor MCP do ProspectOS (Stdio Mode)
echo =======================================================
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
    echo Runtime canonico ausente: backend\venv\Scripts\python.exe
    echo Instale backend\requirements.txt no venv do projeto antes de iniciar o MCP.
    exit /b 1
)
venv\Scripts\python.exe -m mcp_server
