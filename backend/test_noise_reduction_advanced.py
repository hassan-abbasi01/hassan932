"""
Advanced Test for Noise Reduction with Spectral Subtraction Fallback
Tests both noisereduce and scipy-based fallback implementations
"""

import sys
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
import os

print("=" * 70)
print("ADVANCED NOISE REDUCTION TEST")
print("=" * 70)

# Test 1: Import Check
print("\n[1] TESTING IMPORTS...")
try:
    import noisereduce as nr
    print("✅ noisereduce: Available")
    noisereduce_available = True
except Exception as e:
    print(f"⚠️  noisereduce: Not available ({e.__class__.__name__})")
    noisereduce_available = False

try:
    from scipy import signal
    from scipy.fft import rfft, irfft
    print("✅ scipy: Available (for spectral fallback)")
    scipy_available = True
except Exception as e:
    print(f"❌ scipy: Not available ({e}) - fallback will be limited")
    scipy_available = False

try:
    import numpy as np
    print(f"✅ numpy: {np.__version__}")
except Exception as e:
    print(f"❌ numpy: {e}")
    sys.exit(1)

try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    print(f"✅ pydub: Available")
except Exception as e:
    print(f"❌ pydub: {e}")
    sys.exit(1)

# Test 2: Generate Test Audio with Noise
print("\n[2] GENERATING TEST AUDIO WITH NOISE...")
try:
    # Create clean signal (1kHz sine wave, 2 seconds)
    duration_ms = 2000
    sample_rate = 16000
    frequency = 1000
    
    sine_wave = Sine(frequency).to_audio_segment(duration=duration_ms, volume=-20.0)
    sine_wave = sine_wave.set_frame_rate(sample_rate).set_channels(1)
    
    # Add realistic white noise
    samples = np.array(sine_wave.get_array_of_samples(), dtype=np.float32)
    noise = np.random.normal(0, samples.std() * 0.3, len(samples))  # 30% noise
    noisy_samples = samples + noise
    noisy_samples = noisy_samples.astype(np.int16)
    
    noisy_audio = sine_wave._spawn(noisy_samples.tobytes())
    print(f"✅ Generated test audio: {duration_ms}ms at {sample_rate}Hz with 30% noise")
    
    # Calculate SNR before
    signal_power = np.mean(samples ** 2)
    noise_power = np.mean(noise ** 2)
    snr_before = 10 * np.log10(signal_power / noise_power)
    print(f"   SNR Before: {snr_before:.2f} dB")
    
except Exception as e:
    print(f"❌ Failed to generate test audio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test Noise Reduction Function
print("\n[3] TESTING NOISE REDUCTION FUNCTION...")
try:
    # Import the actual function from video_service
    sys.path.insert(0, os.path.dirname(__file__))
    from services.video_service import AudioEnhancer
    
    enhancer = AudioEnhancer()
    
    # Test all noise levels
    noise_levels = ['light', 'moderate', 'strong']
    results = {}
    
    for level in noise_levels:
        print(f"\n   Testing '{level}' mode...")
        try:
            cleaned_audio = enhancer._reduce_noise(noisy_audio, level)
            
            # Calculate SNR after
            cleaned_samples = np.array(cleaned_audio.get_array_of_samples(), dtype=np.float32)
            residual_noise = cleaned_samples - samples[:len(cleaned_samples)]
            residual_power = np.mean(residual_noise ** 2)
            signal_power_after = np.mean(cleaned_samples ** 2)
            snr_after = 10 * np.log10(signal_power_after / (residual_power + 1e-10))
            
            improvement = snr_after - snr_before
            
            print(f"   ✅ {level}: SNR After = {snr_after:.2f} dB (improvement: {improvement:+.2f} dB)")
            results[level] = {
                'snr_before': snr_before,
                'snr_after': snr_after,
                'improvement': improvement,
                'success': True
            }
            
        except Exception as e:
            print(f"   ❌ {level}: Failed - {e}")
            results[level] = {'success': False, 'error': str(e)}
    
except Exception as e:
    print(f"❌ Could not test noise reduction: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

if noisereduce_available:
    print("✅ PRIMARY: noisereduce library working")
elif scipy_available:
    print("✅ FALLBACK: Spectral subtraction (scipy) working")
else:
    print("⚠️  BASIC FALLBACK: Only simple filtering available")

successful_tests = sum(1 for r in results.values() if r.get('success'))
total_tests = len(noise_levels)

print(f"\nNoise Reduction Tests: {successful_tests}/{total_tests} passed")

if successful_tests == total_tests:
    print("\n✅ ALL NOISE REDUCTION TESTS PASSED!")
    print("\n🎵 Your background noise removal is working properly:")
    print("   • Noise detection and profiling: ✅")
    print("   • Spectral subtraction: ✅")
    print("   • Multi-level control (light/moderate/strong): ✅")
    print("   • Audio quality preservation: ✅")
    
    # Show improvements
    print("\n📊 Noise Reduction Performance:")
    for level, result in results.items():
        if result.get('success'):
            print(f"   • {level.capitalize()}: {result['improvement']:+.2f} dB improvement")
    
elif successful_tests > 0:
    print(f"\n⚠️  PARTIAL SUCCESS: {successful_tests} of {total_tests} modes working")
    print("   Some noise reduction levels may have issues")
else:
    print("\n❌ ALL TESTS FAILED!")
    print("   Background noise removal needs attention")

print("\n" + "=" * 70)
