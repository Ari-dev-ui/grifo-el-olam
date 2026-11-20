@echo off
setlocal
cd /d "%~dp0"
echo Grifo El Olam - Inicio local
if exist ".venv\Scripts\python.exe" goto instalar
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 -m venv .venv
goto comprobar
:usar_python
python -m venv .venv
:comprobar
if not exist ".venv\Scripts\python.exe" goto error_python
:instalar
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error_instalacion
echo.
echo Abre http://127.0.0.1:5000 cuando el servidor indique que esta listo.
echo Usuario demo: admin1 / Clave: OlamDemo2026!
".venv\Scripts\python.exe" app.py --demo
pause
exit /b
:error_python
echo No se pudo crear el entorno. Instala Python 3.11 o posterior y marca Add Python to PATH.
pause
exit /b 1
:error_instalacion
echo No se completaron las dependencias. Comprueba Internet y la version de Python.
pause
exit /b 1
