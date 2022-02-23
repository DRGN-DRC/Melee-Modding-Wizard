@echo off

:: You may uncomment one of the following lines to 
:: control whether Dolphin is run in Debug Mode.

python "%~dp0main.py" test --boot %*
::python "%~dp0main.py" test --debug --boot %*


:: Exit if no problems, otherwise pause so we can see what happened.
if [%ERRORLEVEL%]==[0] goto :EOF
color 0C
echo Press any key to exit . . .
pause > nul