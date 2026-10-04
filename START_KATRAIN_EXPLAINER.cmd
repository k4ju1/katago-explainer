@echo off
title KaTrain - Move Explanations
cd /d "%~dp0"
set "explainer_python=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%explainer_python%" (
    "%explainer_python%" scripts\launch_katrain.py
) else (
    python scripts\launch_katrain.py
)
if errorlevel 1 pause
