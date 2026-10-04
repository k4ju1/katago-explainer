@echo off
title KataGo Explainer
cd /d "%~dp0"
set "explainer_python=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%explainer_python%" (
    "%explainer_python%" -m explainer.server --open-browser
) else (
    python -m explainer.server --open-browser
)
if errorlevel 1 pause
