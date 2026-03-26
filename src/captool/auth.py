"""Auth flow execution — runs login steps and preserves session in a browser context."""

from __future__ import annotations

from playwright.async_api import BrowserContext, Page

from .manifest import AuthFlow, AuthStep


async def run_auth_flow(context: BrowserContext, flow: AuthFlow, base_url: str) -> None:
    """Execute all steps in *flow* using a temporary page, then close it.

    Cookies and storage are retained in *context* for subsequent pages.
    """
    page = await context.new_page()
    try:
        for step in flow.steps:
            await _execute_step(page, step, base_url)
    finally:
        await page.close()


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
    else:
        raise ValueError(f"Unknown auth step action: {action}")
