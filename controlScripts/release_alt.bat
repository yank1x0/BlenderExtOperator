@echo off
cd %~dp0
set winTitle=%1
keyb_control.exe ALT -release %winTitle%