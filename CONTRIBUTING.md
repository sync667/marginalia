# Contributing

Bugs, ideas, PRs — all welcome.

## Repo layout

```
marginalia/
├── SKILL.md                        # Claude Code invocation contract
├── build.py                        # Python 3.9+, stdlib only
├── template.html                   # single-file SPA (vanilla JS)
├── .claude-plugin/
│   ├── plugin.json                 # plugin manifest
│   └── marketplace.json            # single-entry marketplace (source: "./")
├── examples/
│   └── example-comments.json       # sample export payload
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
└── .github/workflows/ci.yml
```

`SKILL.md` sits at the repo root with no `skills/` subdirectory, which is what makes this load as a single-skill plugin. Don't move it.

## Development

```bash
# Sanity-check build.py against your own docs
python build.py --docs-dir ./docs --output /tmp/preview.html --no-open

# Full offline build (fetches marked + highlight.js into vendor/)
python build.py --offline

# Manifests must validate before you push — CI runs both
claude plugin validate . --strict
claude plugin validate ./.claude-plugin/plugin.json --strict
```

To try your working copy as a real install without touching your config:

```bash
CLAUDE_CONFIG_DIR=/tmp/mg-test claude plugin marketplace add .
CLAUDE_CONFIG_DIR=/tmp/mg-test claude plugin install marginalia@marginalia
CLAUDE_CONFIG_DIR=/tmp/mg-test claude plugin details marginalia
rm -rf /tmp/mg-test
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
- Releases pin a version: bump `version` in **both** `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (and `metadata.version` in `SKILL.md`), or Claude Code users won't receive the update.
- Test in Chrome + Firefox at minimum. Report if a feature is Chrome-only (e.g. File System Access API).
