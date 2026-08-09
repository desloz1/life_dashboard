@echo off
rem Executa o Organizador Pessoal (PySide6)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado no PATH. Instale o Python 3.12+ e tente novamente.
    pause
    exit /b 1
)

python main.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao executar o programa.
    pause
)
