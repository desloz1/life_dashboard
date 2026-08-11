@echo off
setlocal EnableExtensions
rem Executa o Organizador Pessoal (PySide6).
rem Detecta Python e dependencias; instala automaticamente se faltarem.
cd /d "%~dp0"

set "PYTHON_EXE="
set "PY_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=powershell.exe"

rem ------------------------------------------------------------------
rem 1) Procurar um Python ja instalado
rem ------------------------------------------------------------------
rem 1a) instalação padrão por usuário (python.org). Prioridade ao 3.12+,
rem     pois o Scrapling exige Python 3.10+.
if not defined PYTHON_EXE (
    for %%v in (312 313 311 310) do (
        if exist "%LocalAppData%\Programs\Python\Python%%v\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python%%v\python.exe"
    )
)

rem 1b) python.exe no PATH (expansao nativa do cmd, sem where.exe). Só se
rem     não achou um 3.10+ por usuário acima; a checagem de versão (1e) garante.
if not defined PYTHON_EXE (
    for %%i in (python.exe) do set "PYTHON_EXE=%%~$PATH:i"
)

rem 1c) instalacao local conhecida desta maquina
if not defined PYTHON_EXE (
    if exist "C:\PYTHON\python.exe" set "PYTHON_EXE=C:\PYTHON\python.exe"
)

rem 1d) launcher "py" (encaminha -c/-m/scripts para o interpretador)
if not defined PYTHON_EXE (
    if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Launcher\py.exe"
)

rem 1e) exige Python >= 3.10 (Scrapling não roda em versões anteriores)
if defined PYTHON_EXE (
    "%PYTHON_EXE%" -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if errorlevel 1 set "PYTHON_EXE="
)

rem ------------------------------------------------------------------
rem 2) Python ausente: instalar automaticamente
rem ------------------------------------------------------------------
if not defined PYTHON_EXE (
    echo Python nao encontrado. Tentando instalar o Python 3.12...
    call :install_python
    rem re-verifica apos a instalacao
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    if not defined PYTHON_EXE for %%i in (python.exe) do set "PYTHON_EXE=%%~$PATH:i"
)

if not defined PYTHON_EXE (
    echo.
    echo Nao foi possivel instalar o Python automaticamente.
    echo Baixe e instale o Python 3.12+ em https://www.python.org/downloads/
    echo e execute este arquivo novamente.
    pause
    exit /b 1
)

rem ------------------------------------------------------------------
rem 3) Verificar e instalar dependencias
rem ------------------------------------------------------------------
echo Python encontrado: %PYTHON_EXE%
"%PYTHON_EXE%" -c "import PySide6, qtawesome, requests, keyring, lxml, scrapling" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias do app...
    call :install_deps "%PYTHON_EXE%"
    if errorlevel 1 (
        echo.
        echo Falha ao instalar as dependencias. Verifique sua conexao e tente novamente.
        pause
        exit /b 1
    )
)

rem ------------------------------------------------------------------
rem 4) Executar o app
rem ------------------------------------------------------------------
"%PYTHON_EXE%" main.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao executar o programa.
    pause
)
exit /b 0

rem ==================================================================
rem Sub-rotinas
rem ==================================================================

:install_python
    rem tenta winget (via caminho completo, pois pode nao estar no PATH)
    if exist "%LocalAppData%\Microsoft\WindowsApps\winget.exe" (
        "%LocalAppData%\Microsoft\WindowsApps\winget.exe" install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements >nul 2>nul
        if exist "%LocalAppData%\Programs\Python\Python312\python.exe" exit /b 0
    )

    rem fallback: instalador oficial da python.org
    set "PY_INSTALLER=%TEMP%\python-3.12.10-amd64.exe"
    if not exist "%PY_INSTALLER%" (
        echo Baixando instalador do Python...
        "%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('%PY_URL%','%PY_INSTALLER%')"
    )
    if not exist "%PY_INSTALLER%" exit /b 1

    echo Instalando Python (pode levar alguns minutos)...
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0
    exit /b %errorlevel%

:install_deps
    rem %1 = caminho do interpretador
    "%~1" -m ensurepip --upgrade >nul 2>nul
    "%~1" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
    "%~1" -c "import PySide6, qtawesome, requests, keyring, lxml, scrapling" >nul 2>nul
    exit /b %errorlevel%
