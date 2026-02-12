Set WshShell = CreateObject("WScript.Shell")
' Run the clean start BAT in silent mode (0 = hidden)
WshShell.Run "cmd /c d:\Swarm-contol-in-sc2bot\JARVIS_CLEAN_START.bat", 0, False
Set WshShell = Nothing
