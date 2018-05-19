@echo off
setlocal enabledelayedexpansion
set logic=%1
set selected_file=%2
rem IF START_PROG RUNS THE REFINER, KEEP REFERENCE TO THE 4 FILES SELECTED BY USER
set HEAD_FILE=%3
set UPPER_JAW_FILE=%4
set LOWER_JAW_FILE=%5

set logs_file=..\log.txt

set curr=%~dp0
set reg_key=HKEY_CURRENT_USER\SOFTWARE\IvoryDigital

goto start_blender

:replace_in_string
	set str=%1
	set replace_what=%2
	set replace_with=%3
	set replace_result=
	set /a ind=0
	:replace_loop
		set char=!str:~%ind%,1!
		if "!char!"=="!replace_what!" ( 

			if !replace_result!=="" ( set replace_result=!replace_with!
			 ) else ( set replace_result=!replace_result!!replace_with!
			 )
			
		 ) else ( 

			if !replace_result!=="" ( set replace_result=!char!
			 ) else ( set replace_result=!replace_result!!char!
			 )

			 )

		set /a ind=!ind!+1
		if NOT "!char!"=="" ( 
			goto replace_loop
		 )
	goto:eof

:start_blender
	rem set the correct teeth folder
	if "%logic%"=="main_refiner.py" set selected_teeth_dir="NONE"

	call:replace_in_string %selected_teeth_dir% ^\ ^\^\
	set selected_teeth_dir=%replace_result%
	for /f tokens^=2^ delims^=^" %%i in ( 'reg query !reg_key! /v ^"modules^"' ) do ( 
		set classes_path=%%i
	 )

	for /f tokens^=2^ delims^=^" %%i in ( 'reg query !reg_key! /v ^"location^"' ) do ( 
		set install_loc=%%i
	 )

	if not exist "!selected_teeth_dir!" set selected_teeth_dir=NONE
	cd %curr%
	rem call "override_line.bat" "!classes_path!" Constants.py TEETH_FOLDER "!selected_teeth_dir!" 1
	rem call:replace_in_string %install_loc% ^\ ^\^\
	rem call "override_line.bat" "!classes_path!" Constants.py INSTALL_DIR "!replace_result!\\IvoryDigital\\DentureModeller" 1
	cd %env_blend_dir%
	rem if no head file selected, then this is modeller part. else this is refiner part
	if "%HEAD_FILE%"=="" ( 
		echo start /wait /b blender.exe %selected_file% --python %logic% -- %selected_file% >%logs_file% 2>&1
		start /wait /b blender.exe %selected_file% --python %logic% -- %selected_file% >%logs_file% 2>&1
	 ) else ( 
		echo start /wait /b blender.exe %selected_file% --python %logic% -- %HEAD_FILE% %UPPER_JAW_FILE% %LOWER_JAW_FILE%
		start /wait /b blender.exe %selected_file% --python %logic% -- %HEAD_FILE% %UPPER_JAW_FILE% %LOWER_JAW_FILE%
		rem  >%logs_file% 2>&1
	 )
	rem UNCOMMENT NEXT LINE TO KEEP CONSOLE WINDOW OPEN FOR DEBUG
	exit
endlocal