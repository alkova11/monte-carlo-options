# Contributing

Use Python 3.12, uv.lock and the checked-in TypeScript lockfile. Run commands from
the repository root. The initial application is a local research tool.

## Set up

```bash
uv sync --locked --python 3.12
npm ci --ignore-scripts --cache .npm-cache
```

## Before a pull request

```bash
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
npm run typecheck
npm run build
uv run --locked quant-options price --config configs/european.json
```

For UI changes, run the opt-in browser workflow described in README.md. Commit the
regenerated `app/web/static/app.js` whenever its TypeScript source changes.

Keep numerical logic in `src/mc_options`, not the browser. State the independent
sampling units and count pilot costs. Use seeded statistical checks with justified
tolerances; do not require every 95% confidence interval to contain the reference.

Report before/after behaviour, relevant checks and material limitations in pull
requests. Benchmark claims must link to saved repeated-seed evidence. If changing
experiment design or estimators, regenerate results and describe any change to the
reference, averaging dates, budget or uncertainty calculation.

Do not commit virtual environments, caches, credentials, generated experiment runs,
local paths or market data with redistribution restrictions. The bundled evidence is
synthetic. No external API is needed for routine CI.
