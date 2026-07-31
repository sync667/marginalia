# marginalia

[![ci](https://github.com/sync667/marginalia/actions/workflows/ci.yml/badge.svg)](https://github.com/sync667/marginalia/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> _mar·gi·na·lia_ · marginal notes; annotations written in the margins of a manuscript.

A Claude Code skill that turns any project's markdown documentation into a **local, self-contained web review tool**. Read all your docs in one place, highlight passages, add inline comments, edit content in-place, then hand the whole batch back to Claude to act on.

**Install:** `git clone https://github.com/sync667/marginalia .claude/skills/marginalia`, then invoke `/marginalia` in Claude Code.
See [`docs/PUBLISHING.md`](docs/PUBLISHING.md) for how this repo was set up and how to fork / republish.

Built for reviewing large multi-document sets — design packages, ADRs, RFCs, spec batches, wiki folders — where you need to browse dozens of files, add many small notes across them, and pass the notes to an AI or teammate for follow-up.

## What it does

- **Bundles** every `.md` file in one or many directories (or auto-discovers across the project) into a single self-contained HTML page.
- **Opens** it in your default browser — no server, no dependencies for the reader beyond a modern browser.
- Clean 3-column layout: file tree · rendered markdown · comment thread.
- Select any text → **💬 Add comment** popover → modal → highlight persists.
- Comments live in `localStorage`, keyed per-project.
- **Export** as JSON (structured for Claude) or Markdown (for humans).
- **Live mode** — connect a docs folder via the File System Access API, page reads files directly from disk, `↻ Refresh` shows current content.
- **Save to project** — the export writes directly to a chosen folder (typically `.claude/scratchpad/`) so Claude can read it without a paste.
- **First-run help modal** built in — new users get onboarded automatically.
- **Cross-doc navigation** — clicking `[text](other-doc.md)` links opens that doc in-place.
- **Search** across every filename and content.
- **Dark / light theme**, syntax highlighting, keyboard shortcuts.
- Not a hosted service. Everything is local — browser + your file system.

## How to use it

Inside Claude Code, invoke:

```
/marginalia
```

Claude will scan `docs/` (or whatever directory you name), generate a self-contained HTML file at `.claude/scratchpad/marginalia.html`, and open it in your default browser.

In the browser:

- Click any doc in the sidebar.
- Select a passage — a floating **💬 Add comment** button appears.
- Click, type, save. The passage is now highlighted; a card appears in the right sidebar.
- Filter comments per doc / all / open; mark as **resolved** or **dismissed** as you triage.
- Hit **Export** (or `Ctrl/Cmd+S`) to hand comments back. Three ways:
  - **Copy** — JSON to clipboard, paste into Claude.
  - **Download** — file to your Downloads folder, then tell Claude the path.
  - **Save to project** — writes directly to a folder you pick once (typically `.claude/scratchpad/`); Claude reads it from there without a paste.
- Or: if you have Chrome DevTools MCP connected, tell Claude "read my Marginalia comments" — it grabs them from the tab's `localStorage` directly.
- Hit `?` any time for the in-app help.

## Live mode (real-time refresh from disk)

By default the HTML has a snapshot of your docs baked in. If you edit a doc, the tool still shows the old version until you re-run the skill.

To fix that:

1. Click **🔗 Connect** in the header.
2. Pick your docs folder in the browser prompt (grants read permission).
3. The **● LIVE** badge appears in the header.
4. From now on, clicking **↻ Refresh** re-reads the folder from disk and rebuilds the doc list.

Requires Chrome or Edge (File System Access API). In Firefox / Safari the button is hidden — refresh means re-running the skill.

## Keyboard shortcuts

- `Ctrl/Cmd+K` — focus search
- `Ctrl/Cmd+S` — open export dialog
- `Ctrl/Cmd+R` — refresh (Live mode only; otherwise normal browser reload)
- `?` — open the help modal
- `Esc` — close a modal / dismiss the popover
- `Ctrl/Cmd+Enter` — save comment (inside the comment modal)

## Requirements

- **Python 3.9+** on your machine (for the build script — stdlib only, no `pip install`).
- A modern browser (Chrome / Edge / Safari / Firefox recent).
- Internet on **first open** — the app loads `marked` and `highlight.js` from cdnjs. Browser caches them after.
- For fully offline HTML: pass `--offline` to `build.py`. First offline build fetches the two libs into `vendor/`; subsequent builds inline from cache. No network needed at open time after that.

## Installation

### Per-project (recommended for teams)

Copy the `marginalia/` folder into your project at `.claude/skills/`:

```
your-project/
└── .claude/
    └── skills/
        └── marginalia/
            ├── SKILL.md
            ├── build.py
            ├── template.html
            ├── vendor/         # created on first --offline build
            └── README.md
```

Claude Code auto-discovers project skills.

### Global (recommended for personal use across many projects)

Copy to your user-level skills directory:

```
~/.claude/skills/marginalia/
```

Available in every project you open with Claude Code.

## build.py options

```
--docs-dir DIR       Directory to scan. Repeatable.  Default: docs/ (fallback: project root).
--auto               Scan the whole project. Skips .git, node_modules, .venv, target,
                     dist, .claude, .idea, .vscode, .cache, __pycache__, etc.
--project-root PATH  Where to resolve relative paths from. Default: cwd.
--output PATH        HTML output. Default: .claude/scratchpad/marginalia.html.
--project-name NAME  Shown in the app header. Default: cwd basename.
--offline            Inline marked + highlight.js. First run fetches them from cdnjs
                     into vendor/; subsequent runs reuse the cache.
--vendor-dir PATH    Cache location for --offline (default: next to build.py).
--no-open            Skip auto-opening the browser.
```

## Export format

```json
{
  "schema": "doc-reviewer.v1",
  "project": "MyProject",
  "docs_dir": "docs",
  "generated_at": "2026-07-31T14:22:03.512Z",
  "generator_session_id": "e7f2a1c3b4d5",
  "file_count": 24,
  "comments": [
    {
      "id": "c_a3f9d2xyz100",
      "doc_path": "docs/subsystems/07-legality-confidence-engine.md",
      "quote": "the segment status is confirmed if…",
      "context_before": "…decay function, and thus …",
      "context_after": "… otherwise it downgrades…",
      "comment": "Should this include an explicit tie-breaker for equal weights?",
      "created_at": "2026-07-31T14:15:12.001Z",
      "updated_at": "2026-07-31T14:16:00.812Z",
      "status": "open"
    }
  ]
}
```

`context_before` and `context_after` capture ~40 chars around the quote so a comment can still be located if surrounding text drifts.

## Data & privacy

- Nothing is uploaded. Comments live in your browser's `localStorage`, keyed by a hash of the docs directory absolute path.
- The bundled HTML contains the full text of every doc — treat it accordingly if your docs are sensitive.
- To wipe all comments, click 🗑 in the comments panel header.

## Limitations

- **Multi-user review** — comments live in one browser's `localStorage`. Not designed for concurrent editing.
- **File System Access API** requires Chrome/Edge; on Firefox/Safari, Live mode and Save-to-project are hidden. Everything else works.
- **Multi-node highlights** — selections spanning heavy inline formatting (e.g. bold+link+code in one selection) will save the comment but the visual highlight may be partial. The comment still appears in the sidebar with the exact quote for manual lookup.

## Roadmap

- Cross-reference validator: check every `[see NN](path)` link resolves.
- Doc statistics panel (word count, largest sections, most-linked docs).
- Multi-user comment sync via optional file export/import.

## License

MIT. Fork it, ship it, tell people.
