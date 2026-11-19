#Requires -RunAsAdministrator
# Installs the watchdog as a scheduled task that runs in your desktop session at logon.
# Usage: .\install_service.ps1 [-Port 8002]

param(
    [int]$Port = 0  # 0 means use $DefaultPort from config.ps1
)

. "$PSScriptRoot\config.ps1"
if ($Port -eq 0) { $Port = $DefaultPort }

# Step 1: Create Virtual Environment if not exists
if (!(Test-Path $PythonExe)) {
    # Use the py launcher if installed, otherwise fall back to python on PATH
    $PythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
    Write-Output "Creating virtual environment with '$PythonCmd'..."
    & $PythonCmd -m venv $VenvPath
}

if (!(Test-Path $PythonExe)) {
    Write-Error "Virtual environment creation failed: $PythonExe not found. Is Python installed?"
    exit 1
}

# Step 2: Install required dependencies
Write-Output "Installing dependencies..."
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r $RequirementsFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dependency installation failed. Fix the pip error above and re-run."
    exit 1
}

# Step 3: Stop and remove the old scheduled task (if exists)
Write-Output "Removing old scheduled task (if exists)..."
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Step 4: Register the scheduled task.
# pythonw.exe runs without a console window; main.py writes its own log file,
# since a task action is not a shell and cannot redirect output.
Write-Output "Registering scheduled task..."
$Action    = New-ScheduledTaskAction -Execute $PythonwExe `
                 -Argument "`"$MainScript`" --port $Port --log-file `"$LogFile`"" `
                 -WorkingDirectory $ProjectDir
$Trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
# Defaults would kill the task after 72 hours and refuse to run on battery.
$Settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
                 -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Principal $Principal -Settings $Settings | Out-Null

# Step 5: Start it now rather than waiting for the next logon
Write-Output "Starting the watchdog..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

try {
    Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 5 | Out-Null
    Write-Output "Setup completed! Watchdog is running at http://127.0.0.1:$Port"
} catch {
    Write-Warning "Task started but http://127.0.0.1:$Port/health is not responding yet. Check $LogFile or run .\status_service.ps1"
}
Write-Output "It will start automatically at logon. Logs: $LogFile"
