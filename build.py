#!/usr/bin/env python3
"""
Marginalia — build script.

Scans one or more markdown directories in a project, bundles every `.md`
file into a single self-contained HTML review page, optionally inlines the
Marked / highlight.js libraries so the page works offline, and opens it in
the default browser.

Usage:
    # Default: scan the project's `docs/` directory
    python build.py

    # Multiple directories
    python build.py --docs-dir docs --docs-dir specs --docs-dir wiki

    # Auto-discover all markdown across the project (skips node_modules,
    # .git, venv, target, dist, .claude, .cache, and similar)
    python build.py --auto

    # Force offline mode: fetch marked + highlight.js on first build,
    # cache into vendor/, inline into the HTML.
    python build.py --offline

    # Everything at once, custom output
    python build.py --auto --offline --output review.html --project-name MyProject

Requires Python 3.9+. Uses only stdlib (urllib for one-time vendor fetch).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------------- #
# Vendor CDNs (only used if --offline is requested and vendor/ is empty)
# ------------------------------------------------------------------------- #

VENDOR_SOURCES = {
    "marked.min.js": "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js",
    "highlight.min.js": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js",
    "hljs-atom-one-dark.min.css": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css",
    "hljs-atom-one-light.min.css": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css",
}

# Directories skipped during --auto discovery
AUTO_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "bower_components",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", "dist", "build", "out", ".next", ".nuxt", ".output",
    ".claude", ".idea", ".vscode",
    ".cache", ".turbo", ".parcel-cache",
    "vendor", "third_party", "third-party",
}


def default_vendor_dir() -> Path:
    """Where to cache the offline libs.

    When Marginalia runs as an installed Claude Code plugin, the plugin
    directory is a cache that gets replaced on update, so the vendor files
    go to the persistent plugin data dir instead. Standalone checkouts keep
    using `vendor/` next to this script.
    """
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data) / "vendor"
    return Path(__file__).parent / "vendor"


def fetch_vendor(vendor_dir: Path) -> dict[str, str]:
    """Fetch vendor files if not already cached. Returns filename -> content map.

    On network failure, returns whatever is already cached; missing entries
    will fall back to CDN <link>/<script> tags in the final HTML.
    """
    vendor_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for name, url in VENDOR_SOURCES.items():
        path = vendor_dir / name
        if not path.exists():
            print(f"vendor: fetching {name} …", file=sys.stderr)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "marginalia-build"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    path.write_bytes(resp.read())
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"vendor: FAILED to fetch {name}: {e}", file=sys.stderr)
                continue
        try:
            out[name] = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"vendor: could not read {name}: {e}", file=sys.stderr)
    return out


# ------------------------------------------------------------------------- #
# Doc scanning
# ------------------------------------------------------------------------- #

def scan_docs(docs_dirs: list[Path], project_root: Path) -> list[dict]:
    """Scan the given directories for .md files. Return list of dicts."""
    seen: set[Path] = set()
    files: list[dict] = []
    for docs_dir in docs_dirs:
        if not docs_dir.exists():
            print(f"warn: skipping missing dir: {docs_dir}", file=sys.stderr)
            continue
        for md_path in sorted(docs_dir.rglob("*.md")):
            # Skip auto-skip dirs
            if any(seg in AUTO_SKIP_DIRS for seg in md_path.parts):
                continue
            if md_path in seen:
                continue
            seen.add(md_path)
            try:
                content = md_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"warn: skipping non-UTF8 file: {md_path}", file=sys.stderr)
                continue

            try:
                rel_path = md_path.relative_to(project_root).as_posix()
            except ValueError:
                rel_path = str(md_path).replace("\\", "/")

            parent = md_path.parent
            try:
                rel_parent = parent.relative_to(project_root).as_posix()
            except ValueError:
                rel_parent = str(parent).replace("\\", "/")
            group = "" if rel_parent == "." else rel_parent

            files.append({
                "path": rel_path,
                "name": md_path.name,
                "stem": md_path.stem,
                "group": group,
                "content": content,
                "size": len(content),
                "lines": content.count("\n") + 1,
                "hash": hashlib.sha1(content.encode("utf-8")).hexdigest()[:10],
                "mtime": int(md_path.stat().st_mtime),
            })
    return files


def auto_discover(project_root: Path) -> list[Path]:
    """Return [project_root] if it contains any .md files at all (after
    skipping AUTO_SKIP_DIRS)."""
    for _dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in AUTO_SKIP_DIRS and not d.startswith(".")]
        if any(f.endswith(".md") for f in filenames):
            return [project_root]
    return []


def natural_sort_key(path: str) -> list:
    """Sort so `01-a.md` < `02-b.md` < `10-c.md`."""
    parts: list = []
    buf = ""
    for ch in path:
        if ch.isdigit():
            if buf and not buf[-1].isdigit():
                parts.append(buf)
                buf = ""
            buf += ch
        else:
            if buf and buf[-1].isdigit():
                parts.append(int(buf))
                buf = ""
            buf += ch
    if buf:
        parts.append(int(buf) if buf.isdigit() else buf)
    return parts


# ------------------------------------------------------------------------- #
# HTML build
# ------------------------------------------------------------------------- #

def build_head_assets(vendor: dict[str, str], offline: bool) -> str:
    """Return the <head> stylesheet + script tags. Inline vendored files
    when --offline is on and they're available; else fall back to CDN."""
    dark_css = vendor.get("hljs-atom-one-dark.min.css")
    light_css = vendor.get("hljs-atom-one-light.min.css")
    marked_js = vendor.get("marked.min.js")
    hljs_js = vendor.get("highlight.min.js")

    parts: list[str] = []
    if offline and dark_css:
        parts.append(f'<style id="hljs-theme-dark">{dark_css}</style>')
    else:
        parts.append('<link rel="stylesheet" id="hljs-theme-dark" '
                     'href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css" />')
    if offline and light_css:
        parts.append(f'<style id="hljs-theme-light" disabled>{light_css}</style>')
    else:
        parts.append('<link rel="stylesheet" id="hljs-theme-light" '
                     'href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css" disabled />')

    scripts: list[str] = []
    if offline and marked_js:
        scripts.append(f'<script>{marked_js}</script>')
    else:
        scripts.append('<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js" crossorigin="anonymous"></script>')
    if offline and hljs_js:
        scripts.append(f'<script>{hljs_js}</script>')
    else:
        scripts.append('<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js" crossorigin="anonymous"></script>')

    return "\n".join(parts) + "\n" + "\n".join(scripts)


