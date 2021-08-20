:: 
@echo off

python "%~dp0main.py" test --path %*

:: Exit if no problems, otherwise pause so we can see what happened.
if [%ERRORLEVEL%]==[0] goto eof
pause > nul
echo Press any key to exit . . .