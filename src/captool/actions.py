"""Before-capture action execution."""

from __future__ import annotations

import asyncio

from playwright.async_api import Page

from .manifest import BeforeAction


async def run_before_actions(page: Page, actions: list[BeforeAction]) -> None:
    """Execute a sequence of before_capture actions on *page*."""
    for action in actions:
        await _execute(page, action)


async def _execute(page: Page, action: BeforeAction) -> None:
    name = action.action
    params = action.params

    if name == "click":
        await page.click(str(params))
    elif name == "fill":
        await page.fill(params["selector"], params["value"])
    elif name == "scroll_to":
        await page.locator(str(params)).scroll_into_view_if_needed()
    elif name == "wait_for":
        await page.wait_for_selector(str(params))
    elif name == "wait_for_url":
        await page.wait_for_url(f"**{params}**", timeout=30000)
    elif name == "wait_after":
        await asyncio.sleep(int(params) / 1000)
    elif name == "select_tab":
        await page.locator(f"text={params}").first.click()
    elif name == "click_and_navigate":
        async with page.expect_navigation(wait_until="networkidle"):
            await page.click(str(params))
    elif name == "select_option":
        await page.select_option(params["selector"], label=params["value"])
    elif name == "goto":
        await page.goto(str(params), wait_until="networkidle")
    else:
        raise ValueError(f"Unknown before_capture action: {name}")
