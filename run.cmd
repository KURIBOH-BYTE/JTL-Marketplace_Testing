@echo off
REM Startet ein Werkzeug ohne venv und ohne PYTHONPATH von Hand zu setzen.
REM   run.cmd build_import --platform galaxus <datei>
REM   run.cmd jtl_import --mapping
REM   run.cmd inspect_csv samples\export\auftraege.csv
setlocal
if "%~1"=="" (
  echo Aufruf: run.cmd ^<werkzeug^> [argumente]
  echo.
  echo Verfuegbar:
  for %%f in ("%~dp0tools\*.py") do echo   %%~nf
  exit /b 2
)
set "TOOL=%~dp0tools\%~1.py"
if not exist "%TOOL%" (
  echo Unbekanntes Werkzeug: %~1
  exit /b 2
)
shift
set "ARGS=%1"
:collect
shift
if "%~1"=="" goto run
set "ARGS=%ARGS% %1"
goto collect
:run
py "%TOOL%" %ARGS%
