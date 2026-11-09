"""Screenshots of every page at 1280 and 1440 px from a running local app (`make run`), saved to docs/screenshots/."""

import argparse
from pathlib import Path

from loguru import logger
from playwright.sync_api import Page, sync_playwright

PAGES = {
    "overview": "",
    "trends": "trends",
    "flags": "flags",
    "table": "table",
    "methodology": "methodology",
}


def settle(page: Page) -> None:
    page.wait_for_selector('[data-testid="stSidebar"]')
    page.wait_for_function(
        "!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=30_000
    )
    page.wait_for_timeout(1500)


def choose(page: Page, label: str, option: str) -> None:
    box = (
        page.locator('[data-testid="stSelectbox"]')
        .filter(has_text=label)
        .locator("input")
    )
    box.click()
    box.fill(option)
    page.keyboard.press("Enter")
    settle(page)


def shoot(page: Page, path: Path, width: int) -> None:
    """Streamlit scrolls inside its main container, so grow the viewport to the content before the screenshot."""
    height = page.evaluate(
        "document.querySelector('[data-testid=\"stMain\"]').scrollHeight"
    )
    page.set_viewport_size({"width": width, "height": max(900, height)})
    page.wait_for_timeout(800)
    page.screenshot(path=path)
    page.set_viewport_size({"width": width, "height": 900})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8780")
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1280, 1440):
            page = browser.new_page(
                viewport={"width": width, "height": 900}, color_scheme="dark"
            )
            for name, path in PAGES.items():
                page.goto(f"{args.url}/{path}")
                settle(page)
                shoot(page, args.out / f"{name}-{width}.png", width)
            page.goto(args.url)
            settle(page)
            choose(page, "Week", "2011-09-19")
            shoot(page, args.out / f"overview-week-2011-09-19-{width}.png", width)
            choose(page, "Preset", "UK only")
            shoot(page, args.out / f"overview-uk-only-{width}.png", width)
            page.close()
        browser.close()
    logger.info(
        "saved {} screenshots to {}", len(list(args.out.glob("*.png"))), args.out
    )


if __name__ == "__main__":
    main()
