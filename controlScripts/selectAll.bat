@echo off
cd %~dp0
set winTitle=%1
start /min cmd.exe /c "keyb_control a -click %winTitle%"