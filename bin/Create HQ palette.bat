@echo off

:: Get the input file path, without extension
set inputFile=%~dpn1
set outputFile=%inputFile%_+256p.png

if ["%inputFile%"]==[] (
    echo No texture file provided.
    echo.
    echo A texture file should be provided as the first argument.
    echo.
    echo Press any key to exit. . .
    pause > nul
    goto eof
)

echo Outputting as "%outputFile%"

cd /d %~dp0
pngquant.exe --speed 1 --output "%outputFile%" 256 "%inputFile%.png"
