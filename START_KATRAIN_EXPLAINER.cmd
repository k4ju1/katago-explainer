@echo off
title KaTrain - Move Explanations
cd /d "%~dp0"
if defined KATAGO_EXPLAINER_PYTHON (
    "%KATAGO_EXPLAINER_PYTHON%" scripts\launch_katrain.py %*
    goto finish
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\launch_katrain.py %*
    goto finish
)
py -3 -c "import sys; assert sys.version_info >= (3, 11)" >nul 2>&1
if not errorlevel 1 (
    py -3 scripts\launch_katrain.py %*
    goto finish
)
python -c "import sys; assert sys.version_info >= (3, 11)" >nul 2>&1
if not errorlevel 1 (
    python scripts\launch_katrain.py %*
    goto finish
)
echo Python 3.11 or later is required for installation.
echo Install Python or set KATAGO_EXPLAINER_PYTHON to its executable path.
pause
exit /b 1
:finish
if errorlevel 1 pause
