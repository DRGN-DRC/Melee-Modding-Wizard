:: 
@echo off

python "%~dp0main.py" test --path %*

timeout 5

if [%ERRORLEVEL%]==[0] exit /b

pause