def build(
    docs_dirs: list[Path],
    project_root: Path,
    output: Path,
    project_name: str,
    offline: bool,
    vendor_dir: Path,
) -> tuple[int, int, str]:
    template_path = Path(__file__).parent / "template.html"
    if not template_path.exists():
        print(f"error: template.html not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")
    vendor = fetch_vendor(vendor_dir) if offline else {}
    head_assets = build_head_assets(vendor, offline)

    docs = scan_docs(docs_dirs, project_root)
    docs.sort(key=lambda d: (d["group"], natural_sort_key(d["path"])))

    if not docs:
        print(f"warn: no .md files found in {[str(d) for d in docs_dirs]}", file=sys.stderr)

    session_id = hashlib.sha1(
        "|".join(sorted(str(d.absolute()) for d in docs_dirs)).encode()
    ).hexdigest()[:12]

    metadata = {
        "project": project_name,
        "project_root": str(project_root.absolute()),
        "docs_dirs": [str(d) for d in docs_dirs],
        "docs_dirs_absolute": [str(d.absolute()) for d in docs_dirs],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "file_count": len(docs),
        "total_lines": sum(d["lines"] for d in docs),
        "total_bytes": sum(d["size"] for d in docs),
        "offline": bool(offline and vendor),
        "app_name": "Marginalia",
        "app_short": "M",
    }

    docs_json = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")
    meta_json = json.dumps(metadata, ensure_ascii=False).replace("</", "<\\/")

    html = (
        template
        .replace("__HEAD_ASSETS__", head_assets)
        .replace("__DOCS_JSON__", docs_json)
        .replace("__META_JSON__", meta_json)
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    return len(docs), sum(d["lines"] for d in docs), session_id


def open_in_browser(path: Path) -> None:
    url = path.absolute().as_uri()
    try:
        webbrowser.open(url)
    except Exception as e:  # noqa: BLE001
        print(f"warn: could not open browser ({e}); open manually: {url}", file=sys.stderr)


# ------------------------------------------------------------------------- #
# CLI
# ------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(
        # Set by the npm wrapper so `--help` reads `marginalia`, not `build.py`.
        prog=os.environ.get("MARGINALIA_PROG") or None,
        description="Generate a self-contained Marginalia review page from project markdown docs.",
    )
    parser.add_argument(
        "--docs-dir",
        action="append",
        default=None,
        help="Directory to scan. May be given multiple times. Default: 'docs' (or project root if 'docs' missing).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-discover markdown across the whole project "
             "(skips .git, node_modules, .venv, target, dist, .claude, etc.).",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root for relative paths (default: cwd).",
    )
    parser.add_argument(
        "--output",
        default=".claude/scratchpad/marginalia.html",
        help="Output HTML path (default: .claude/scratchpad/marginalia.html).",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="Project name displayed in the header (default: cwd basename).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Inline marked + highlight.js into the HTML for offline use. "
             "First build fetches them; subsequent builds use the cache.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not auto-open in browser.",
    )
    parser.add_argument(
        "--vendor-dir",
        default=None,
        help="Where to cache vendored libs (default: $CLAUDE_PLUGIN_DATA/vendor when "
             "running as an installed plugin, else next to build.py).",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"error: project root not found: {project_root}", file=sys.stderr)
        return 2

    if args.auto:
        docs_dirs = auto_discover(project_root)
        if not docs_dirs:
            print("error: --auto found no markdown files", file=sys.stderr)
            return 2
        print(f"auto: scanning project root {project_root}", file=sys.stderr)
    elif args.docs_dir:
        docs_dirs = [Path(d).resolve() for d in args.docs_dir]
    else:
        default = project_root / "docs"
        docs_dirs = [default] if default.is_dir() else [project_root]

    output = Path(args.output).resolve()
    project_name = args.project_name or project_root.name
    vendor_dir = Path(args.vendor_dir).resolve() if args.vendor_dir else default_vendor_dir()

    count, lines, session_id = build(
        docs_dirs=docs_dirs,
        project_root=project_root,
        output=output,
        project_name=project_name,
        offline=args.offline,
        vendor_dir=vendor_dir,
    )

    print(f"wrote:     {output}")
    print(f"bundled:   {count} docs, {lines:,} lines")
    print(f"scanned:   {', '.join(str(d) for d in docs_dirs)}")
    print(f"session:   {session_id}")
    print(f"mode:      {'offline (inlined vendor)' if args.offline else 'online (CDN)'}")

    if not args.no_open:
        open_in_browser(output)
        print("opened in default browser")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
