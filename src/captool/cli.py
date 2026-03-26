"""Click CLI entry point."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from .diff import diff_directories
from .manifest import load_manifest, validate_manifest
from .runner import CaptureReport, run_captures


@click.group()
def cli() -> None:
    """captool — automated screenshot capture for design analysis."""


# ── run ───────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--only", default=None, help="Comma-separated page IDs to capture.")
@click.option("--viewport", default=None, help="Capture only this viewport name.")
@click.option("--env-file", default=None, help="Path to .env file.")
def run(manifest_path: str, only: str | None, viewport: str | None, env_file: str | None) -> None:
    """Capture screenshots defined in MANIFEST_PATH."""
    manifest = load_manifest(manifest_path, env_file=env_file)
    only_list = [s.strip() for s in only.split(",")] if only else None

    report = asyncio.run(run_captures(manifest, only=only_list, viewport_filter=viewport))
    _print_summary(report)

    if report.failed:
        sys.exit(1)


# ── list ──────────────────────────────────────────────────────────────────────


@cli.command("list")
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--env-file", default=None, help="Path to .env file.")
def list_pages(manifest_path: str, env_file: str | None) -> None:
    """List all pages defined in MANIFEST_PATH."""
    manifest = load_manifest(manifest_path, env_file=env_file, strict_env=False)

    click.echo(f"{'ID':<30} {'Path':<30} {'Auth':<10} {'Viewports'}")
    click.echo("─" * 90)
    for page in manifest.pages:
        vps = ", ".join(page.viewports)
        auth = page.auth or "none"
        click.echo(f"{page.id:<30} {page.path:<30} {auth:<10} {vps}")
    click.echo(f"\n{len(manifest.pages)} page(s)")


# ── validate ──────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--env-file", default=None, help="Path to .env file.")
def validate(manifest_path: str, env_file: str | None) -> None:
    """Validate MANIFEST_PATH without running captures."""
    errors, warnings = validate_manifest(manifest_path, env_file=env_file)
    for w in warnings:
        click.secho(f"  ⚠ {w}", fg="yellow")
    if errors:
        click.secho("Validation failed:", fg="red", bold=True)
        for err in errors:
            click.echo(f"  • {err}")
        sys.exit(1)
    else:
        click.secho("Manifest is valid.", fg="green")


# ── diff ──────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("dir_a", type=click.Path(exists=True))
@click.argument("dir_b", type=click.Path(exists=True))
def diff(dir_a: str, dir_b: str) -> None:
    """Compare screenshots in DIR_A (before) and DIR_B (after)."""
    results = diff_directories(Path(dir_a), Path(dir_b))

    if not results:
        click.echo("No matching images found between the two directories.")
        return

    click.echo(f"{'File':<45} {'Diff %':>8}  Status")
    click.echo("─" * 65)
    flagged = 0
    for r in results:
        status = click.style("CHANGED", fg="yellow") if r.flagged else click.style("ok", fg="green")
        click.echo(f"{r.filename:<45} {r.diff_percent:>7.2f}%  {status}")
        if r.flagged:
            flagged += 1

    click.echo(f"\n{len(results)} image(s) compared, {flagged} with >1% change.")
    if results:
        report_path = Path(dir_b) / "diff" / "diff-report.html"
        click.echo(f"Report: {report_path}")

    if flagged:
        sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _print_summary(report: CaptureReport) -> None:
    click.echo()
    click.echo(f"{'Page ID':<35} {'Viewport':<12} {'Size':>10}  {'Path'}")
    click.echo("─" * 90)

    for r in report.results:
        if r.success:
            size = _fmt_size(r.file_size)
            path = str(r.path) if r.path else ""
            click.echo(f"{r.page_id:<35} {r.viewport:<12} {size:>10}  {path}")
        else:
            err = r.error or "unknown error"
            label = click.style("FAIL", fg="red", bold=True)
            click.echo(f"{r.page_id:<35} {r.viewport:<12} {label:>10}  {err}")

    passed = len(report.passed)
    failed = len(report.failed)
    click.echo(f"\n{passed} passed, {failed} failed, {passed + failed} total.")

    if report.output_dir:
        gallery = report.output_dir / "index.html"
        if gallery.exists():
            click.echo(f"Gallery: {gallery}")


def _fmt_size(nbytes: int) -> str:
    if nbytes < 1024:
        return f"{nbytes} B"
    return f"{nbytes / 1024:.1f} KB"
