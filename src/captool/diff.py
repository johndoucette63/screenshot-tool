"""Screenshot diffing — pixel comparison and HTML report."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class DiffResult:
    filename: str
    diff_percent: float
    flagged: bool
    before_path: Path
    after_path: Path
    diff_path: Path | None = None


def diff_directories(
    dir_a: Path,
    dir_b: Path,
    output_dir: Path | None = None,
) -> list[DiffResult]:
    """Compare matching screenshots in *dir_a* (before) and *dir_b* (after).

    Returns per-image diff results and writes a ``diff-report.html``.
    """
    if output_dir is None:
        output_dir = dir_b / "diff"
    output_dir.mkdir(parents=True, exist_ok=True)

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
    files_a = {f.name: f for f in dir_a.iterdir() if f.suffix.lower() in IMAGE_EXTS}
    files_b = {f.name: f for f in dir_b.iterdir() if f.suffix.lower() in IMAGE_EXTS}

    common = sorted(set(files_a) & set(files_b))
    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))

    results: list[DiffResult] = []

    for name in common:
        path_a = files_a[name]
        path_b = files_b[name]

        img_a = Image.open(path_a).convert("RGB")
        img_b = Image.open(path_b).convert("RGB")

        # Resize if dimensions differ
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.LANCZOS)

        arr_a = np.array(img_a, dtype=np.int16)
        arr_b = np.array(img_b, dtype=np.int16)

        pixel_diff = np.abs(arr_a - arr_b)
        changed = np.any(pixel_diff > 0, axis=2)
        diff_pct = round(float(changed.sum()) / changed.size * 100, 2)

        # Build diff visualisation: changed pixels in magenta, unchanged dimmed
        vis = np.zeros_like(arr_a, dtype=np.uint8)
        vis[changed] = [255, 0, 100]
        vis[~changed] = (np.array(img_a, dtype=np.uint8)[~changed] * 0.3).astype(np.uint8)
        diff_img = Image.fromarray(vis)

        diff_path = output_dir / f"diff-{name}"
        diff_img.save(diff_path)

        results.append(
            DiffResult(
                filename=name,
                diff_percent=diff_pct,
                flagged=diff_pct > 1.0,
                before_path=path_a,
                after_path=path_b,
                diff_path=diff_path,
            )
        )

    _generate_diff_report(output_dir, results, only_a, only_b, dir_a, dir_b)
    return results


# ── Report generation ─────────────────────────────────────────────────────────


def _rel(from_dir: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, from_dir)


def _generate_diff_report(
    output_dir: Path,
    results: list[DiffResult],
    only_a: list[str],
    only_b: list[str],
    dir_a: Path,
    dir_b: Path,
) -> None:
    rows: list[str] = []
    for r in results:
        flag = "CHANGED" if r.flagged else "ok"
        flag_cls = "changed" if r.flagged else "ok"
        before_rel = _rel(output_dir, r.before_path)
        after_rel = _rel(output_dir, r.after_path)
        diff_rel = _rel(output_dir, r.diff_path) if r.diff_path else ""
        rows.append(
            f'<div class="row {flag_cls}">'
            f'<div class="info"><strong>{r.filename}</strong>'
            f'<span class="pct">{r.diff_percent}%</span>'
            f'<span class="flag {flag_cls}">{flag}</span></div>'
            f'<div class="images">'
            f'<div><img src="{before_rel}"><span>Before</span></div>'
            f'<div><img src="{after_rel}"><span>After</span></div>'
            f'<div><img src="{diff_rel}"><span>Diff</span></div>'
            f"</div></div>"
        )

    orphan_items: list[str] = []
    for name in only_a:
        orphan_items.append(f"<li><strong>Removed:</strong> {name}</li>")
    for name in only_b:
        orphan_items.append(f"<li><strong>Added:</strong> {name}</li>")
    orphans_section = ""
    if orphan_items:
        orphans_section = (
            '<div class="orphans"><h2>Unmatched files</h2><ul>'
            + "\n".join(orphan_items)
            + "</ul></div>"
        )

    html = _DIFF_TEMPLATE.replace("{{rows}}", "\n".join(rows)).replace(
        "{{orphans}}", orphans_section
    )
    (output_dir / "diff-report.html").write_text(html)


_DIFF_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visual Diff Report</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:#0f0f0f;color:#e0e0e0;padding:2rem}
h1{font-size:1.4rem;font-weight:600;margin-bottom:1.5rem}
h2{font-size:1.1rem;margin:2rem 0 .75rem}
.row{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;margin-bottom:1.5rem;overflow:hidden}
.row.changed{border-color:#e67e22}
.info{padding:.75rem 1rem;display:flex;align-items:center;gap:1rem;font-size:.85rem}
.pct{color:#888}
.flag{padding:.1rem .5rem;border-radius:4px;font-size:.75rem;font-weight:600}
.flag.changed{background:#e67e22;color:#fff}
.flag.ok{background:#27ae60;color:#fff}
.images{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px;background:#111}
.images div{text-align:center}
.images img{width:100%;display:block}
.images span{display:block;font-size:.75rem;color:#888;padding:.35rem 0}
.orphans ul{list-style:none;padding-left:0}
.orphans li{padding:.25rem 0;font-size:.85rem}
</style>
</head>
<body>
<h1>Visual Diff Report</h1>
{{rows}}
{{orphans}}
</body>
</html>
"""
