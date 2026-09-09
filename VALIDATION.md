# Local validation record

Validation date: 2026-09-08

This repository was prepared and validated locally. It has not been published.

## Exact candidate checks

- Backend: 511 tests passed with `pytest`.
- Frontend: `npm audit` reported 0 vulnerabilities.
- Frontend: `npm run lint` passed.
- Frontend: `npm run build` passed (3,184 modules transformed).
- Desktop: clean `npm ci` completed and `npm audit` reported 0 vulnerabilities.
- Desktop: the backend bundle was built successfully with PyInstaller 6.22.2.
- Desktop: the Windows NSIS installer was built successfully with
  `electron-builder 26.16.1` and `--publish never`.
- Local HTTP smoke: `/api/health` returned `ok=true` and
  `database_ready=true`; `/` and the generated JavaScript asset returned 200.

The temporary portable Node binary, Google Maps scraper binary, dependency
directories, PyInstaller output, frontend build output, and generated installer
were removed after validation. They are not part of this Git snapshot.

## Build-only artifact evidence

- Installer SHA-256:
  `304378F7340D924269832D063EE032C9229EB71BFFABBF8B17D4B904952DAB8D`
- Packaged backend executable SHA-256:
  `D4CFFAB5EBE0C572A3867FCD90C112553C13DF40DFB2D5DAB7EC9AEDEC88A7CB`

These hashes identify ephemeral local validation artifacts; the artifacts are
not distributed by this repository.

## Scope limits

The checks above prove tests, dependency audits, compilation, packaging, and a
source-mode HTTP smoke on this machine. Browser visual/console inspection was
not observable because the required in-app browser driver was unavailable in
this session. These checks do not prove live behavior of Google Maps,
Instagram, AI providers, external publishing, auto-update, code signing, or
production use.
