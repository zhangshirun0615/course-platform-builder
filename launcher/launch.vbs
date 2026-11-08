' Course Platform Bot launcher (opens GUI with no console window)
Option Explicit
Dim fso, shell, here, ps1
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = here & "\launcher_gui.ps1"
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1 & """", 0, False
