param(
    [int]$Port = 8002  # Default port if none provided
)

# Step 1: Set variables
$ProjectDir       = $PSScriptRoot
$MainScript       = "$ProjectDir\main.py"
$RequirementsFile = "$ProjectDir\requirements.txt"
$TaskName         = "WindowsSystemWatchdog"
$VenvPath         = "$ProjectDir\venv"
$PythonExe        = "$VenvPath\Scripts\python.exe"
$LogFile          = "$ProjectDir\watchdog.log"

# Step 2: Create Virtual Environment if not exists
if (!(Test-Path $VenvPath)) {
    Write-Output "Creating virtual environment..."
    & py -m venv $VenvPath
}

# Step 3: Install required dependencies
Write-Output "Installing dependencies..."
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r $RequirementsFile

# Step 4: Remove old scheduled task (if exists)
Write-Output "Removing old scheduled task (if exists)..."
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Step 5: Register new scheduled task (At logon + one-time trigger 30s from now)
Write-Output "Registering scheduled task..."
$Action    = New-ScheduledTaskAction -Execute $PythonExe -Argument "$MainScript --port $Port *> $LogFile 2>&1"
$LogonTrigger   = New-ScheduledTaskTrigger -AtLogOn
$OneTimeTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(30)
$Principal = New-ScheduledTaskPrincipal -UserId $env:UserName -LogonType Interactive -RunLevel Highest

# Multiple triggers: logon + one-time delayed
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $LogonTrigger,$OneTimeTrigger -Principal $Principal

# Step 6: Launch the app immediately in your interactive session (minimized window)
Write-Output "Starting FastAPI immediately in a minimized console window..."
Start-Process "$PythonExe" "$MainScript --port $Port" -WindowStyle Minimized

Write-Output "Setup completed! FastAPI should be running at http://127.0.0.1:$Port"
Write-Output "Task scheduled to run automatically at logon and 30 seconds from now."
Write-Output "Logs will be written to $LogFile"
