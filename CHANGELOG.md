# Changelog

All notable changes to Marginalia are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — Initial public release

### Added
- Bundle any number of markdown directories into a single self-contained HTML review page (`build.py --docs-dir` repeatable, or `--auto`).
- Reader with 3-column layout: file tree · rendered markdown · comment thread.
- Comments: select text → floating **💬 Add comment** → modal → highlight persists in `localStorage`.
- Comment states: open / resolved / dismissed. Inline edit. Delete with confirm.
- Cross-doc `[link](other-doc.md)` navigation — opens in-app, preserves `#anchor` if present.
- Same-page heading anchors work (marked v12 headings post-processed with slug IDs).
- Search across every doc filename + content, filters sidebar.
- Dark / light theme, syntax highlighting via highlight.js.
- **In-app editor** — `✎ Edit` per doc (or `Ctrl+E`); saves to disk via File System Access API when Live mode is connected; falls back to `showSaveFilePicker` or download.
- **Live mode** — connect a docs folder once, `↻ Refresh` re-reads `.md` files from disk without a rebuild.
- **Save to project** button in the Export dialog — writes JSON/Markdown directly to a chosen folder so Claude can read it without a paste.
- **Help modal** shown on first run (and any time via `?`); explains workflow + shortcuts + privacy.
- Offline mode (`build.py --offline`) — inlines `marked` and `highlight.js` into the HTML; first build fetches from cdnjs into `vendor/`, subsequent builds reuse the cache.
- Multi-node highlight support — selections spanning inline formatting still wrap correctly.
- Keyboard shortcuts: `Ctrl/Cmd+K` (search), `Ctrl/Cmd+S` (export / save when editing), `Ctrl/Cmd+E` (edit toggle), `Ctrl/Cmd+R` (refresh in Live mode), `?` (help), `Esc` (close modal), `Ctrl/Cmd+Enter` (save comment).
