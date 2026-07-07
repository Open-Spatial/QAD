@echo off
setlocal

if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\Program Files\QGIS 4.0.0"

if exist "%OSGEO4W_ROOT%\bin\o4w_env.bat" call "%OSGEO4W_ROOT%\bin\o4w_env.bat"

for %%D in ("%OSGEO4W_ROOT%\apps\qgis\bin" "%OSGEO4W_ROOT%\apps\qgis-dev\bin" "%OSGEO4W_ROOT%\apps\qgis-ltr\bin") do (
  if exist "%%~fD" set "PATH=%%~fD;%PATH%"
)

where pyrcc6 >nul 2>nul && set "PYRCC=pyrcc6"
if not defined PYRCC where pyrcc5 >nul 2>nul && set "PYRCC=pyrcc5"
if not defined PYRCC (
  echo Unable to find pyrcc6 or pyrcc5 in PATH.
  exit /b 1
)

cd /d %~dp0

echo Using %PYRCC%
call "%PYRCC%" -o qad_rc.py qad.qrc
call :rewrite_rc_import qad_rc.py
call "%PYRCC%" -o qad_dsettings_rc.py qad_dsettings.qrc
call :rewrite_rc_import qad_dsettings_rc.py
exit /b %errorlevel%

:rewrite_rc_import
powershell -NoProfile -Command "(Get-Content '%~1') -replace '^from PyQt[56] import QtCore$','from qgis.PyQt import QtCore' | Set-Content '%~1'"
exit /b %errorlevel%
