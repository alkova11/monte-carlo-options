# Data and saved artifacts

All data are synthetic GBM samples. No accounts, feeds, market subscriptions, API keys,
external observations, personal information or database are required.

`configs/european.json`, `configs/benchmark.json`, `configs/asian.json` specify inputs.
`reports/experiments/<run-id>/` contains immutable generated results (ignored by Git).
`reports/published/` contains selected compact evidence from actual completed runs,
including the repeated-seed Parquet table, summary tables, original manifest and
configuration. `publication_index.json` maps original artifact locations to these
portable copies and hashes them. Original manifest paths refer to the local run folder.

Manifest fields include run_id, project, Git state or reason unavailable, source hash,
lock hash, canonical config hash, seed, UTC times, status and artifact checksums.
Synthetic dataset_ids/dataset_hashes are empty rather than fabricated observations.
Parquet tables retain case_id/run_id/method and independent replicate identifiers.
NPZ arrays contain production independent units and raw payoffs; controls' raw payoff
array excludes pilot payoffs, while pilot seed/coefficient/cost are recorded. Seeds
regenerate pilots. Asian study reference is numerical and has its own seed and CI.

To reproduce figures, rerun the configuration. Large HTML figures embed Plotly for
offline use and are kept in generated run folders. Published screenshots and focused
HTML research figures are linked from the README. There is no hidden live data source.
