#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Event Stream GIF Optimizer
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Aggressive optimization for event-stream.gif
"""

from pathlib import Path
from PIL import Image, ImageSequence

BASE_DIR = Path(__file__).parent
gif_path = BASE_DIR / "assets" / "gifs" / "event-stream.gif"

print(f"Aggressive optimization of {gif_path.name}...")
original_size_mb = gif_path.stat().st_size / (1024 * 1024)
print(f"Original size: {original_size_mb:.2f} MB")

# Load GIF
img = Image.open(gif_path)

# Extract frames
frames = []
for frame in ImageSequence.Iterator(img):
    frames.append(frame.copy().convert('RGB'))

print(f"Original frames: {len(frames)}")

# Keep every 3rd frame (aggressive reduction)
frames = frames[::3]
print(f"Reduced frames: {len(frames)}")

# Reduce resolution slightly
target_size = (1100, 640)  # Down from 1200x700
optimized_frames = []
for frame in frames:
    # Resize
    resized = frame.resize(target_size, Image.Resampling.LANCZOS)
    # Reduce colors to 64 (very aggressive)
    p_frame = resized.convert('P', palette=Image.Palette.ADAPTIVE, colors=64)
    optimized_frames.append(p_frame)

print(f"Reduced colors: 64 per frame")
print(f"Reduced resolution: {target_size[0]}x{target_size[1]}")

# Save with maximum optimization
optimized_frames[0].save(
    gif_path,
    save_all=True,
    append_images=optimized_frames[1:],
    duration=200,  # Slower FPS to compensate for fewer frames
    loop=0,
    optimize=True,
    disposal=2
)

new_size_mb = gif_path.stat().st_size / (1024 * 1024)
print(f"New size: {new_size_mb:.2f} MB ({new_size_mb - original_size_mb:+.2f} MB)")

if new_size_mb <= 3.0:
    print("✓ Under 3 MB target!")
else:
    print(f"⚠ Still {new_size_mb - 3.0:.2f} MB over target")
