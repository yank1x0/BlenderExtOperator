@echo off
cd %~dp0
set winTitle=%1
keyb_control.exe NUMPAD6 -release %winTitle% &^
keyb_control.exe RCTRL -release %winTitle%