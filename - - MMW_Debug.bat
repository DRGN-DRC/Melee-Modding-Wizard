@echo off

python "%~dp0main.py" %*


if [%ERRORLEVEL%]==[0] goto eof

pause