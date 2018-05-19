@echo off
cd %~dp0
set winTitle=%1
keyb_control.exe RCTRL -press %winTitle% &^
keyb_control.exe NUMPAD6 -press %winTitle%