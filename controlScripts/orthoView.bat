@echo off
cd %~dp0
set winTitle=%1
timeout 1 >null
keyb_control NUMPAD5 -click %winTitle%