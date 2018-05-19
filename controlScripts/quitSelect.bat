@echo off
cd %~dp0
set winTitle=%1
start /min execute.bat "start /wait keyb_control ESC -click %winTitle%"