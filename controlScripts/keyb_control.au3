#include "AutoItConstants.au3"
#include "Misc.au3"

Func exitMessage($txt)
  ConsoleWrite($txt)
  Exit
EndFunc

Func closeApp($appTitle)
	WinClose($appTitle)
EndFunc

Func ConsoleWriteLine($txt)
	ConsoleWrite($txt & @LF)
EndFunc

Func pressKey($key)
  If $key=="CTRL" OR $key=="SHIFT" OR $key=="ALT" Then
    Send("{" & $key & "DOWN}")
 Else
   Send("{" & $key & " down}")
 EndIf
EndFunc

Func releaseKey($key)
  If $key=="CTRL" OR $key=="SHIFT" OR $key=="ALT" Then
    Send("{" & $key & "DOWN}")
    Send("{" & $key & "UP}")
 Else
   Send("{" & $key & " up}")
 EndIf
EndFunc

$parametersNum=$CmdLine[0]

If $parametersNum<1 Then
 exitMessage("local_keyb_control.au3 <key> <action>" & @LF & _
    "action=-press or -releae -click")
EndIf
 
$key=$CmdLine[1]
$action=$CmdLine[2]
$title=$CmdLine[3]

;set focus for target
$full_title=WinGetTitle($title)
WinActivate($full_title)
If $action=="-press" Then
  pressKey($key)
ElseIf $action=="-release" Then
  releaseKey($key)
ElseIf $action=="-click" Then
 pressKey($key)
 releaseKey($key)
ElseIf $action=="-close" Then
 closeApp($full_title)
EndIf
