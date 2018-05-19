@echo off
cd %~dp0
set winTitle=%1
start /wait keyb_control.exe ALT -press %winTitle%
start /wait keyb_control.exe F10 -click %winTitle%
start /wait keyb_control.exe ALT -release %winTitle%
rem keyb_control.exe ALT -click %winTitle%