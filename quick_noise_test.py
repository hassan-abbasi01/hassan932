"""
Quick Test: Verify Noise Reduction is Actually Working
"""

import sys
import os
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

print("="  * 70)
print("QUICK NOISE REDUCTION VERIFICATION TEST")
print("=" * 70)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("\n[1] Importing AudioEnhancer...")
try:
    from services.video_service import AudioEnhancer
    print("✅ AudioEnhancer imported")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

print("\n[2] Creating test audio with obvious noise...")
# Create clean audio
sine = Sine(440).to_audio_segment(duration=3000, volume=-20.0)
sine = sine.set_frame_rate(16000).set_channels(1)

# Add LOUD white noise (50% of signal - very obvious)
samples = np.array(sine.get_array_of_samples(), dtype=np.float32)
noise = np.random.normal(0, samples.std() * 0.5, len(samples))  # 50% noise - LOUD
noisy_samples = (samples + noise).astype(np.int16)
noisy_audio = sine._spawn(noisy_samples.tobytes())

# Save noisy audio for comparison
noisy_path = "test_noisy.wav"
clean_path = "test_cleaned.wav"
noisy_audio.export(noisy_path, format="wav")
print(f"✅ Saved noisy test audio: {noisy_path}")
print(f"   Duration: {len(noisy_audio)}ms, Loudness: {noisy_audio.dBFS:.1f} dB")

print("\n[3] Applying noise reduction...")
enhancer = AudioEnhancer()

# Test with STRONG mode for obvious results
cleaned_audio = enhancer._reduce_noise(noisy_audio, 'strong')

# Save cleaned audio
cleaned_audio.export(clean_path, format="wav")
print(f"✅ Saved cleaned audio: {clean_path}")
print(f"   Duration: {len(cleaned_audio)}ms, Loudness: {cleaned_audio.dBFS:.1f} dB")

print("\n[4] Analyzing results...")
# Calculate improvement
noisy_samples_check = np.array(noisy_audio.get_array_of_samples(), dtype=np.float32)
cleaned_samples_check = np.array(cleaned_audio.get_array_of_samples(), dtype=np.float32)

# Calculate SNR improvement
original_power = np.mean(noisy_samples_check ** 2)
cleaned_power = np.mean(cleaned_samples_check ** 2)

# Estimate noise floor
noise_estimate = np.percentile(np.abs(noisy_samples_check), 20)
signal_estimate = np.percentile(np.abs(noisy_samples_check), 80)

print(f"\n📊 Audio Analysis:")
print(f"   Original Power: {original_power:.2e}")
print(f"   Cleaned Power: {cleaned_power:.2e}")
print(f"   Power Reduction: {((original_power - cleaned_power) / original_power * 100):.1f}%")
print(f"   Est. Noise Floor: {noise_estimate:.2f}")
print(f"   Est. Signal Peak: {signal_estimate:.2f}")

print("\n" + "=" * 70)
print("✅ TEST COMPLETE!")
print("=" * 70)
print(f"\n🎧 LISTEN TO COMPARE:")
print(f"   1. BEFORE: {os.path.abspath(noisy_path)}")
print(f"   2. AFTER:  {os.path.abspath(clean_path)}")
print(f"\n👂 Open both files and compare - cleaned version should have")
print(f"   less background hiss/noise!")
print("=" * 70)
