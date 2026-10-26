# Third-party notices

The project's original source is MIT-licensed. Its dependencies retain their own
licenses; this file does not relicense them. Dependency versions are locked in
`uv.lock` and `package-lock.json`.

| Component | Use | License / notice |
| --- | --- | --- |
| NumPy | Sampling and array numerics | BSD-3-Clause; distributions include additional component licenses. |
| SciPy | Normal CDF and scientific routines | BSD-style; bundled libraries carry their own notices. |
| pandas | Research tables | BSD-3-Clause. |
| Apache Arrow / PyArrow | Parquet storage | Apache-2.0. |
| Plotly.py and Plotly.js | Charts and embedded offline figures | MIT; included copy in `LICENSES/plotly.txt`. |
| TypeScript | Development compiler | Apache-2.0; no compiler runtime is bundled in the app. |
| pytest / Ruff | Development checks | MIT. |
| Playwright | Optional browser validation | Apache-2.0; browser binaries are not distributed here. |

Plotly.js is embedded in the downloadable offline HTML research figures and served
from the installed Plotly Python package when the app runs. Upstream bundle notices
are preserved. The repository's PNG screenshots show the project's own interface.

No market data, proprietary research code, paid assets or third-party screenshots are
redistributed. Numerical methods were implemented from standard formulas; sources
consulted are listed in `docs/METHODOLOGY.md`. Historical experiment manifests record
the exact software versions used, including the earlier interface prototype.

For complete dependency and bundled-library terms, inspect the license files supplied
with the installed distributions and their upstream projects.
