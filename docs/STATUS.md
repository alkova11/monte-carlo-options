# Release status

The v0.2.0 source release is prepared locally. Publication status is recorded separately
in `docs/PUBLISHING.md`; no remote repository or LinkedIn post is assumed to exist.

## Implemented

European references/limits, three Monte Carlo estimators with independent-unit
uncertainty, repeated-seed research, arithmetic Asian extension, custom local web app,
CLI workflows, downloadable provenance and research documentation.

The verified saved European grid has 24 cases and 21,600 estimates. Earlier narrative
counts were corrected to match the actual data. Historical manifests remain unchanged.

## Checked locally

- 54 Python tests: numerical references, estimator uncertainty, repeated runs, inputs,
Asian controls, real HTTP workflows and artifact checksums.
- Ruff lint/format; TypeScript typecheck/build; dependency lock validation.
- Browser workflow: explicit runs, no resampling on hover/switch, refresh restoration,
downloads, research navigation, error retention, Asian options and responsive layouts.
- Portable research-evidence SHA-256 hashes checked against the publication index.
- Clean extracted source archive: all 54 tests and the CLI pricing workflow passed.
- Release-package hashes, public Markdown links and publication graphics checked.

The app binds to loopback; no external data subscription, account or API key is required.
GitHub Actions is prepared; remote checks have not been claimed as completed.

## Publication preparation

README, contribution guidance, release notes, verified LinkedIn copy, screenshots and
source archive/checksum are prepared for owner review. GitHub account alkova11 is connected; the owner selected the MIT license.
The proposed new repository is alkova11/monte-carlo-options. Local system Git is unavailable until the host's
Xcode licence issue is resolved; GitHub access can also be provided through a connection.


## 26 October 2026 — public browser release

Public browser demo deployed with visitor access. Same Python estimators run through Pyodide in a worker; per-visitor IndexedDB retains five runs. Verified browser/native prices within 1e-10, ZIP checksums, reload, method switching, research, Asian pricing and visitor isolation. 57 Python tests and TypeScript checks pass. GitHub publication is underway in alkova11/monte-carlo-options. PNG and LinkedIn draft prepared; no LinkedIn post sent.
