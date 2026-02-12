#!/usr/bin/env python3
"""
SuperLocalMemory V2 - GIF Generator
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Generates 5 animated GIFs from existing screenshot assets.
"""

import os
from pathlib import Path
from PIL import Image, ImageSequence
import sys

# Base paths
BASE_DIR = Path(__file__).parent
SCREENSHOTS_DIR = BASE_DIR / "assets" / "screenshots"
OUTPUT_DIR = BASE_DIR / "assets" / "gifs"
ROOT_DIR = BASE_DIR

def resize_image(img, target_size):
    """Resize image to target size while maintaining aspect ratio."""
    target_w, target_h = target_size
    img_w, img_h = img.size

    # Calculate scaling factor
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    # Resize
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Create canvas and paste centered
    canvas = Image.new('RGB', target_size, (255, 255, 255))
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas.paste(img, (x, y))

    return canvas

def create_crossfade(img1, img2, steps=10):
    """Create crossfade transition between two images."""
    frames = []
    for i in range(steps):
        alpha = i / steps
        frame = Image.blend(img1.convert('RGB'), img2.convert('RGB'), alpha)
        frames.append(frame)
    return frames

def create_cli_demo():
    """Create CLI demo GIF."""
    print("Creating cli-demo.gif...")

    cli_dir = SCREENSHOTS_DIR / "cli"
    target_size = (800, 500)

    # Load images
    images = [
        cli_dir / "cli-remember.png",
        cli_dir / "cli-recall.png",
        cli_dir / "cli-list.png",
    ]

    frames = []
    loaded_images = []

    # Load and resize all images
    for img_path in images:
        if img_path.exists():
            img = Image.open(img_path)
            img = resize_image(img, target_size)
            loaded_images.append(img)

    if not loaded_images:
        print("  ⚠ No CLI images found, skipping...")
        return

    # Create sequence with crossfades
    for i, img in enumerate(loaded_images):
        # Hold current image for 2 seconds (24 frames at 12fps)
        frames.extend([img] * 24)

        # Crossfade to next (or loop to first)
        next_img = loaded_images[(i + 1) % len(loaded_images)]
        frames.extend(create_crossfade(img, next_img, 6))

    # Save GIF
    output_path = OUTPUT_DIR / "cli-demo.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000/12,  # 12 FPS
        loop=0,
        optimize=True
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.2f} MB)")

def create_dashboard_search():
    """Create dashboard search GIF."""
    print("Creating dashboard-search.gif...")

    dashboard_dir = SCREENSHOTS_DIR / "dashboard"
    target_size = (1200, 700)

    # Use memories view
    img_path = dashboard_dir / "dashboard-memories.png"

    if not img_path.exists():
        print("  ⚠ Dashboard memories image not found, skipping...")
        return

    img = Image.open(img_path)
    img = resize_image(img, target_size)

    frames = []

    # Create reveal effect (top to bottom)
    height = img.height
    steps = 30

    for i in range(steps):
        reveal_height = int(height * (i + 1) / steps)
        frame = Image.new('RGB', target_size, (255, 255, 255))
        cropped = img.crop((0, 0, img.width, reveal_height))
        frame.paste(cropped, (0, 0))
        frames.append(frame)

    # Hold full image
    frames.extend([img] * 30)

    # Fade out
    white = Image.new('RGB', target_size, (255, 255, 255))
    frames.extend(create_crossfade(img, white, 10))

    # Save GIF
    output_path = OUTPUT_DIR / "dashboard-search.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000/15,  # 15 FPS
        loop=0,
        optimize=True
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.2f} MB)")

def create_graph_interaction():
    """Create graph interaction GIF."""
    print("Creating graph-interaction.gif...")

    dashboard_dir = SCREENSHOTS_DIR / "dashboard"
    target_size = (1200, 700)

    img_path = dashboard_dir / "dashboard-graph.png"

    if not img_path.exists():
        print("  ⚠ Dashboard graph image not found, skipping...")
        return

    img = Image.open(img_path)
    img = resize_image(img, target_size)

    frames = []

    # Start with full view
    frames.extend([img] * 24)

    # Simulate zoom in (scale up center)
    zoom_steps = 20
    for i in range(zoom_steps):
        scale = 1.0 + (i / zoom_steps) * 0.5
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        zoomed = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center crop
        left = (new_w - target_size[0]) // 2
        top = (new_h - target_size[1]) // 2
        frame = zoomed.crop((left, top, left + target_size[0], top + target_size[1]))
        frames.append(frame)

    # Hold zoomed
    frames.extend([frames[-1]] * 20)

    # Zoom out
    for i in range(zoom_steps):
        scale = 1.5 - (i / zoom_steps) * 0.5
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        zoomed = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = (new_w - target_size[0]) // 2
        top = (new_h - target_size[1]) // 2
        frame = zoomed.crop((left, top, left + target_size[0], top + target_size[1]))
        frames.append(frame)

    # Hold final view
    frames.extend([img] * 24)

    # Save GIF
    output_path = OUTPUT_DIR / "graph-interaction.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000/12,  # 12 FPS
        loop=0,
        optimize=True
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.2f} MB)")

