@echo off
cd %~dp0
set winTitle=%1
keyb_control.exe CTRL -press %winTitle% &^
keyb_control.exe j -click %winTitle% &^
keyb_control.exe CTRL -release %winTitle%