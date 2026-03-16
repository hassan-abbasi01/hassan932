"""
GPU Detection and Configuration Module
Automatically detects GPU availability and configures video processing for optimal performance
"""
import torch
import cv2
import subprocess
import logging

logger = logging.getLogger(__name__)

class GPUManager:
    """Manages GPU detection and configuration for video processing"""
    
    def __init__(self):
        self.has_cuda = torch.cuda.is_available()
        self.gpu_info = self._detect_gpu()
        self.device = "cuda" if self.has_cuda else "cpu"
        self.opencv_cuda = self._check_opencv_cuda()
        
        # Log GPU status
        self._log_gpu_status()
        
    def _detect_gpu(self):
        """Detect GPU specifications"""
        if not self.has_cuda:
            return None
            
        try:
            gpu_info = {
                'name': torch.cuda.get_device_name(0),
                'count': torch.cuda.device_count(),
                'memory_total': torch.cuda.get_device_properties(0).total_memory / (1024**3),  # GB
                'cuda_version': torch.version.cuda,
                'compute_capability': torch.cuda.get_device_capability(0)
            }
            
            # Get current memory usage
            if hasattr(torch.cuda, 'memory_allocated'):
                gpu_info['memory_allocated'] = torch.cuda.memory_allocated(0) / (1024**3)
                gpu_info['memory_cached'] = torch.cuda.memory_reserved(0) / (1024**3)
            
            return gpu_info
        except Exception as e:
            logger.error(f"Error detecting GPU: {e}")
            return None
    
    def _check_opencv_cuda(self):
        """Check if OpenCV was built with CUDA support"""
        try:
            return cv2.cuda.getCudaEnabledDeviceCount() > 0
        except:
            return False
    
    def _log_gpu_status(self):
        """Log GPU configuration status"""
        logger.info("=" * 60)
        logger.info("GPU CONFIGURATION")
        logger.info("=" * 60)
        
        if self.has_cuda and self.gpu_info:
            logger.info(f"✅ GPU AVAILABLE: {self.gpu_info['name']}")
            logger.info(f"   GPU Count: {self.gpu_info['count']}")
            logger.info(f"   Total Memory: {self.gpu_info['memory_total']:.2f} GB")
            logger.info(f"   CUDA Version: {self.gpu_info['cuda_version']}")
            logger.info(f"   Compute Capability: {self.gpu_info['compute_capability']}")
            logger.info(f"   PyTorch Device: {self.device}")
            
            if self.opencv_cuda:
                logger.info("   OpenCV CUDA: ✅ Enabled")
            else:
                logger.info("   OpenCV CUDA: ❌ Not available (using CPU fallback)")
        else:
            logger.info("❌ No GPU detected - Using CPU")
            logger.info("   Video processing will be slower but functional")
        
        logger.info("=" * 60)
    
    def get_pytorch_device(self):
        """Get PyTorch device for AI models"""
        return self.device
    
    def get_ffmpeg_encoder(self, codec='h264'):
        """Get FFmpeg encoder based on GPU availability"""
        if not self.has_cuda:
            # CPU encoders
            encoders = {
                'h264': 'libx264',
                'h265': 'libx265',
                'vp9': 'libvpx-vp9'
            }
            logger.info(f"Using CPU encoder: {encoders.get(codec, 'libx264')}")
            return encoders.get(codec, 'libx264')
        
        # NVIDIA GPU encoders (NVENC)
        gpu_encoders = {
            'h264': 'h264_nvenc',
            'h265': 'hevc_nvenc',
            'vp9': 'vp9_nvenc'  # Fallback if not available
        }
        
        # Check if NVENC is available
        encoder = gpu_encoders.get(codec, 'h264_nvenc')
        if self._check_ffmpeg_encoder(encoder):
            logger.info(f"✅ Using GPU encoder: {encoder}")
            return encoder
        else:
            # Fallback to CPU
            fallback = 'libx264' if codec == 'h264' else 'libx265'
            logger.warning(f"GPU encoder {encoder} not available, using CPU: {fallback}")
            return fallback
    
    def get_ffmpeg_decoder(self):
        """Get FFmpeg decoder based on GPU availability"""
        if self.has_cuda and self._check_ffmpeg_encoder('h264_cuvid'):
            logger.info("✅ Using GPU decoder: h264_cuvid")
            return 'h264_cuvid'
        
        logger.info("Using CPU decoder")
        return None  # FFmpeg will use default CPU decoder
    
    def _check_ffmpeg_encoder(self, encoder_name):
        """Check if FFmpeg encoder is available"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return encoder_name in result.stdout
        except:
            return False
    
    def get_ffmpeg_hwaccel_args(self):
        """Get FFmpeg hardware acceleration arguments"""
        if not self.has_cuda:
            return []
        
        # NVIDIA CUDA acceleration
        return [
            '-hwaccel', 'cuda',
            '-hwaccel_output_format', 'cuda'
        ]
    
    def optimize_torch_settings(self):
        """Optimize PyTorch settings for GPU/CPU"""
        if self.has_cuda:
            # Enable cuDNN autotuner for better performance
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            logger.info("✅ PyTorch GPU optimizations enabled")
        else:
            # CPU optimizations
            torch.set_num_threads(4)  # Adjust based on CPU cores
            logger.info("✅ PyTorch CPU optimizations enabled")
    
    def clear_gpu_cache(self):
        """Clear GPU memory cache"""
        if self.has_cuda:
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
    
    def get_gpu_memory_info(self):
        """Get current GPU memory usage"""
        if not self.has_cuda:
            return None
        
        try:
            return {
                'allocated': torch.cuda.memory_allocated(0) / (1024**3),
                'cached': torch.cuda.memory_reserved(0) / (1024**3),
                'total': self.gpu_info['memory_total']
            }
        except:
            return None
    
    def should_use_gpu_for_task(self, task_type='general'):
        """Determine if GPU should be used for specific task"""
        if not self.has_cuda:
            return False
        
        # Check available memory
        mem_info = self.get_gpu_memory_info()
        if mem_info:
            available_memory = mem_info['total'] - mem_info['allocated']
            
            # Different tasks need different amounts of memory
            memory_requirements = {
                'ai_model': 2.0,  # GB
                'video_encode': 1.0,
                'image_process': 0.5,
                'general': 0.5
            }
            
            required = memory_requirements.get(task_type, 0.5)
            
            if available_memory < required:
                logger.warning(f"Insufficient GPU memory for {task_type} ({available_memory:.2f}GB < {required}GB)")
                return False
        
        return True

# Global GPU manager instance
gpu_manager = GPUManager()

# Optimize PyTorch settings on import
gpu_manager.optimize_torch_settings()

# Export commonly used functions
def get_device():
    """Get PyTorch device (cuda/cpu)"""
    return gpu_manager.get_pytorch_device()

def get_ffmpeg_encoder(codec='h264'):
    """Get optimal FFmpeg encoder"""
    return gpu_manager.get_ffmpeg_encoder(codec)

def get_ffmpeg_decoder():
    """Get optimal FFmpeg decoder"""
    return gpu_manager.get_ffmpeg_decoder()

def get_hwaccel_args():
    """Get FFmpeg hardware acceleration args"""
    return gpu_manager.get_ffmpeg_hwaccel_args()

def clear_cache():
    """Clear GPU cache"""
    gpu_manager.clear_gpu_cache()

def has_gpu():
    """Check if GPU is available"""
    return gpu_manager.has_cuda

def get_gpu_info():
    """Get GPU information"""
    return gpu_manager.gpu_info

def log_gpu_status():
    """Log current GPU status"""
    gpu_manager._log_gpu_status()
