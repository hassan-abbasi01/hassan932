@echo off
echo Starting ngrok tunnel...
echo.
echo Make sure backend is running first!
echo.
ngrok http 5001
pause
