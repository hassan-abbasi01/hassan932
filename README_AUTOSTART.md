# Auto-Start Backend & ngrok Setup

This folder contains scripts to automatically start your Flask backend and ngrok on your GPU PC.

## Files Created

1. **start_backend_ngrok.ps1** - Main script that starts both services
2. **start_backend_ngrok.bat** - Batch file to run the PowerShell script (double-click friendly)
3. **setup_autostart.ps1** - Sets up automatic startup on Windows login
4. **stop_services.ps1** - Stops all running backend and ngrok processes

## Quick Start

### Option 1: Manual Start (Recommended for Testing)
1. Double-click `start_backend_ngrok.bat`
2. OR run in PowerShell: `.\start_backend_ngrok.ps1`

This will open two minimized windows:
- One for the Flask backend
- One for ngrok

### Option 2: Automatic Start on Login
1. Run PowerShell **as Administrator**
2. Navigate to this folder: `cd C:\Users\GPU\Documents\FYP`
3. Run: `.\setup_autostart.ps1`
4. The services will now start automatically when you log in to Windows

## How to Stop Services

Run in PowerShell:
```powershell
.\stop_services.ps1
```

Or manually close the PowerShell windows running the services.

## How to View ngrok URL

After starting, you can view your ngrok public URL by:
1. Opening the ngrok window (it will be minimized in taskbar)
2. OR visiting http://localhost:4040 in your browser (ngrok web interface)

## Configuration

Edit `start_backend_ngrok.ps1` to change:
- `$BackendPath` - Path to your backend folder
- `$NgrokPort` - Port number for ngrok (default: 5001)

## Disable Auto-Start

To remove the auto-start task, run in PowerShell:
```powershell
Unregister-ScheduledTask -TaskName 'FYP_Backend_Ngrok_Autostart' -Confirm:$false
```

## Troubleshooting

**Issue:** Script won't run (execution policy error)
**Solution:** Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Issue:** Backend doesn't start
**Solution:** 
- Check that Python is installed and in PATH
- Ensure `app.py` exists at `C:\Users\GPU\Documents\FYP\backend\app.py`
- Check the backend window for error messages

**Issue:** ngrok doesn't start
**Solution:**
- Ensure ngrok is installed and in PATH
- Run `ngrok --version` to verify installation
- Check the ngrok window for error messages
