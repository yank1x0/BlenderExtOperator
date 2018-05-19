@echo off
setlocal enabledelayedexpansion

set fileToOverrideDir=%1
set fileToOverride=%2
set indicator=%3
set newLine=%4
set occurence=%5

set /a occurence_counter=0

for /f tokens^=1^ delims^=^" %%a in ( 'echo !fileToOverrideDir!' ) do ( 
		 set fileToOverrideDir=%%a
	 )


set tempFile="%fileToOverrideDir%\temp"
set full_override_path=%fileToOverrideDir%\%fileToOverride%

break >%tempFile%
for /f "usebackq tokens=*" %%i in ("!full_override_path!") do ( 
	set line=%%i
	set override=false
	for /f %%a in ('echo !line! ^| find "!indicator!"') do ( 
		if not "%%a"=="" ( 
			set /a occurence_counter=!occurence_counter!+1
			if "!occurence_counter!"=="!occurence!" ( 
				set override=true
				echo !indicator!=!newLine! >>%tempFile%
			 )
			if "!occurence!"=="" ( 
				set override=true
				echo !indicator!=!newLine! >>%tempFile%
			 )
		 )
	 )
	if "!override!"=="false" echo !line! >>%tempFile%
	 
 )
del /q /s "%full_override_path%" >NUL

ren %tempFile% %fileToOverride% >NUL

endlocal