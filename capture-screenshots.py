#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Dashboard Screenshot Capture
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Captures high-quality dashboard screenshots using Playwright.
"""

import asyncio
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright not installed. Installing now...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    print("✅ Playwright installed. Please run the script again.")
    sys.exit(0)

# Configuration
DASHBOARD_URL = "http://localhost:8765"
SCREENSHOT_DIR = Path(__file__).parent / "assets" / "screenshots" / "dashboard"
VIEWPORT_SIZE = {"width": 1920, "height": 1080}
SCREENSHOT_QUALITY = 100

# Screenshots to capture
SCREENSHOTS = [
    {
        "filename": "dashboard-overview.png",
        "description": "Main dashboard overview with stats",
        "tab": None,  # Default/stats view
        "wait_for": ".stats-grid",
        "additional_wait": 2000
    },
    {
        "filename": "dashboard-live-events.png",
        "description": "Live Events tab",
        "tab": "Live Events",
        "wait_for": "#live-events-section",
        "additional_wait": 2000
    },
    {
        "filename": "dashboard-agents.png",
        "description": "Agents tab",
        "tab": "Agents",
        "wait_for": "#agents-section",
        "additional_wait": 1000
    },
    {
        "filename": "dashboard-graph.png",
        "description": "Knowledge Graph visualization",
        "tab": "Knowledge Graph",
        "wait_for": "#graph-section",
        "additional_wait": 3000  # Graph rendering takes time
    },
    {
        "filename": "dashboard-memories.png",
        "description": "Memories list view",
        "tab": "Memories",
        "wait_for": "#memories-section",
        "additional_wait": 1500
    },
    {
        "filename": "dashboard-clusters.png",
        "description": "Clusters view",
        "tab": "Clusters",
        "wait_for": "#clusters-section",
        "additional_wait": 1000
    },
    {
        "filename": "dashboard-patterns.png",
        "description": "Learned patterns view",
        "tab": "Patterns",
        "wait_for": "#patterns-section",
        "additional_wait": 1000
    },
    {
        "filename": "dashboard-timeline.png",
        "description": "Timeline view",
        "tab": "Timeline",
        "wait_for": "#timeline-section",
        "additional_wait": 1500
    }
]

async def capture_screenshot(page, screenshot_config, dark_mode=False):
    """Capture a single screenshot."""
    filename = screenshot_config["filename"]
    if dark_mode:
        filename = filename.replace(".png", "-dark.png")

    description = screenshot_config["description"]
    if dark_mode:
        description += " (Dark Mode)"

    print(f"  📸 Capturing: {description}")

    try:
        # Navigate to dashboard if needed
        if page.url != DASHBOARD_URL:
            try:
                await page.goto(DASHBOARD_URL, wait_until="load", timeout=60000)
            except:
                await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)  # Let initial load complete

        # Toggle dark mode if needed
        if dark_mode:
            await page.evaluate("document.body.classList.add('dark-mode')")
            await asyncio.sleep(0.5)

        # Click tab if specified
        if screenshot_config["tab"]:
            try:
                # Try different possible selectors for tabs
                tab_selectors = [
                    f"button:has-text('{screenshot_config['tab']}')",
                    f"a:has-text('{screenshot_config['tab']}')",
                    f".tab:has-text('{screenshot_config['tab']}')",
                    f".nav-item:has-text('{screenshot_config['tab']}')"
                ]

                tab_clicked = False
                for selector in tab_selectors:
                    try:
                        await page.click(selector, timeout=2000)
                        tab_clicked = True
                        break
                    except:
                        continue

                if not tab_clicked:
                    print(f"    ⚠️  Could not find tab: {screenshot_config['tab']}")
                    return False

                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️  Error clicking tab: {e}")
                return False

        # Wait for specific element
        try:
            await page.wait_for_selector(screenshot_config["wait_for"], timeout=10000)
        except Exception as e:
            print(f"    ⚠️  Element not found: {screenshot_config['wait_for']}")
            # Continue anyway, might still get useful screenshot

        # Additional wait for rendering
        await asyncio.sleep(screenshot_config["additional_wait"] / 1000)

        # Capture screenshot
        output_path = SCREENSHOT_DIR / filename
        await page.screenshot(
            path=str(output_path),
            full_page=False,  # Viewport only for consistent size
            type="png"
        )

        print(f"    ✅ Saved: {filename}")
        return True

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

async def main():
    print("=" * 60)
    print("SuperLocalMemory V2 - Dashboard Screenshot Capture")
    print("=" * 60)
    print()

    # Ensure screenshot directory exists
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Screenshot directory: {SCREENSHOT_DIR}")
    print()

    # Check if dashboard is running
    print("Checking dashboard availability...")
    try:
        import urllib.request
        urllib.request.urlopen(DASHBOARD_URL, timeout=5)
        print(f"✅ Dashboard is running at {DASHBOARD_URL}")
    except Exception as e:
        print(f"❌ Dashboard not accessible at {DASHBOARD_URL}")
        print(f"Error: {e}")
        print("\nPlease start the dashboard first:")
        print("  python3 ~/.claude-memory/ui_server.py")
        sys.exit(1)

    print()
    print("Starting screenshot capture...")
    print()

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT_SIZE,
            device_scale_factor=2  # Higher DPI for sharper screenshots
        )
        page = await context.new_page()

        # Capture light mode screenshots
        print("📸 Capturing Light Mode Screenshots")
        print("-" * 60)
        light_success = 0
        for config in SCREENSHOTS:
            if await capture_screenshot(page, config, dark_mode=False):
                light_success += 1

        print()
        print(f"✅ Captured {light_success}/{len(SCREENSHOTS)} light mode screenshots")
        print()

        # Capture dark mode screenshots (key views only)
        print("📸 Capturing Dark Mode Screenshots")
        print("-" * 60)
        dark_mode_configs = [
            SCREENSHOTS[0],  # Overview
            SCREENSHOTS[1],  # Live Events
            SCREENSHOTS[4],  # Memories
        ]

        dark_success = 0
        for config in dark_mode_configs:
            if await capture_screenshot(page, config, dark_mode=True):
                dark_success += 1

        print()
        print(f"✅ Captured {dark_success}/{len(dark_mode_configs)} dark mode screenshots")

        # Capture filtered view
        print()
        print("📸 Capturing Special Views")
        print("-" * 60)

        # Navigate to Memories tab and apply filter
        try:
            await page.goto(DASHBOARD_URL, wait_until="load", timeout=60000)
            await asyncio.sleep(2)

            # Click Memories tab
            await page.click("button:has-text('Memories')")
            await asyncio.sleep(1)

            # Try to find and fill filter input
            filter_selectors = ["input[placeholder*='filter']", "input[placeholder*='search']", "#filter-input", ".filter-input"]
            for selector in filter_selectors:
                try:
                    await page.fill(selector, "api", timeout=2000)
                    await asyncio.sleep(1)
                    break
                except:
                    continue

            await page.screenshot(
                path=str(SCREENSHOT_DIR / "dashboard-filtered.png"),
                full_page=False,
                type="png"
            )
            print("  ✅ Saved: dashboard-filtered.png")

        except Exception as e:
            print(f"  ⚠️  Could not capture filtered view: {e}")

        await browser.close()

    print()
    print("=" * 60)
    print("✅ Screenshot capture complete!")
    print("=" * 60)
    print()
    print(f"📁 Screenshots saved to: {SCREENSHOT_DIR}")
    print()
    print("Files captured:")
    for screenshot_file in sorted(SCREENSHOT_DIR.glob("*.png")):
        size_kb = screenshot_file.stat().st_size / 1024
        print(f"  • {screenshot_file.name} ({size_kb:.1f} KB)")
    print()

if __name__ == "__main__":
    asyncio.run(main())
