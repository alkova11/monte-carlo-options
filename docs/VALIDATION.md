# Local release validation — v0.2.0

Checked on 25 October 2026. These are local results, not a claim that remote GitHub
Actions has completed.

| Check | Observed result |
| --- | --- |
| Python test suite | 54 passed. |
| Clean extracted source archive | 54 passed; package root resolved inside the extracted checkout. |
| Clean-checkout CLI pricing | Succeeded using `configs/european.json`; artifacts saved inside that checkout. |
| Ruff lint and formatting | Passed. |
| TypeScript typecheck and build | Passed. |
| uv lock check | Passed offline. |
| Public Markdown links | All relative targets checked and present. |
| Research evidence integrity | All portable evidence SHA-256 hashes matched the publication index. |
| Research cardinality | 24 cases, 21,600 estimates, 100 replicates per case/method/budget. |
| Source archive integrity | ZIP CRC and per-file SHA-256 validation passed. |
| Publication content scan | No credential-like strings or personal absolute paths detected by the release script. |
| Publication graphics | Rendered locally from the actual app screenshot and visually inspected. |

The HTTP tests require permission to bind a temporary loopback port. The restricted
sandbox blocked that operation; rerunning with loopback access passed all tests.
Browser workflow validation from the custom-interface build covers explicit runs,
hover/estimator switches without resampling, restoration, downloads, research navigation,
invalid inputs, Asian options and desktop/tablet/mobile layouts. The interface code
was not changed during release preparation.

Reproduce the release-package checks:

```bash
uv run --locked python scripts/prepare_release.py
uv run --locked python scripts/check_release.py
```

The scripts build and check a local source archive; they do not upload anything or
create a remote repository. See `docs/PUBLISHING.md` for the separate publication steps.
