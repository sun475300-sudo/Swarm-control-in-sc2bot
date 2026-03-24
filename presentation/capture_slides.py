"""Capture each slide from slides.html as a PNG image using Playwright."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

HTML_PATH = Path(__file__).parent / "slides.html"
OUTPUT_DIR = Path(__file__).parent
SLIDE_COUNT = 10

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=2
        )
        await page.goto(f"file:///{HTML_PATH.as_posix()}")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)

        for i in range(1, SLIDE_COUNT + 1):
            selector = f"#slide{i}"
            element = page.locator(selector)
            out_path = OUTPUT_DIR / f"slide_{i:02d}.png"
            await element.screenshot(path=str(out_path))
            print(f"Saved: {out_path.name}")

        await browser.close()
        print(f"\nDone! {SLIDE_COUNT} slides saved to {OUTPUT_DIR}")

asyncio.run(main())
