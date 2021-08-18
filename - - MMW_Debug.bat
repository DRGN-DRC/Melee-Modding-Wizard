@echo off


C:\Python27\python.exe "%~dp0main.py" %*


:: Exit if no problems, otherwise pause so we can see what happened.
if [%ERRORLEVEL%]==[0] goto eof
pause > nul
echo Press any key to exit . . .