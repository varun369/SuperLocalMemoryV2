#!/usr/bin/env python3
"""
Generate terminal mockup screenshots using Playwright
Renders terminal-mockup.html with different scenarios
"""

import asyncio
import os
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed.")
    print("Install with: pip install playwright && playwright install chromium")
    exit(1)

# Scenarios to render
SCENARIOS = [
    ("status", "cli-status.png"),
    ("remember", "cli-remember.png"),
    ("recall", "cli-recall.png"),
    ("list", "cli-list.png"),
    ("build-graph", "cli-build-graph.png"),
    ("profile-switch", "cli-profile-switch.png"),
    ("help", "cli-help.png"),
]

async def generate_screenshots():
    """Generate all terminal mockup screenshots"""
    script_dir = Path(__file__).parent
    html_file = script_dir / "terminal-mockup.html"

    if not html_file.exists():
        print(f"ERROR: {html_file} not found")
        return

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 800})

        print("Generating terminal mockup screenshots...")

        for scenario_id, filename in SCENARIOS:
            url = f"file://{html_file.absolute()}?scenario={scenario_id}"

            # Navigate to scenario
            await page.goto(url)

            # Wait for content to render
            await page.wait_for_timeout(500)

            # Take screenshot
            output_path = script_dir / filename
            await page.screenshot(path=str(output_path), full_page=False)

            print(f"  ✓ {filename}")

        await browser.close()
        print(f"\n✅ Generated {len(SCENARIOS)} screenshots in {script_dir}")

if __name__ == "__main__":
    asyncio.run(generate_screenshots())
