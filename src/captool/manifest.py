"""YAML manifest parsing and validation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class Viewport:
    name: str
    width: int
    height: int
    device_scale_factor: float = 1.0


@dataclass
class AuthStep:
    action: str
    params: dict | str


@dataclass
class AuthFlow:
    name: str
    steps: list[AuthStep]


@dataclass
class BeforeAction:
    action: str
    params: dict | str | int


@dataclass
class Defaults:
    wait_until: str = "networkidle"
    wait_after: int = 500
    format: str = "png"


@dataclass
class PageConfig:
    id: str
    path: str
    auth: str | None = None
    viewports: list[str] = field(default_factory=lambda: ["desktop"])
    full_page: bool = False
    before_capture: list[BeforeAction] = field(default_factory=list)
    wait_until: str | None = None
    wait_after: int | None = None
    format: str | None = None


@dataclass
class Manifest:
    base_url: str
    output_dir: str
    timestamp_dirs: bool
    defaults: Defaults
    viewports: dict[str, Viewport]
    auth_flows: dict[str, AuthFlow]
    pages: list[PageConfig]


# ── Env-var resolution ────────────────────────────────────────────────────────


def _resolve_env_vars(value: str, *, strict: bool = True) -> str:
    def _replacer(match: re.Match) -> str:
        var = match.group(1)
        val = os.environ.get(var)
        if val is None:
            if strict:
                raise ValueError(f"Environment variable '{var}' is not set")
            return match.group(0)  # leave placeholder intact
        return val

    return ENV_VAR_PATTERN.sub(_replacer, value)


def _resolve_env_recursive(obj: object, *, strict: bool = True) -> object:
    if isinstance(obj, str):
        return _resolve_env_vars(obj, strict=strict)
    if isinstance(obj, dict):
        return {k: _resolve_env_recursive(v, strict=strict) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_recursive(item, strict=strict) for item in obj]
    return obj


# ── Step parsing ──────────────────────────────────────────────────────────────


def _parse_step(step_data: dict, label: str) -> tuple[str, dict | str | int]:
    if not isinstance(step_data, dict) or len(step_data) != 1:
        raise ValueError(f"{label} must be a single-action mapping, got: {step_data}")
    action = next(iter(step_data))
    return action, step_data[action]


# ── Public API ────────────────────────────────────────────────────────────────


def load_manifest(
    path: str | Path,
    env_file: str | None = None,
    *,
    strict_env: bool = True,
) -> Manifest:
    """Load, resolve env vars, and parse a manifest YAML file.

    When *strict_env* is False, unresolvable ``${VAR}`` references are left as-is
    instead of raising.  Useful for inspection commands (list, validate).
    """
    load_dotenv(env_file or ".env", override=False)

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    raw = _resolve_env_recursive(raw, strict=strict_env)
    return _parse_manifest(raw)


def validate_manifest(
    path: str | Path, env_file: str | None = None
) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)``. Empty errors list means structurally valid."""
    load_dotenv(env_file or ".env", override=False)

    errors: list[str] = []
    warnings: list[str] = []
    path = Path(path)

    if not path.exists():
        return [f"Manifest not found: {path}"], []

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        return ["Manifest must be a YAML mapping"], []

    if "base_url" not in raw:
        errors.append("Missing required key: base_url")
    if "pages" not in raw:
        errors.append("Missing required key: pages")

    # Collect unresolvable env vars as warnings, but continue validation
    try:
        raw = _resolve_env_recursive(raw, strict=True)
    except ValueError as exc:
        warnings.append(str(exc))
        raw = _resolve_env_recursive(raw, strict=False)

    # Viewports
    viewports = raw.get("viewports", {})
    for name, vp in viewports.items():
        if not isinstance(vp, dict):
            errors.append(f"Viewport '{name}' must be a mapping")
        elif "width" not in vp or "height" not in vp:
            errors.append(f"Viewport '{name}' must have width and height")

    # Auth flows
    auth_flows = raw.get("auth_flows", {})
    for name, flow in auth_flows.items():
        if not isinstance(flow, dict) or "steps" not in flow:
            errors.append(f"Auth flow '{name}' must have 'steps'")
            continue
        for i, step in enumerate(flow["steps"]):
            if not isinstance(step, dict) or len(step) != 1:
                errors.append(f"Auth flow '{name}' step {i}: must be a single-action mapping")

    # Pages
    pages = raw.get("pages", [])
    if not isinstance(pages, list):
        errors.append("'pages' must be a list")
    else:
        seen_ids: set[str] = set()
        for i, page in enumerate(pages):
            if not isinstance(page, dict):
                errors.append(f"Page {i} must be a mapping")
                continue
            pid = page.get("id")
            if not pid:
                errors.append(f"Page {i}: missing 'id'")
            elif pid in seen_ids:
                errors.append(f"Duplicate page id: '{pid}'")
            else:
                seen_ids.add(pid)

            if "path" not in page:
                errors.append(f"Page '{pid or i}': missing 'path'")

            for vp_name in page.get("viewports", []):
                if vp_name not in viewports:
                    errors.append(f"Page '{pid or i}': undefined viewport '{vp_name}'")

            auth = page.get("auth")
            if auth and auth != "none" and auth not in auth_flows:
                errors.append(f"Page '{pid or i}': undefined auth flow '{auth}'")

            for j, action in enumerate(page.get("before_capture", [])):
                if not isinstance(action, dict) or len(action) != 1:
                    errors.append(
                        f"Page '{pid or i}' before_capture[{j}]: "
                        "must be a single-action mapping"
                    )

    return errors, warnings


# ── Internal parsing ──────────────────────────────────────────────────────────


def _parse_manifest(raw: dict) -> Manifest:
    raw_defaults = raw.get("defaults", {})
    defaults = Defaults(
        wait_until=raw_defaults.get("wait_until", "networkidle"),
        wait_after=raw_defaults.get("wait_after", 500),
        format=raw_defaults.get("format", "png"),
    )

    viewports: dict[str, Viewport] = {}
    for name, vp in raw.get("viewports", {}).items():
        viewports[name] = Viewport(
            name=name,
            width=vp["width"],
            height=vp["height"],
            device_scale_factor=vp.get("device_scale_factor", 1.0),
        )

    auth_flows: dict[str, AuthFlow] = {}
    for name, flow in raw.get("auth_flows", {}).items():
        steps = []
        for i, s in enumerate(flow["steps"]):
            action, params = _parse_step(s, f"auth_flows.{name}.steps[{i}]")
            steps.append(AuthStep(action=action, params=params))
        auth_flows[name] = AuthFlow(name=name, steps=steps)

    pages: list[PageConfig] = []
    for p in raw.get("pages", []):
        before: list[BeforeAction] = []
        for i, a in enumerate(p.get("before_capture", [])):
            action, params = _parse_step(a, f"pages.{p['id']}.before_capture[{i}]")
            before.append(BeforeAction(action=action, params=params))

        pages.append(
            PageConfig(
                id=p["id"],
                path=p["path"],
                auth=p.get("auth"),
                viewports=p.get("viewports", ["desktop"]),
                full_page=p.get("full_page", False),
                before_capture=before,
                wait_until=p.get("wait_until"),
                wait_after=p.get("wait_after"),
                format=p.get("format"),
            )
        )

    return Manifest(
        base_url=raw["base_url"].rstrip("/"),
        output_dir=raw.get("output_dir", "./screenshots"),
        timestamp_dirs=raw.get("timestamp_dirs", False),
        defaults=defaults,
        viewports=viewports,
        auth_flows=auth_flows,
        pages=pages,
    )
