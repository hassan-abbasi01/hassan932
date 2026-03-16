# Stop Backend and ngrok processes
Write-Host "Stopping Flask Backend and ngrok..." -ForegroundColor Yellow

# Stop all Python processes (Flask backend)
$PythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if ($PythonProcesses) {
    Write-Host "Stopping $($PythonProcesses.Count) Python process(es)..." -ForegroundColor Cyan
    $PythonProcesses | Stop-Process -Force
    Write-Host "Python processes stopped." -ForegroundColor Green
} else {
    Write-Host "No Python processes found." -ForegroundColor Gray
}

# Stop all ngrok processes
$NgrokProcesses = Get-Process -Name ngrok -ErrorAction SilentlyContinue
if ($NgrokProcesses) {
    Write-Host "Stopping $($NgrokProcesses.Count) ngrok process(es)..." -ForegroundColor Cyan
    $NgrokProcesses | Stop-Process -Force
    Write-Host "ngrok processes stopped." -ForegroundColor Green
} else {
    Write-Host "No ngrok processes found." -ForegroundColor Gray
}

Write-Host "`nAll services stopped." -ForegroundColor Green
