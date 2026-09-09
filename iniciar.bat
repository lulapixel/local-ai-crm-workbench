@echo off
cd /d "%~dp0"

set PASTA_BACKEND=%~dp0backend
set PASTA_FRONTEND=%~dp0frontend
set PASTA_LOGS=%~dp0logs
set PASTA_SCRIPTS=%~dp0scripts

if not exist "%PASTA_LOGS%" mkdir "%PASTA_LOGS%"
if not exist "%PASTA_LOGS%\vazio.txt" type nul > "%PASTA_LOGS%\vazio.txt"

echo Verificando se o backend ja esta rodando...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:5000/api/metricas -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Backend ja estava rodando.
) else (
    echo Iniciando o backend...
    powershell -NoProfile -Command "Start-Process '%PASTA_BACKEND%\venv\Scripts\python.exe' -ArgumentList 'app.py' -WorkingDirectory '%PASTA_BACKEND%' -WindowStyle Hidden -RedirectStandardOutput '%PASTA_LOGS%\backend-saida.log' -RedirectStandardError '%PASTA_LOGS%\backend-erro.log' -RedirectStandardInput '%PASTA_LOGS%\vazio.txt'"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PASTA_SCRIPTS%\wait-http.ps1" -Uri "http://127.0.0.1:5000/api/metricas" -TimeoutSec 20
    if errorlevel 1 (
        echo Backend nao respondeu dentro do prazo. Consulte logs\backend-erro.log.
        exit /b 1
    )
)

echo Verificando se a interface ja esta rodando...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Interface ja estava rodando.
) else (
    echo Iniciando a interface...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c','npm.cmd run dev' -WorkingDirectory '%PASTA_FRONTEND%' -WindowStyle Hidden -RedirectStandardOutput '%PASTA_LOGS%\frontend-saida.log' -RedirectStandardError '%PASTA_LOGS%\frontend-erro.log' -RedirectStandardInput '%PASTA_LOGS%\vazio.txt'"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PASTA_SCRIPTS%\wait-http.ps1" -Uri "http://localhost:5173" -TimeoutSec 30
    if errorlevel 1 (
        echo Interface nao respondeu dentro do prazo. Consulte logs\frontend-erro.log.
        exit /b 1
    )
)

start http://localhost:5173
