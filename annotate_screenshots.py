#!/usr/bin/env python3
"""
Screenshot Annotation Script
Adds professional arrows, boxes, and labels to SuperLocalMemory V2 dashboard screenshots
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Annotation style constants
RED = "#FF0000"
ARROW_WIDTH = 3
BOX_WIDTH = 2
LABEL_BG = "#FFFFFF"
LABEL_TEXT = "#000000"
LABEL_FONT_SIZE = 14
LABEL_PADDING = 8
LABEL_CORNER_RADIUS = 6

def draw_arrow(draw, start, end, color=RED, width=ARROW_WIDTH):
    """Draw an arrow from start to end coordinates with arrow head"""
    # Draw the line
    draw.line([start, end], fill=color, width=width)

    # Calculate arrow head
    import math
    x1, y1 = start
    x2, y2 = end

    # Arrow head size
    head_length = 15
    head_width = 10

    # Calculate angle
    angle = math.atan2(y2 - y1, x2 - x1)

    # Arrow head points
    left_angle = angle + math.pi * 0.8
    right_angle = angle - math.pi * 0.8

    left_point = (
        x2 - head_length * math.cos(left_angle),
        y2 - head_length * math.sin(left_angle)
    )
    right_point = (
        x2 - head_length * math.cos(right_angle),
        y2 - head_length * math.sin(right_angle)
    )

    # Draw arrow head (filled triangle)
    draw.polygon([end, left_point, right_point], fill=color)

def draw_box(draw, top_left, bottom_right, color=RED, width=BOX_WIDTH):
    """Draw a rectangle box"""
    draw.rectangle([top_left, bottom_right], outline=color, width=width)

def draw_label(draw, position, text, font):
    """Draw a label with white background and black text"""
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate label box with padding
    x, y = position
    label_width = text_width + LABEL_PADDING * 2
    label_height = text_height + LABEL_PADDING * 2

    # Draw rounded rectangle background
    draw.rounded_rectangle(
        [(x, y), (x + label_width, y + label_height)],
        radius=LABEL_CORNER_RADIUS,
        fill=LABEL_BG,
        outline=RED,
        width=1
    )

    # Draw text
    text_x = x + LABEL_PADDING
    text_y = y + LABEL_PADDING - bbox[1]  # Adjust for baseline
    draw.text((text_x, text_y), text, fill=LABEL_TEXT, font=font)

def annotate_dashboard_overview(image_path, output_path):
    """Annotate dashboard-overview.png"""
    img = Image.open(image_path)
    # Convert to RGB if needed (fixes palette mode issues)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Arrow pointing to stats cards → "Real-time statistics"
    draw_arrow(draw, (100, 40), (170, 70))
    draw_label(draw, (20, 25), "Real-time statistics", font)

    # Box around Live Events tab → "NEW in v2.5"
    # Live Events tab is around position (553, 210)
    draw_box(draw, (505, 200), (585, 222))
    draw_label(draw, (590, 202), "NEW in v2.5", font)

    img.save(output_path, quality=95)
    print(f"✓ Annotated: {output_path}")

def annotate_dashboard_live_events(image_path, output_path):
    """Annotate dashboard-live-events.png"""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Arrow to event stream → "Real-time memory operations"
    draw_arrow(draw, (80, 280), (120, 260))
    draw_label(draw, (85, 285), "Real-time memory operations", font)

    # Box around event type badges → "Color-coded events"
    # Event type badge around (105, 263)
    draw_box(draw, (90, 258), (160, 270))
    draw_label(draw, (165, 254), "Color-coded events", font)

    img.save(output_path, quality=95)
    print(f"✓ Annotated: {output_path}")

def annotate_dashboard_agents(image_path, output_path):
    """Annotate dashboard-agents.png"""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Arrow to trust score → "Agent trust scoring"
    draw_arrow(draw, (490, 380), (522, 399))
    draw_label(draw, (410, 365), "Agent trust scoring", font)

    # Box around protocol badge → "MCP/A2A support"
    # MCP badge around (327, 400)
    draw_box(draw, (311, 393), (343, 409))
    draw_label(draw, (348, 390), "MCP/A2A support", font)

    img.save(output_path, quality=95)
    print(f"✓ Annotated: {output_path}")

def annotate_dashboard_graph(image_path, output_path):
    """Annotate dashboard-graph.png"""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Arrow to cluster → "Semantic clusters"
    # Blue cluster at top-left around (567, 350)
    draw_arrow(draw, (500, 320), (567, 350))
    draw_label(draw, (400, 305), "Semantic clusters", font)

    # Label for interactive graph
    draw_label(draw, (30, 320), "Interactive graph visualization", font)

    img.save(output_path, quality=95)
    print(f"✓ Annotated: {output_path}")

def annotate_dashboard_memories(image_path, output_path):
    """Annotate dashboard-memories.png"""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", LABEL_FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Arrow to search box → "Hybrid search"
    draw_arrow(draw, (200, 90), (250, 110))
    draw_label(draw, (20, 75), "Hybrid search (TF-IDF + FTS5 + Graph)", font)

    # Box around filter panel (Category dropdown)
    # Category dropdown around position (250, 110)
    draw_box(draw, (240, 105), (345, 118))
    draw_label(draw, (350, 102), "Advanced filters", font)

    img.save(output_path, quality=95)
    print(f"✓ Annotated: {output_path}")

def main():
    """Annotate all 5 dashboard screenshots"""
    base_dir = "/Users/v.pratap.bhardwaj/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/assets/screenshots/dashboard"

    screenshots = [
        ("dashboard-overview.png", annotate_dashboard_overview),
        ("dashboard-live-events.png", annotate_dashboard_live_events),
        ("dashboard-agents.png", annotate_dashboard_agents),
        ("dashboard-graph.png", annotate_dashboard_graph),
        ("dashboard-memories.png", annotate_dashboard_memories)
    ]

    print("Starting screenshot annotation...")
    print(f"Base directory: {base_dir}\n")

    for filename, annotate_func in screenshots:
        input_path = os.path.join(base_dir, filename)
        output_filename = filename.replace(".png", "-annotated.png")
        output_path = os.path.join(base_dir, output_filename)

        if not os.path.exists(input_path):
            print(f"✗ Not found: {input_path}")
            continue

        try:
            annotate_func(input_path, output_path)
        except Exception as e:
            print(f"✗ Error annotating {filename}: {e}")

    print("\n✓ All annotations complete!")
    print(f"\nAnnotated files saved with '-annotated' suffix in:")
    print(f"  {base_dir}/")

if __name__ == "__main__":
    main()
