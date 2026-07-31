#!/usr/bin/env node
'use strict';

/**
 * npm entry point for Marginalia.
 *
 * The tool itself is `build.py` (stdlib-only Python). This wrapper exists so
 * `npx @sync667/marginalia` works without a clone: it locates a usable Python
 * interpreter, then hands every argument straight through to build.py.
 */

const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const ROOT = path.resolve(__dirname, '..');
const SCRIPT = path.join(ROOT, 'build.py');
const MIN_MAJOR = 3;
const MIN_MINOR = 9;

/** Ask a candidate interpreter for its version. Returns null if it isn't usable. */
function probe(cmd) {
  let res;
  try {
    res = spawnSync(cmd, ['-c', 'import sys; print("%d.%d" % sys.version_info[:2])'], {
      encoding: 'utf8',
      timeout: 10000,
      windowsHide: true,
    });
  } catch {
    return null;
  }
  if (res.error || res.status !== 0 || !res.stdout) return null;

  const parts = res.stdout.trim().split('.');
  const major = Number(parts[0]);
  const minor = Number(parts[1]);
  if (!Number.isInteger(major) || !Number.isInteger(minor)) return null;

  const ok = major > MIN_MAJOR || (major === MIN_MAJOR && minor >= MIN_MINOR);
  return { cmd, version: `${major}.${minor}`, ok };
}

function findPython() {
  // `py` (the Windows launcher) first on Windows: it resolves the newest install
  // and avoids the App Execution Alias stub that shadows `python` on some setups.
  const candidates =
    process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python'];

  const rejected = [];
  for (const cmd of candidates) {
    const found = probe(cmd);
    if (!found) continue;
    if (found.ok) return { found, rejected };
    rejected.push(found);
  }
  return { found: null, rejected };
}

function fail(message) {
  process.stderr.write(`marginalia: ${message}\n`);
  process.exit(1);
}

if (!fs.existsSync(SCRIPT)) {
  fail(`build.py is missing from the package (looked in ${ROOT}). Please report this at
  https://github.com/sync667/marginalia/issues`);
}

const { found, rejected } = findPython();

if (!found) {
  const detail = rejected.length
    ? `Found ${rejected.map((r) => `${r.cmd} ${r.version}`).join(', ')}, but Marginalia needs ${MIN_MAJOR}.${MIN_MINOR} or newer.`
    : 'No Python interpreter was found on PATH.';
  fail(`${detail}

Marginalia's generator is a Python script, so a local Python ${MIN_MAJOR}.${MIN_MINOR}+ is required
(standard library only — there is nothing to pip install).

  macOS     brew install python
  Windows   winget install Python.Python.3.12
  Linux     apt install python3   (or your distro's equivalent)

Then re-run this command.`);
}

const result = spawnSync(found.cmd, [SCRIPT, ...process.argv.slice(2)], {
  stdio: 'inherit',
  windowsHide: true,
  env: { ...process.env, MARGINALIA_PROG: 'marginalia' },
});

if (result.error) {
  fail(`failed to run ${found.cmd}: ${result.error.message}`);
}
// Propagate a signal death as the conventional 128+n so shells see it correctly.
process.exit(result.signal ? 1 : (result.status ?? 1));
