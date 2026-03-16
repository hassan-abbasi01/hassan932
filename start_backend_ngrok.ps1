# Start Backend and ngrok automatically
# This script starts the Flask backend and ngrok in separate background processes

$BackendPath = "C:\Users\GPU\Documents\FYP\backend"
$NgrokPort = 5001

Write-Host "Starting Flask Backend and ngrok..." -ForegroundColor Green

# Start Flask Backend in a new PowerShell window (minimized)
Write-Host "Starting Flask Backend from $BackendPath..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BackendPath'; python app.py" -WindowStyle Minimized

# Wait a few seconds for the backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start ngrok in a new PowerShell window (minimized)
Write-Host "Starting ngrok on port $NgrokPort..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http $NgrokPort" -WindowStyle Minimized

Write-Host "`nBoth services started successfully!" -ForegroundColor Green
Write-Host "- Backend running on http://localhost:$NgrokPort" -ForegroundColor White
Write-Host "- ngrok tunneling port $NgrokPort" -ForegroundColor White
Write-Host "`nTo view the ngrok URL, check the ngrok window or visit http://localhost:4040" -ForegroundColor Yellow
