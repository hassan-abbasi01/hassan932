# Quick GPU Check Script
# Verifies if PyTorch can see your NVIDIA GPU

Write-Host "`n🔍 GPU DETECTION CHECK" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Check NVIDIA drivers
Write-Host "`n1. NVIDIA Driver Status:" -ForegroundColor Yellow
try {
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    Write-Host "   ✅ NVIDIA drivers working" -ForegroundColor Green
} catch {
    Write-Host "   ❌ NVIDIA drivers not found" -ForegroundColor Red
}

# Check PyTorch
Write-Host "`n2. PyTorch CUDA Status:" -ForegroundColor Yellow
python -c @"
import torch
print(f'   PyTorch Version: {torch.__version__}')
print(f'   CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'   CUDA Version: {torch.version.cuda}')
    print(f'   GPU Name: {torch.cuda.get_device_name(0)}')
    print(f'   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB')
    print('   ✅ GPU READY!')
else:
    print('   ❌ CUDA NOT AVAILABLE - Install PyTorch with CUDA')
    print('   Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118')
"@

Write-Host "`n" -ForegroundColor Gray