def create_event_stream():
    """Create event stream GIF."""
    print("Creating event-stream.gif...")

    target_size = (1200, 700)

    # Use v2.5 live events screenshot
    img_path = ROOT_DIR / "v25-live-events-working.png"

    if not img_path.exists():
        print("  ⚠ Live events image not found, skipping...")
        return

    img = Image.open(img_path)
    img = resize_image(img, target_size)

    frames = []

    # Create scrolling effect (bottom to top)
    height = img.height
    scroll_steps = 60
    scroll_distance = 200  # pixels to scroll

    for i in range(scroll_steps):
        offset = int(scroll_distance * (i / scroll_steps))
        frame = Image.new('RGB', target_size, (255, 255, 255))

        # Scroll by cropping and repositioning
        if offset < height:
            cropped = img.crop((0, offset, img.width, min(height, offset + target_size[1])))
            frame.paste(cropped, (0, 0))

        frames.append(frame)

    # Hold at end
    frames.extend([frames[-1]] * 20)

    # Scroll back
    for i in range(scroll_steps):
        offset = int(scroll_distance * ((scroll_steps - i) / scroll_steps))
        frame = Image.new('RGB', target_size, (255, 255, 255))

        if offset < height:
            cropped = img.crop((0, offset, img.width, min(height, offset + target_size[1])))
            frame.paste(cropped, (0, 0))

        frames.append(frame)

    # Hold at start
    frames.extend([img] * 20)

    # Save GIF
    output_path = OUTPUT_DIR / "event-stream.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000/15,  # 15 FPS
        loop=0,
        optimize=True
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.2f} MB)")

def create_dashboard_tabs():
    """Create dashboard tabs navigation GIF."""
    print("Creating dashboard-tabs.gif...")

    dashboard_dir = SCREENSHOTS_DIR / "dashboard"
    target_size = (1400, 900)

    # Load multiple dashboard views
    images = [
        dashboard_dir / "dashboard-overview-dark.png",
        dashboard_dir / "dashboard-live-events-dark.png",
        dashboard_dir / "dashboard-memories.png",
        dashboard_dir / "dashboard-graph.png",
        dashboard_dir / "dashboard-timeline.png",
    ]

    frames = []
    loaded_images = []

    # Load and resize all images
    for img_path in images:
        if img_path.exists():
            img = Image.open(img_path)
            img = resize_image(img, target_size)
            loaded_images.append(img)

    if not loaded_images:
        print("  ⚠ No dashboard images found, skipping...")
        return

    # Create sequence with crossfades
    for i, img in enumerate(loaded_images):
        # Hold current tab for 1.5 seconds (18 frames at 12fps)
        frames.extend([img] * 18)

        # Crossfade to next
        if i < len(loaded_images) - 1:
            next_img = loaded_images[i + 1]
            frames.extend(create_crossfade(img, next_img, 8))

    # Loop back to first
    frames.extend(create_crossfade(loaded_images[-1], loaded_images[0], 8))

    # Save GIF
    output_path = OUTPUT_DIR / "dashboard-tabs.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000/12,  # 12 FPS
        loop=0,
        optimize=True
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.2f} MB)")

def main():
    """Generate all GIFs."""
    print("SuperLocalMemory V2 - GIF Generator")
    print("=" * 50)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate each GIF
    try:
        create_cli_demo()
        create_dashboard_search()
        create_graph_interaction()
        create_event_stream()
        create_dashboard_tabs()

        print("\n" + "=" * 50)
        print("✓ All GIFs created successfully!")
        print(f"Output directory: {OUTPUT_DIR}")

        # List all created GIFs
        print("\nCreated files:")
        for gif in sorted(OUTPUT_DIR.glob("*.gif")):
            size_mb = gif.stat().st_size / (1024 * 1024)
            print(f"  - {gif.name} ({size_mb:.2f} MB)")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
