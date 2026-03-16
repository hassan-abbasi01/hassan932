# GPU Setup Script - Install PyTorch with CUDA Support
# Run this in your backend folder

Write-Host ""
Write-Host "🔧 INSTALLING PYTORCH WITH CUDA SUPPORT" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Gray

# Check NVIDIA GPU
Write-Host ""
Write-Host "1️⃣ Checking NVIDIA GPU..." -ForegroundColor Yellow
try {
    $gpu = nvidia-smi --query-gpu=name,driver_version,cuda_version --format=csv,noheader 2>$null
    if ($gpu) {
        Write-Host "✅ NVIDIA GPU Found: $gpu" -ForegroundColor Green
    } else {
        Write-Host "❌ NVIDIA GPU not detected" -ForegroundColor Red
        Write-Host "   Make sure NVIDIA drivers are installed" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ nvidia-smi not found - Install NVIDIA drivers first" -ForegroundColor Red
    exit 1
}

# Uninstall CPU-only PyTorch
Write-Host ""
Write-Host "2️⃣ Removing CPU-only PyTorch..." -ForegroundColor Yellow
pip uninstall -y torch torchvision torchaudio

# Install PyTorch with CUDA 11.8 (most compatible)
Write-Host ""
Write-Host "3️⃣ Installing PyTorch with CUDA 11.8..." -ForegroundColor Yellow
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
Write-Host ""
Write-Host "4️⃣ Verifying CUDA installation..." -ForegroundColor Yellow

# Create temp verification script
$verifyScript = @"
import torch
print('PyTorch version:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA version:', torch.version.cuda)
    print('GPU Name:', torch.cuda.get_device_name(0))
else:
    print('CUDA version: N/A')
    print('GPU Name: N/A')
"@

$verifyScript | Out-File -FilePath "temp_verify.py" -Encoding utf8
python temp_verify.py
Remove-Item "temp_verify.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ GPU SETUP COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "Restart your backend server to use GPU acceleration!" -ForegroundColor Cyan
