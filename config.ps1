# Shared settings, dot-sourced by the *_service.ps1 scripts.

$DefaultPort      = 8002
$TaskName         = "WindowsSystemWatchdog"
$ProjectDir       = $PSScriptRoot
$MainScript       = "$ProjectDir\main.py"
$RequirementsFile = "$ProjectDir\requirements.txt"
$VenvPath         = "$ProjectDir\venv"
$PythonExe        = "$VenvPath\Scripts\python.exe"
$PythonwExe       = "$VenvPath\Scripts\pythonw.exe"  # No console window
$LogFile          = "$ProjectDir\watchdog.log"
