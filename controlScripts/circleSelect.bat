@echo off
cd %~dp0
set winTitle=%1
rem A PROBLEMATIC WORKAROUND:
for /l %%i in (1,1,20) do (
	start /min cmd.exe /c "start keyb_control.exe c -click %winTitle%"
)