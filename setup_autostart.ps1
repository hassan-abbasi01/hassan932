# Setup Auto-start for Backend and ngrok
# This script creates a scheduled task to run the services at startup

$ScriptPath = "C:\Users\GPU\Documents\FYP\start_backend_ngrok.ps1"
$TaskName = "FYP_Backend_Ngrok_Autostart"

Write-Host "Setting up auto-start task..." -ForegroundColor Green

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create action to run the PowerShell script
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""

# Create trigger for user logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Create principal to run with highest privileges
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

# Register the scheduled task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Description "Auto-start FYP Backend and ngrok"

Write-Host "`nAuto-start task created successfully!" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Cyan
Write-Host "`nThe backend and ngrok will start automatically when you log in." -ForegroundColor Yellow
Write-Host "`nTo disable auto-start, run:" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Gray
