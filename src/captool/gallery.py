"""HTML gallery generator for captured screenshots."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import CaptureResult


def generate_gallery(output_dir: Path, results: list[CaptureResult]) -> Path:
    """Write an index.html grid gallery into *output_dir* and return its path."""
    cards: list[str] = []
    for r in results:
        if not (r.path and r.path.exists()):
            continue
        rel = r.path.relative_to(output_dir)
        status = "error" if not r.success else "ok"
        size_kb = r.file_size / 1024
        badge = '<span class="badge error">ERROR</span>' if not r.success else ""
        cards.append(
            f'<div class="card {status}">'
            f'<img src="{rel}" alt="{r.page_id} — {r.viewport}" loading="lazy">'
            f'<div class="meta">'
            f"<strong>{r.page_id}</strong>"
            f'<span class="vp">{r.viewport}</span>'
            f'<span class="size">{size_kb:.1f} KB</span>'
            f"{badge}"
            f"</div></div>"
        )

    html = _TEMPLATE.replace("{{cards}}", "\n".join(cards))
    dest = output_dir / "index.html"
    dest.write_text(html)
    return dest


_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Screenshot Gallery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:#0f0f0f;color:#e0e0e0;padding:2rem}
h1{font-size:1.4rem;font-weight:600;margin-bottom:1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:1.5rem}
.card{background:#1a1a1a;border-radius:8px;overflow:hidden;border:1px solid #2a2a2a}
.card.error{border-color:#c0392b}
.card img{width:100%;display:block}
.meta{padding:.65rem 1rem;display:flex;align-items:center;gap:.75rem;font-size:.85rem}
.vp{color:#888}
.size{color:#666;margin-left:auto}
.badge{padding:.1rem .45rem;border-radius:4px;font-size:.75rem;font-weight:600}
.badge.error{background:#c0392b;color:#fff}
</style>
</head>
<body>
<h1>Screenshot Gallery</h1>
<div class="grid">
{{cards}}
</div>
</body>
</html>
"""
