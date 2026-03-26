"""Capture orchestration — launches browser, runs auth, takes screenshots."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

from .actions import run_before_actions
from .auth import run_auth_flow
from .gallery import generate_gallery
from .manifest import Manifest, PageConfig, Viewport


@dataclass
class CaptureResult:
    page_id: str
    viewport: str
    path: Path | None = None
    file_size: int = 0
    success: bool = True
    error: str | None = None


@dataclass
class CaptureReport:
    results: list[CaptureResult] = field(default_factory=list)
    output_dir: Path | None = None

    @property
    def failed(self) -> list[CaptureResult]:
        return [r for r in self.results if not r.success]

    @property
    def passed(self) -> list[CaptureResult]:
        return [r for r in self.results if r.success]


# ── Public API ────────────────────────────────────────────────────────────────


async def run_captures(
    manifest: Manifest,
    only: list[str] | None = None,
    viewport_filter: str | None = None,
) -> CaptureReport:
    """Run all screenshot captures defined in *manifest*."""
    report = CaptureReport()

    # Resolve output directory
    output_dir = Path(manifest.output_dir)
    if manifest.timestamp_dirs:
        output_dir = output_dir / datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    report.output_dir = output_dir

    # Filter pages
    pages = manifest.pages
    if only:
        pages = [p for p in pages if p.id in only]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            # Auth page cache: auth_name → authenticated Page (kept alive
            # so in-memory tokens survive across navigations).
            auth_pages: dict[str, Page] = {}
            contexts: list[BrowserContext] = []

            for page_cfg in pages:
                vp_names = page_cfg.viewports
                if viewport_filter:
                    vp_names = [v for v in vp_names if v == viewport_filter]
                elif manifest.enabled_viewports:
                    vp_names = [v for v in vp_names if v in manifest.enabled_viewports]

                for vp_name in vp_names:
                    vp = manifest.viewports.get(vp_name)
                    if vp is None:
                        report.results.append(
                            CaptureResult(
                                page_id=page_cfg.id,
                                viewport=vp_name,
                                success=False,
                                error=f"Undefined viewport: {vp_name}",
                            )
                        )
                        continue

                    auth_name = page_cfg.auth if page_cfg.auth != "none" else None

                    # Authenticate on first use of each auth flow
                    if auth_name and auth_name not in auth_pages:
                        ctx = await browser.new_context(
                            device_scale_factor=vp.device_scale_factor,
                        )
                        contexts.append(ctx)
                        if auth_name in manifest.auth_flows:
                            try:
                                auth_page = await run_auth_flow(
                                    ctx, manifest.auth_flows[auth_name], manifest.base_url
                                )
                                auth_pages[auth_name] = auth_page
                            except Exception as exc:
                                await ctx.close()
                                report.results.append(
                                    CaptureResult(
                                        page_id=page_cfg.id,
                                        viewport=vp_name,
                                        success=False,
                                        error=f"Auth flow '{auth_name}' failed: {exc}",
                                    )
                                )
                                continue

                    # For unauthenticated pages, create a temporary page
                    page_to_use = auth_pages.get(auth_name)
                    temp_page = None
                    if page_to_use is None:
                        ctx = await browser.new_context(
                            device_scale_factor=vp.device_scale_factor,
                        )
                        contexts.append(ctx)
                        temp_page = await ctx.new_page()
                        page_to_use = temp_page

                    result = await _capture_page(
                        page_to_use, page_cfg, vp, manifest, output_dir
                    )
                    if temp_page:
                        await temp_page.close()
                    report.results.append(result)

            for ctx in contexts:
                await ctx.close()
        finally:
            await browser.close()

    # Generate gallery
    if report.results:
        generate_gallery(output_dir, report.results)

    return report


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _capture_page(
    auth_page: Page | None,
    page_cfg: PageConfig,
    viewport: Viewport,
    manifest: Manifest,
    output_dir: Path,
) -> CaptureResult:
    wait_until = page_cfg.wait_until or manifest.defaults.wait_until
    wait_after = (
        page_cfg.wait_after if page_cfg.wait_after is not None else manifest.defaults.wait_after
    )
    fmt = page_cfg.format or manifest.defaults.format

    filename = f"{page_cfg.id}-{viewport.name}.{fmt}"
    filepath = output_dir / filename

    page = auth_page

    try:
        await page.set_viewport_size({"width": viewport.width, "height": viewport.height})
        url = f"{manifest.base_url}{page_cfg.path}"

        # Navigate
        try:
            await page.goto(url, wait_until=wait_until, timeout=30_000)
        except Exception as exc:
            return await _error_capture(page_cfg, viewport, fmt, output_dir, page, exc)

        # Post-load pause
        if wait_after and wait_after > 0:
            await asyncio.sleep(wait_after / 1000)

        # Before-capture actions
        if page_cfg.before_capture:
            try:
                await run_before_actions(page, page_cfg.before_capture)
            except Exception as exc:
                return await _error_capture(page_cfg, viewport, fmt, output_dir, page, exc)

        # Screenshot
        await page.screenshot(path=str(filepath), full_page=page_cfg.full_page)

        return CaptureResult(
            page_id=page_cfg.id,
            viewport=viewport.name,
            path=filepath,
            file_size=filepath.stat().st_size,
        )
    except Exception as exc:
        return CaptureResult(
            page_id=page_cfg.id,
            viewport=viewport.name,
            success=False,
            error=str(exc),
        )


async def _error_capture(
    page_cfg: PageConfig,
    viewport: Viewport,
    fmt: str,
    output_dir: Path,
    page,
    exc: Exception,
) -> CaptureResult:
    """Attempt a partial screenshot of whatever rendered, then return a failure result."""
    error_path = output_dir / f"{page_cfg.id}-{viewport.name}-ERROR.{fmt}"
    try:
        await page.screenshot(path=str(error_path), full_page=page_cfg.full_page)
    except Exception:
        pass
    return CaptureResult(
        page_id=page_cfg.id,
        viewport=viewport.name,
        path=error_path if error_path.exists() else None,
        file_size=error_path.stat().st_size if error_path.exists() else 0,
        success=False,
        error=str(exc),
    )
