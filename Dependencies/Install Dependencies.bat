:: Created by DRGN
:: 8/18/2021
:: v1.0
@echo off
setlocal EnableDelayedExpansion


	:: Set an install directory, and 
	:: see if Python is installed there.

set pythonDir=C:\Python27
if exist "%pythonDir%\python.exe" (
    echo Skipping Python 2.7 installation, since it's already installed.
    goto ModuleInstallation
)


	:InstallPython

:: Get the python installer filename and python version
for /R .\ %%G in (python-*.msi) do set pythonInstaller=%%~nxG
for /f "tokens=1,2,3,4 delims=-." %%G in ("%pythonInstaller%") do set pythonVersion=%%H.%%I.%%J

:: Run the installer
echo Installing Python v%pythonVersion%...
msiexec /i %pythonInstaller% /passive TargetDir=%pythonDir%
if not [%ERRORLEVEL%]==[0] goto :PythonInstallFailed
echo Python installed.


	:ModuleInstallation

:: Temporarily add python locations to PATH so we can reference pip. 
:: The path variable for the current session may not have these yet.
set PATH=%pythonDir%;%pythonDir%\Scripts;%PATH%

echo.
echo Installing supplementary Python modules...
:: Install the python module wheels
for %%G in ("*.whl") do (
    set returnCode=
    call :InstallModule "%%G" returnCode
    if not !returnCode!==0 goto :ModuleInstallFailed
)


:: Install ruamel.yaml; must be done last
echo 	- ruamel.yaml...
%pythonDir%\python.exe -m pip install --quiet --quiet --no-index --disable-pip-version-check "ruamel.yaml-0.16.13-py2.py3-none-any.whl" 1> nul
if not %ERRORLEVEL%==0 goto :ModuleInstallFailed


:: Success
color 02
echo.
echo Dependency installation complete.
set exitCode=0
goto Exit


:PythonInstallFailed
color 04
echo.
echo Python installation failed.
set exitCode=1
goto Exit


:ModuleInstallFailed
color 04
echo.
echo Supplementary module installation failed.
set exitCode=2


:Exit
endlocal
echo Press any key to exit . . .
pause > nul
exit /b %exitCode%


:InstallModule
:: Takes in 2 arguments: 
::	- A relative path to a .whl file to install
::	- A return code variable, so we can check the result of the installation
for /f "tokens=1 delims=-" %%G in (%1) do set moduleName=%%G
:: Skip ruamel.yaml; it must be done last
if %moduleName%==ruamel.yaml (
    set %2=0
    goto :eof
)
echo 	- %moduleName%...
%pythonDir%\python.exe -m pip install --quiet --quiet --no-index --disable-pip-version-check %1 1> nul
set %2=%ERRORLEVEL%
goto :eof