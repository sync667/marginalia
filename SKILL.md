---
name: marginalia
description: Generate a self-contained HTML tool for reviewing and commenting on any project's markdown documentation. Bundles every .md file into one browser page; the user highlights passages and adds inline comments; comments come back to Claude as structured JSON. Use when the user asks to review, browse, read through, annotate, comment on, proofread, or get feedback on docs, specs, ADRs, RFCs, design packages, or a wiki/docs folder — and offer it proactively whenever they are working across more than a handful of markdown files and would be better served reading and marking them up in a browser than scrolling the terminal.
---

# Marginalia

Named for the literary tradition of margin notes. Turns any project's markdown docs into a self-contained web review tool the user can open locally. Supports text highlighting, inline comments, cross-doc navigation and search, dark/light theme, live-refresh from disk, and structured export back to Claude.

## When to use this

**Run it when asked.** Any of these is a direct request: "review my docs", "let me comment on the specs", "open my documentation", "I want to annotate this", "/marginalia".

**Offer it when it fits.** Don't run it unprompted, but suggest it in one line — *"Want me to open these in Marginalia so you can comment inline?"* — when:

- You just generated or heavily edited several markdown docs and the user needs to read them over.
- The user is reviewing a doc set (`docs/`, `specs/`, `wiki/`, ADR or RFC folders) with more than ~5 files.
- The user is giving scattered feedback across many documents in chat and it's getting hard to track.
- The user asks "what do you think of these docs?" or wants a second pass on documentation quality.

**Skip it** for a single short file (just read it in the terminal), for non-markdown content, and when the user only wants a summary rather than to mark passages up.

## Step 1 — Generate & open

Decide what to scan. Ask the user only if ambiguous. Defaults, in order:

1. If the user names a directory (`review my docs/ folder`, `look at wiki/`) use that.
2. If `docs/` exists in the project root, use that.
3. Otherwise, offer `--auto` (scans the whole project excluding `.git`, `node_modules`, `.venv`, `target`, `dist`, `.claude`, etc.).
4. Multi-dir works too — pass `--docs-dir` multiple times.

Run the build script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/build.py" \
  --docs-dir <dir>  [--docs-dir <dir2> ...] \
  --output .claude/scratchpad/marginalia.html \
  --project-name "<current project name>"
```

`${CLAUDE_PLUGIN_ROOT}` is substituted with this skill's install directory. If it reaches you unsubstituted (older Claude Code, or a non-Claude agent), use the directory this `SKILL.md` lives in instead — typically `.claude/skills/marginalia/` or `~/.claude/skills/marginalia/`.

Add `--auto` if the user said "everything" / "the whole project".
Add `--offline` if the user wants a truly self-contained HTML (inlines Marked + highlight.js — first build fetches from cdnjs, subsequent builds reuse the cache in `vendor/`).

The script:
- Scans directories (natural sort — `01`, `02` before `10`).
- Bundles all doc content into one HTML at the output path.
- Opens it in the default browser.
- Prints: number of docs, total line count, session ID, path.

Report to the user in one line: how many docs, total lines, HTML path. Don't repeat the in-app help — the tool shows help on first-run automatically (they can also hit **`?`** anytime).

## Step 2 — When the user comes back with comments

**Try in this order:**

### A. Auto-read via Chrome DevTools MCP (fastest, no user action)

If the `mcp__plugin_chrome-devtools-mcp__*` tools are available and the user still has the Marginalia tab open:

1. Call `mcp__plugin_chrome-devtools-mcp__list_pages` — find the "Marginalia" tab.
2. Call `mcp__plugin_chrome-devtools-mcp__evaluate_script` with:
   ```js
   () => {
     const key = Object.keys(localStorage).find(k => k.startsWith("doc-reviewer.") && k.endsWith(".comments.v1"))
       || Object.keys(localStorage).find(k => k.startsWith("marginalia.") && k.endsWith(".comments.v1"));
     if (!key) return { comments: [], meta: null };
     return {
       comments: JSON.parse(localStorage.getItem(key)),
       meta: window.__META__ || null
     };
   }
   ```
3. Parse the result directly.

### B. Read from the project-saved file (if the user hit "Save to project")

Check `.claude/scratchpad/marginalia-comments.json` (or `.md`). The user grants folder access once via the browser's File System Access API prompt; subsequent exports write silently to that path.

### C. Paste / download fallback

The user exported to their Downloads folder (typical filename: `marginalia-comments-<project>-<timestamp>.json`) and points you to it, or pastes the JSON into chat directly. Parse it.

**Then, whichever path you got it from:**

- Group comments by `doc_path`.
- Show each: quote + user's note + status (`open` / `resolved` / `dismissed`).
- Ask what to do:
  1. Address open comments one by one (interactive).
  2. Batch-fix by category ("all typos", "all cross-ref fixes", "all TODOs").
  3. Archive without action (write to `docs/REVIEW-<date>.md`).
  4. Something else.

Only start editing docs after the user picks. Do not touch files based on a single comment without asking.

## Options the user can turn on inside the browser

- **🔗 Connect (Live mode)** — user picks a folder; the page then reads `.md` files directly from disk. **↻ Refresh** re-reads. This is how the user gets real-time updates when they edit docs and want to re-review without regenerating the HTML.
- **Save to project** (in the Export dialog) — writes the export directly to a project folder using the File System Access API. Path B above applies after this.
- Both features require Chrome / Edge (File System Access API). In Firefox / Safari they're hidden — the user must download exports and paste manually.

## Common user asks and what to run

- "review my docs" → default: `--docs-dir docs`.
- "review everything" → `--auto`.
- "review my specs and wiki" → `--docs-dir specs --docs-dir wiki`.
- "run marginalia offline" → add `--offline`.
- "refresh" → tell them to hit **↻** in the app (or reconnect Live mode).
- "how do I use this?" → tell them to hit **`?`** in the app (or the Help button).

## Notes for maintainers

- `template.html` is the review app — a single self-contained SPA. Uses `marked` and `highlight.js` from cdnjs by default; `--offline` inlines them.
- `build.py` is stdlib-only Python 3.9+. Its `--offline` cache goes to `$CLAUDE_PLUGIN_DATA/vendor` when installed as a plugin (survives updates), else `vendor/` next to the script.
- Packaged as a Claude Code plugin: `.claude-plugin/plugin.json` (manifest) and `.claude-plugin/marketplace.json` (single-entry marketplace pointing at the repo root). The root `SKILL.md` with no `skills/` subdirectory makes this a single-skill plugin automatically.
- Comments persist in `localStorage` keyed by a hash of the docs directory absolute path (so switching projects gives a fresh workspace).
- Text-selection persistence uses quote + ~40 chars of context on each side. Multi-node highlights (selections spanning `<strong>` / `<em>` / code) are handled via a fallback path that walks concatenated text.
- Not designed for concurrent multi-user review. Personal tool.
