#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Video Generator
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Generate silent video slideshows from screenshot sequences.
"""

import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
import shutil

# Base paths
SCRIPT_DIR = Path(__file__).parent
CLI_DIR = SCRIPT_DIR / "cli"
DASHBOARD_DIR = SCRIPT_DIR / "dashboard"
V25_DIR = SCRIPT_DIR / "v25"
OUTPUT_DIR = SCRIPT_DIR.parent / "videos"

# Video specs
WIDTH = 1920
HEIGHT = 1080
FPS = 30
FADE_DURATION = 0.5


def create_title_slide(text, output_path):
    """Create a title slide with centered text."""
    img = Image.new('RGB', (WIDTH, HEIGHT), color='#1a1a1a')
    draw = ImageDraw.Draw(img)

    # Try to use a system font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    # Draw title
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (WIDTH - text_width) // 2
    y = (HEIGHT - text_height) // 2 - 50

    # Draw shadow
    draw.text((x + 3, y + 3), text, font=font, fill='#000000')
    # Draw text
    draw.text((x, y), text, font=font, fill='#ffffff')

    # Draw subtitle
    subtitle = "SuperLocalMemory V2"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    sub_width = bbox[2] - bbox[0]
    sub_x = (WIDTH - sub_width) // 2
    sub_y = y + text_height + 30

    draw.text((sub_x + 2, sub_y + 2), subtitle, font=subtitle_font, fill='#000000')
    draw.text((sub_x, sub_y), subtitle, font=subtitle_font, fill='#666666')

    img.save(output_path)
    print(f"✓ Created title slide: {output_path.name}")


def add_text_overlay(image_path, text, output_path, position='bottom'):
    """Add text overlay to an existing image."""
    img = Image.open(image_path)

    # Resize if needed
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # Convert to RGBA for transparency support
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Create overlay layer
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
        except:
            font = ImageFont.load_default()

    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    padding = 40
    bar_height = text_height + padding * 2

    if position == 'bottom':
        y = HEIGHT - bar_height
    else:
        y = padding

    # Draw semi-transparent background bar
    draw.rectangle([(0, y), (WIDTH, y + bar_height)], fill=(0, 0, 0, 180))

    # Draw text
    x = (WIDTH - text_width) // 2
    text_y = y + padding

    # Shadow
    draw.text((x + 2, text_y + 2), text, font=font, fill='#000000')
    # Text
    draw.text((x, text_y), text, font=font, fill='#ffffff')

    # Composite overlay onto image
    img = Image.alpha_composite(img, overlay)

    # Convert back to RGB for video encoding
    img = img.convert('RGB')

    img.save(output_path)
    print(f"✓ Added overlay: {output_path.name}")


def create_video_from_slides(slide_files, output_path, slide_duration=2.5):
    """Create video from a sequence of slide images using ffmpeg."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create concat file for ffmpeg
        concat_file = temp_dir / "concat.txt"
        with open(concat_file, 'w') as f:
            for slide in slide_files:
                f.write(f"file '{slide}'\n")
                f.write(f"duration {slide_duration}\n")
            # Repeat last slide to ensure it displays
            f.write(f"file '{slide_files[-1]}'\n")

        # Generate video with ffmpeg
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-vf', f'fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={len(slide_files) * slide_duration - FADE_DURATION}:d={FADE_DURATION}',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-r', str(FPS),
            '-preset', 'medium',
            '-crf', '23',
            str(output_path)
        ]

        print(f"\n→ Generating video: {output_path.name}")
        subprocess.run(cmd, check=True, capture_output=True)

        # Get file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"✓ Video created: {output_path.name} ({size_mb:.1f} MB)")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def generate_installation_video():
    """Generate installation-walkthrough.mp4 (60 sec)."""
    print("\n" + "="*60)
    print("VIDEO 1: Installation Walkthrough")
    print("="*60)

    temp_dir = Path(tempfile.mkdtemp())
    slides = []

    try:
        # Slide 1: Title
        slide1 = temp_dir / "slide1.png"
        create_title_slide("Installing SuperLocalMemory V2", slide1)
        slides.append(slide1)

        # Slide 2: Clone repository
        slide2 = temp_dir / "slide2.png"
        add_text_overlay(
            CLI_DIR / "cli-help.png",
            "Step 1: Clone the repository",
            slide2
        )
        slides.append(slide2)

        # Slide 3: Run installer
        slide3 = temp_dir / "slide3.png"
        add_text_overlay(
            CLI_DIR / "cli-status.png",
            "Step 2: Run ./install.sh",
            slide3
        )
        slides.append(slide3)

        # Slide 4: Verify installation
        slide4 = temp_dir / "slide4.png"
        add_text_overlay(
            CLI_DIR / "cli-status.png",
            "Step 3: Verify with 'slm status'",
            slide4
        )
        slides.append(slide4)

        # Slide 5: First memory
        slide5 = temp_dir / "slide5.png"
        add_text_overlay(
            CLI_DIR / "cli-remember.png",
            "Step 4: Create your first memory",
            slide5
        )
        slides.append(slide5)

        # Slide 6: End
        slide6 = temp_dir / "slide6.png"
        create_title_slide("Installation Complete!", slide6)
        slides.append(slide6)

        # Create video (10 seconds per slide = 60 seconds total)
        output = OUTPUT_DIR / "installation-walkthrough.mp4"
        create_video_from_slides(slides, output, slide_duration=10)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def generate_quickstart_video():
    """Generate quick-start.mp4 (90 sec)."""
    print("\n" + "="*60)
    print("VIDEO 2: Quick Start Guide")
    print("="*60)

    temp_dir = Path(tempfile.mkdtemp())
    slides = []

    try:
        # Slide 1: Title
        slide1 = temp_dir / "slide1.png"
        create_title_slide("Quick Start Guide", slide1)
        slides.append(slide1)

        # Slide 2: Remember
        slide2 = temp_dir / "slide2.png"
        add_text_overlay(
            CLI_DIR / "cli-remember.png",
            "Create memories with 'slm remember'",
            slide2
        )
        slides.append(slide2)

        # Slide 3: Recall
        slide3 = temp_dir / "slide3.png"
        add_text_overlay(
            CLI_DIR / "cli-recall.png",
            "Search memories with 'slm recall'",
            slide3
        )
        slides.append(slide3)

        # Slide 4: Build graph
        slide4 = temp_dir / "slide4.png"
        add_text_overlay(
            CLI_DIR / "cli-build-graph.png",
            "Build knowledge graph with 'slm build-graph'",
            slide4
        )
        slides.append(slide4)

        # Slide 5: Dashboard overview
        slide5 = temp_dir / "slide5.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-overview.png",
            "Launch web dashboard with 'slm dashboard'",
            slide5
        )
        slides.append(slide5)

        # Slide 6: Graph visualization
        slide6 = temp_dir / "slide6.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-graph.png",
            "Explore your knowledge graph visually",
            slide6
        )
        slides.append(slide6)

        # Slide 7: End
        slide7 = temp_dir / "slide7.png"
        create_title_slide("Start Using SuperLocalMemory!", slide7)
        slides.append(slide7)

        # Create video (12.86 seconds per slide ≈ 90 seconds total)
        output = OUTPUT_DIR / "quick-start.mp4"
        create_video_from_slides(slides, output, slide_duration=12.86)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def generate_dashboard_video():
    """Generate dashboard-tour.mp4 (90 sec)."""
    print("\n" + "="*60)
    print("VIDEO 3: Dashboard Tour")
    print("="*60)

    temp_dir = Path(tempfile.mkdtemp())
    slides = []

    try:
        # Slide 1: Title
        slide1 = temp_dir / "slide1.png"
        create_title_slide("Dashboard Tour", slide1)
        slides.append(slide1)

        # Slide 2: Overview
        slide2 = temp_dir / "slide2.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-overview.png",
            "Overview: Stats, profiles, and quick actions",
            slide2
        )
        slides.append(slide2)

        # Slide 3: Live events (v2.5)
        slide3 = temp_dir / "slide3.png"
        add_text_overlay(
            V25_DIR / "v25-live-events-working.png",
            "Live Events: Real-time memory stream (v2.5)",
            slide3
        )
        slides.append(slide3)

        # Slide 4: Agents (v2.5)
        slide4 = temp_dir / "slide4.png"
        add_text_overlay(
            V25_DIR / "v25-agents-tab.png",
            "Agents: Track connected AI tools (v2.5)",
            slide4
        )
        slides.append(slide4)

        # Slide 5: Memories list
        slide5 = temp_dir / "slide5.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-memories.png",
            "Memories: Browse, search, and manage",
            slide5
        )
        slides.append(slide5)

        # Slide 6: Knowledge graph
        slide6 = temp_dir / "slide6.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-graph.png",
            "Graph: Interactive knowledge visualization",
            slide6
        )
        slides.append(slide6)

        # Slide 7: Clusters
        slide7 = temp_dir / "slide7.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-clusters.png",
            "Clusters: Discover related memories",
            slide7
        )
        slides.append(slide7)

        # Slide 8: Patterns
        slide8 = temp_dir / "slide8.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-patterns.png",
            "Patterns: AI learns your preferences",
            slide8
        )
        slides.append(slide8)

        # Slide 9: Dark mode
        slide9 = temp_dir / "slide9.png"
        add_text_overlay(
            DASHBOARD_DIR / "dashboard-overview-dark.png",
            "Dark Mode: Easy on the eyes",
            slide9
        )
        slides.append(slide9)

        # Slide 10: End
        slide10 = temp_dir / "slide10.png"
        create_title_slide("Explore Your Memories Visually!", slide10)
        slides.append(slide10)

        # Create video (9 seconds per slide = 90 seconds total)
        output = OUTPUT_DIR / "dashboard-tour.mp4"
        create_video_from_slides(slides, output, slide_duration=9)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Generate all three videos."""
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    print("\n" + "="*60)
    print("SuperLocalMemory V2 - Video Generator")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}")

    # Check ffmpeg
    if not shutil.which('ffmpeg'):
        print("\n✗ ERROR: ffmpeg not found. Please install ffmpeg first.")
        sys.exit(1)

    # Generate videos
    generate_installation_video()
    generate_quickstart_video()
    generate_dashboard_video()

    print("\n" + "="*60)
    print("✓ All videos generated successfully!")
    print("="*60)
    print(f"\nOutput files:")
    for video in OUTPUT_DIR.glob("*.mp4"):
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"  - {video.name} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    main()
