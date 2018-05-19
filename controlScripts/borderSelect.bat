@echo off
cd %~dp0
set winTitle=%1
for /l %%i in (1,1,20) do (
	start /min cmd.exe /c "keyb_control b -click %winTitle%"
)