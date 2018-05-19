@echo off
set progName=%1
set progRunning=1

cd %~dp0
:waitForMainToClose
@For /f "Delims=:" %A in ('tasklist /v /fi "WINDOWTITLE eq %progName%"') do @if %A==INFO goto startProgram
goto waitForMainToClose

:startProgram
cd ..
start autorun.bat