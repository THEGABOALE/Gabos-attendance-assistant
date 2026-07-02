@echo off
REM Lanzador de la CLI en Windows (CMD/PowerShell). Uso: gabo <comando>
setlocal
set "PROJECT=%~dp0"
set "PYTHONPATH=%PROJECT%src;%PYTHONPATH%"
"%PROJECT%.venv\Scripts\python.exe" -m attendance_assistant.cli %*
