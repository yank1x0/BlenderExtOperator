@echo off
set curr=%~dp0
rem cleanup
del /q /f %curr%..\resources\model_bases\*.blend1 >NUL 2>&1
del /q /f %curr%..\resources\raw_scans\*.blend1 >NUL 2>&1
set winTitle=%1
keyb_control.exe " " -close %winTitle%