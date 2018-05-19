@echo off
setlocal enabledelayedexpansion
set command=start
:loop
	set command=!command! %1
	shift
	if "%~1"=="" goto start
	goto loop

:start
	echo !command!
	!command!
endlocal