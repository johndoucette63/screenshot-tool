"""Auth flow execution — runs login steps and preserves session in a browser context."""

from __future__ import annotations

from playwright.async_api import BrowserContext, Page

from .manifest import AuthFlow, AuthStep


async def run_auth_flow(context: BrowserContext, flow: AuthFlow, base_url: str) -> Page:
    """Execute all steps in *flow* and return the authenticated page.

    The page is kept open so that in-memory auth tokens are preserved
    for subsequent navigations.
    """
    page = await context.new_page()
    for step in flow.steps:
        await _execute_step(page, step, base_url)
    return page


async def _execute_step(page: Page, step: AuthStep, base_url: str) -> None:
    action = step.action
    params = step.params

    if action == "goto":
        url = params if str(params).startswith("http") else f"{base_url}{params}"
        await page.goto(url)
    elif action == "fill":
        await page.fill(params["selector"], params["value"])
    elif action == "click":
        await page.click(str(params))
    elif action == "wait_for":
        await page.wait_for_selector(str(params))
    elif action == "wait_for_url":
        await page.wait_for_url(f"**{params}**", timeout=30000)
    else:
        raise ValueError(f"Unknown auth step action: {action}")
