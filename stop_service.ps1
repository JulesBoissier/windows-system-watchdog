#Requires -RunAsAdministrator
# Stops the watchdog and removes its scheduled task. Re-install with .\install_service.ps1
# Usage: .\stop_service.ps1 [-Port 8002]

param(
    [int]$Port = 0  # 0 means use $DefaultPort from config.ps1
)

. "$PSScriptRoot\config.ps1"
if ($Port -eq 0) { $Port = $DefaultPort }

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Output "Stopping scheduled task '$TaskName'..."
    Stop-ScheduledTask -TaskName $TaskName
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Scheduled task removed."
} else {
    Write-Output "Scheduled task '$TaskName' is not installed."
}

# Also catch copies started outside the task (e.g. by older install scripts or by hand)
$Listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($Conn in $Listeners) {
    $Proc = Get-Process -Id $Conn.OwningProcess -ErrorAction SilentlyContinue
    if ($Proc -and $Proc.ProcessName -like "python*") {
        Write-Output "Stopping leftover $($Proc.ProcessName) (PID $($Proc.Id)) on port $Port..."
        Stop-Process -Id $Proc.Id -Force
    }
}

Write-Output "Watchdog stopped."
