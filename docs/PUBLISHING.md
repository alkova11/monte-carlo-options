# Publication handoff

## Prepared release

- GitHub owner: `alkova11` (verified through the connected account).
- Repository: https://github.com/alkova11/monte-carlo-options.
- Visibility: public, explicitly authorized by the owner.
- Default branch: `main`.
- Release candidate: `v0.2.0`.
- License: MIT, explicitly selected by the owner; copyright uses the verified handle.
- Source archive: `release/monte-carlo-options-v0.2.0-source.zip` (local, ignored).
- Archive checksum: accompanying `.sha256` file.
- Public README, contribution guide, release notes and measured research evidence included.

Suggested repository description:

> Monte Carlo option-pricing research: variance reduction, confidence coverage,
> European/Asian options and a live Python/TypeScript lab.

Suggested topics:

`quantitative-finance`, `options-pricing`, `monte-carlo`, `black-scholes`,
`variance-reduction`, `python`, `numpy`, `scipy`, `plotly`, `typescript`,
`reproducible-research`.

The prepared source excludes environments, caches, browser binaries, raw generated
runs, credentials, local task instructions and the source archive itself. The package
retains the compact repeated-seed evidence and three actual app screenshots.

## Final GitHub steps

1. Create the public repository under the verified owner, or select the final target.
2. Upload/push the prepared source to `main`; do not add the ignored local environment.
3. Confirm the README, images, MIT license and research files render on GitHub.
4. Let GitHub Actions finish; inspect failures before announcing a checked remote build.
5. Add the description/topics and `reports/figures/linkedin-launch.png` as social preview.
6. Create release `v0.2.0` using `docs/RELEASE_NOTES.md` after the source is public.
7. Replace the explicit pending-link note in the LinkedIn draft with the real public URL.

The connected GitHub tools can read/write existing repositories but do not expose
new-repository creation in this session. Repository creation can use GitHub's web UI.
The Command Line Tools Git binary is available without changing the system Xcode license.

## LinkedIn

The launch copy and image alt text are in `docs/LINKEDIN.md`. Attach
`reports/figures/linkedin-launch.png`; optionally add `reports/figures/github-preview.png`.
Only publish after the repository URL is verified and the owner has approved posting.
The draft makes model assumptions explicit and uses measured evidence rather than a
single-run or market-return claim. No LinkedIn account changes have been made.

## Recorded checks

Local checks are captured in `release/validation.json` after running them. Remote
publication and CI status must not be described as completed before they are verified.
