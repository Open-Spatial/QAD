@echo off
setlocal

if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\Program Files\QGIS 4.0.0"

if exist "%OSGEO4W_ROOT%\bin\o4w_env.bat" call "%OSGEO4W_ROOT%\bin\o4w_env.bat"

for %%D in ("%OSGEO4W_ROOT%\apps\qgis\bin" "%OSGEO4W_ROOT%\apps\qgis-dev\bin" "%OSGEO4W_ROOT%\apps\qgis-ltr\bin") do (
  if exist "%%~fD" set "PATH=%%~fD;%PATH%"
)

where pyuic6 >nul 2>nul && set "PYUIC=pyuic6"
if not defined PYUIC where pyuic5 >nul 2>nul && set "PYUIC=pyuic5"
if not defined PYUIC (
  echo Unable to find pyuic6 or pyuic5 in PATH.
  exit /b 1
)

cd /d %~dp0

echo Using %PYUIC%
call "%PYUIC%" --from-imports -o .\qad_dsettings_ui.py .\qad_dsettings.ui
call :rewrite_ui_import .\qad_dsettings_ui.py
call "%PYUIC%" --from-imports -o .\qad_pointerinput_settings_ui.py .\qad_pointerinput_settings.ui
call :rewrite_ui_import .\qad_pointerinput_settings_ui.py
call "%PYUIC%" --from-imports -o .\qad_dimensioninput_settings_ui.py .\qad_dimensioninput_settings.ui
call :rewrite_ui_import .\qad_dimensioninput_settings_ui.py
call "%PYUIC%" --from-imports -o .\qad_dimstyle_ui.py .\qad_dimstyle.ui
call :rewrite_ui_import .\qad_dimstyle_ui.py
call "%PYUIC%" --from-imports -o .\qad_dimstyle_details_ui.py .\qad_dimstyle_details.ui
call :rewrite_ui_import .\qad_dimstyle_details_ui.py
call "%PYUIC%" --from-imports -o .\qad_dimstyle_new_ui.py .\qad_dimstyle_new.ui
call :rewrite_ui_import .\qad_dimstyle_new_ui.py
call "%PYUIC%" --from-imports -o .\qad_dimstyle_diff_ui.py .\qad_dimstyle_diff.ui
call :rewrite_ui_import .\qad_dimstyle_diff_ui.py
call "%PYUIC%" --from-imports -o .\qad_options_ui.py .\qad_options.ui
call :rewrite_ui_import .\qad_options_ui.py
call "%PYUIC%" --from-imports -o .\qad_gripcolor_ui.py .\qad_gripcolor.ui
call :rewrite_ui_import .\qad_gripcolor_ui.py
call "%PYUIC%" --from-imports -o .\qad_windowcolor_ui.py .\qad_windowcolor.ui
call :rewrite_ui_import .\qad_windowcolor_ui.py
call "%PYUIC%" --from-imports -o .\qad_tooltip_appearance_ui.py .\qad_tooltip_appearance.ui
call :rewrite_ui_import .\qad_tooltip_appearance_ui.py
call "%PYUIC%" --from-imports -o .\qad_rightclick_ui.py .\qad_rightclick.ui
call :rewrite_ui_import .\qad_rightclick_ui.py
exit /b %errorlevel%

:rewrite_ui_import
powershell -NoProfile -Command "(Get-Content '%~1') -replace '^from PyQt[56] import QtCore, QtGui, QtWidgets$','from qgis.PyQt import QtCore, QtGui, QtWidgets' | Set-Content '%~1'"
exit /b %errorlevel%
	
