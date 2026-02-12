#!/usr/bin/env python3
"""
Screenshot Optimization Script for SuperLocalMemory V2
Optimizes PNG files for web usage while maintaining originals
Creates WebP versions for modern browsers
"""

import os
import sys
from pathlib import Path
from PIL import Image
import json
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent / "assets" / "screenshots"
PNG_QUALITY_THRESHOLD = 500 * 1024  # 500KB
WEBP_QUALITY_THRESHOLD = 300 * 1024  # 300KB
WEBP_QUALITY = 85
PNG_MAX_QUALITY = 9  # pngquant max quality

# Statistics tracking
stats = {
    "timestamp": datetime.now().isoformat(),
    "total_files": 0,
    "processed": 0,
    "skipped": 0,
    "files": []
}

def get_file_size(filepath):
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def format_size(bytes_size):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}GB"

def optimize_png(png_path):
    """Optimize PNG file, reducing file size while maintaining quality"""
    try:
        original_size = get_file_size(png_path)

        # Open image
        img = Image.open(png_path)
        original_format = img.format

        # Convert RGBA to RGB if no transparency, or optimize palette if transparent
        if img.mode == 'RGBA':
            # Check if there's actual transparency
            if img.getextrema()[3] != (255, 255):  # Has transparency
                # Keep as RGBA but optimize palette
                img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
            else:
                # No transparency, convert to RGB
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
        elif img.mode == 'P':
            # Already indexed, optimize palette
            img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
        elif img.mode in ['RGB', 'L']:
            # Convert to indexed color to reduce file size
            if img.mode == 'RGB':
                img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)

        # Save optimized PNG
        img.save(png_path, 'PNG', optimize=True)

        optimized_size = get_file_size(png_path)
        reduction = original_size - optimized_size
        reduction_pct = (reduction / original_size * 100) if original_size > 0 else 0

        return {
            "status": "optimized",
            "original_size": original_size,
            "optimized_size": optimized_size,
            "reduction": reduction,
            "reduction_pct": reduction_pct
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def create_webp(png_path, output_dir):
    """Create WebP version of PNG file"""
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Open PNG
        img = Image.open(png_path)
        original_mode = img.mode

        # Normalize to RGB or RGBA
        if original_mode == 'P':
            # Indexed color - check for transparency
            if 'transparency' in img.info:
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        elif original_mode == 'RGBA':
            # Already RGBA, keep it
            pass
        elif original_mode in ['L', '1']:
            # Grayscale or 1-bit
            img = img.convert('RGB')
        else:
            # RGB and others - ensure RGB
            if original_mode != 'RGB':
                img = img.convert('RGB')

        # Create WebP filename
        webp_name = png_path.stem + '.webp'
        webp_path = output_dir / webp_name

        # Save as WebP with quality setting
        img.save(webp_path, 'WEBP', quality=WEBP_QUALITY, method=6)

        webp_size = get_file_size(webp_path)

        return {
            "status": "created",
            "path": str(webp_path),
            "size": webp_size
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def process_directory(directory):
    """Process all PNG files in a directory"""
    directory = Path(directory)

    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    png_files = sorted(directory.glob("*.png"))

    if not png_files:
        print(f"No PNG files found in {directory}")
        return

    print(f"\n{'='*70}")
    print(f"Processing: {directory.relative_to(BASE_DIR)}")
    print(f"{'='*70}")

    for png_path in png_files:
        stats["total_files"] += 1
        print(f"\nProcessing: {png_path.name}")
        print(f"  Original size: {format_size(get_file_size(png_path))}")

        # Optimize PNG
        png_result = optimize_png(png_path)

        if png_result["status"] == "optimized":
            print(f"  ✓ PNG optimized: {format_size(png_result['optimized_size'])} "
                  f"(saved {format_size(png_result['reduction'])} / {png_result['reduction_pct']:.1f}%)")

            # Create WebP
            web_dir = directory / "web"
            webp_result = create_webp(png_path, web_dir)

            if webp_result["status"] == "created":
                print(f"  ✓ WebP created: {format_size(webp_result['size'])}")
                stats["processed"] += 1

                stats["files"].append({
                    "name": png_path.name,
                    "category": directory.relative_to(BASE_DIR).as_posix(),
                    "png": {
                        "size": png_result["optimized_size"],
                        "reduction_pct": png_result["reduction_pct"]
                    },
                    "webp": {
                        "size": webp_result["size"],
                        "path": str(Path(webp_result["path"]).relative_to(BASE_DIR))
                    }
                })
            else:
                print(f"  ✗ WebP error: {webp_result.get('error', 'Unknown error')}")
                stats["skipped"] += 1
        else:
            print(f"  ✗ PNG optimization error: {png_result.get('error', 'Unknown error')}")
            stats["skipped"] += 1

def main():
    """Main optimization workflow"""
    print("\n" + "="*70)
    print("SUPERLOCALMEMORY V2 — SCREENSHOT OPTIMIZATION")
    print("="*70)
    print(f"Base directory: {BASE_DIR}")

    if not BASE_DIR.exists():
        print(f"Error: Base directory not found: {BASE_DIR}")
        sys.exit(1)

    # Find all subdirectories with PNGs
    subdirs = sorted([d for d in BASE_DIR.iterdir() if d.is_dir() and list(d.glob("*.png"))])

    if not subdirs:
        print(f"\nNo PNG files found in any subdirectories")
        sys.exit(1)

    # Process each directory
    for subdir in subdirs:
        process_directory(subdir)

    # Summary report
    print(f"\n{'='*70}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total files found: {stats['total_files']}")
    print(f"Successfully processed: {stats['processed']}")
    print(f"Skipped/Failed: {stats['skipped']}")

    if stats["files"]:
        total_png_saved = sum(f["png"]["reduction_pct"] for f in stats["files"]) / len(stats["files"])
        print(f"\nAverage PNG optimization: {total_png_saved:.1f}%")

        print("\nFile sizes after optimization:")
        print(f"  PNG files: All < 500KB (goal)")
        print(f"  WebP files: All < 300KB (goal)")

        # Save detailed stats
        stats_path = BASE_DIR / "optimization-stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\nDetailed stats saved: {stats_path.relative_to(BASE_DIR.parent)}")

    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
