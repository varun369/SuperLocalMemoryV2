#!/usr/bin/env python3
"""
SuperLocalMemory V2 - GIF Optimizer
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Optimizes GIF file sizes using better compression and color reduction.
"""

from pathlib import Path
from PIL import Image, ImageSequence
import sys

BASE_DIR = Path(__file__).parent
GIFS_DIR = BASE_DIR / "assets" / "gifs"

def optimize_gif(input_path, target_mb, reduce_colors=True, reduce_frames=False):
    """Optimize a GIF file to meet target size."""
    print(f"Optimizing {input_path.name}...")

    original_size_mb = input_path.stat().st_size / (1024 * 1024)
    print(f"  Original size: {original_size_mb:.2f} MB")

    if original_size_mb <= target_mb:
        print(f"  ✓ Already under target ({target_mb} MB)")
        return

    # Load GIF
    img = Image.open(input_path)

    # Extract frames
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(img):
        frames.append(frame.copy().convert('RGB'))
        durations.append(frame.info.get('duration', 100))

    # Get original FPS
    fps = 1000 / durations[0] if durations else 12

    # Reduce frames if needed
    if reduce_frames:
        # Keep every other frame
        frames = frames[::2]
        durations = durations[::2]
        print(f"  - Reduced frames: {len(frames)} frames")

    # Reduce colors
    if reduce_colors:
        # Convert to P mode with adaptive palette
        optimized_frames = []
        for frame in frames:
            p_frame = frame.convert('P', palette=Image.Palette.ADAPTIVE, colors=128)
            optimized_frames.append(p_frame)
        frames = optimized_frames
        print(f"  - Reduced colors: 128 colors per frame")

    # Save with optimization
    frames[0].save(
        input_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations[0] if durations else int(1000/fps),
        loop=0,
        optimize=True,
        disposal=2  # Restore to background
    )

    new_size_mb = input_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ New size: {new_size_mb:.2f} MB ({new_size_mb - original_size_mb:+.2f} MB)")

    if new_size_mb > target_mb:
        print(f"  ⚠ Still over target by {new_size_mb - target_mb:.2f} MB")
    else:
        print(f"  ✓ Under target!")

def main():
    """Optimize all GIFs."""
    print("SuperLocalMemory V2 - GIF Optimizer")
    print("=" * 50)

    # Define targets
    targets = {
        "cli-demo.gif": 3.0,
        "dashboard-search.gif": 4.0,
        "graph-interaction.gif": 4.0,
        "event-stream.gif": 3.0,
        "dashboard-tabs.gif": 5.0,
    }

    for gif_name, target_mb in targets.items():
        gif_path = GIFS_DIR / gif_name
        if not gif_path.exists():
            print(f"⚠ {gif_name} not found, skipping...")
            continue

        # First pass: reduce colors
        optimize_gif(gif_path, target_mb, reduce_colors=True, reduce_frames=False)

        # Second pass: reduce frames if still too large
        if gif_path.stat().st_size / (1024 * 1024) > target_mb:
            print(f"  Second optimization pass (reducing frames)...")
            optimize_gif(gif_path, target_mb, reduce_colors=True, reduce_frames=True)

        print()

    print("=" * 50)
    print("Final sizes:")
    for gif in sorted(GIFS_DIR.glob("*.gif")):
        size_mb = gif.stat().st_size / (1024 * 1024)
        print(f"  - {gif.name}: {size_mb:.2f} MB")

if __name__ == "__main__":
    main()
