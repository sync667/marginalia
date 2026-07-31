# Contributing

Bugs, ideas, PRs — all welcome.

## Repo layout

```
marginalia/
├── SKILL.md          # Claude Code invocation contract
├── build.py          # Python 3.9+, stdlib only
├── template.html     # single-file SPA (vanilla JS)
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── .github/workflows/ci.yml
└── docs/
    └── PUBLISHING.md
```

## Development

```bash
# Sanity-check build.py against your own docs
python build.py --docs-dir ./docs --output /tmp/preview.html --no-open

# Full offline build (fetches marked + highlight.js into vendor/)
python build.py --offline
```

The build script has no runtime deps. `template.html` uses `marked` and `highlight.js` from cdnjs unless `--offline` inlines them.

## Reporting issues

Include:
- OS + browser + version
- The command you ran
- Excerpt from the terminal output
- A short doc directory that reproduces the issue (if the bug is doc-specific)

## Pull requests

- Keep changes focused. One feature or fix per PR.
- Match existing code style (vanilla JS, no build step, small deps).
- If you add a UI element, add it to `README.md` and to the in-app help modal.
- If you change the export JSON schema, bump the `schema` field in `template.html` and note it in `CHANGELOG.md`.
- Test in Chrome + Firefox at minimum. Report if a feature is Chrome-only (e.g. File System Access API).
