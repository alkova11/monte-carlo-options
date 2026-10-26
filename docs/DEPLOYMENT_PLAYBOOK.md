# Reusable project publication workflow

Use this workflow for future projects. GitHub hosts the source; a public web host runs or serves the app. LinkedIn links to both.

1. Finish a working local application and test its main workflow with representative inputs.
2. Prepare a README with setup commands, assumptions, measured results, limitations and a screenshot. Choose a license and exclude secrets, private data, environments and temporary files.
3. Create a public GitHub repository, upload the reviewed source, and run its CI checks.
4. Select hosting that supports the application. Static HTML/JavaScript apps can use static hosting. This project executes its Python estimators through Pyodide in a browser worker. Apps needing private API keys, server databases, large jobs or unsupported Python packages require a suitable backend.
5. Build and test the actual public configuration, including first load, calculations, downloads, errors, mobile layout and data persistence. Publish it with public visitor access, then keep the verified URL in the README.
6. Prepare a PNG from the real app and a concise description stating what it does and what the evidence shows. Add the live link and repository link to a LinkedIn post or Featured project.
7. For updates, reuse the same repository and hosting project, test the change and publish a new version. Keep source and deployment versions traceable.

Suggested request for your next project:

> Prepare this project for public GitHub with my chosen license, test and publish a working live demo, and create a PNG and LinkedIn description. Reuse existing repository and hosting identities where present. Report the verified links and any remaining blockers.

## This app's browser build

Run `npm ci`, `npm run build`, then `uv run python scripts/build_hosted.py` from the repository. The generated `hosted/dist` directory is a static website. Hosting registration and access configuration are separate from generating files. The ignored `hosted` directory has its own hosting source repository; do not copy its identity into a new project.

The public demo downloads a pinned Pyodide runtime plus NumPy/SciPy on first calculation. It supports up to 200,000 payoff evaluations per estimator. The most recent five runs are stored in each visitor's browser when IndexedDB is available. Download the ZIP to retain results independently of browser storage. Browser dependency versions are recorded in each archive and can differ from the native locked environment. Charts in browser archives are JSON; native archives also include HTML figures.

The original Python CLI and local web server remain available for native research runs. Published benchmark findings come from the saved native research evidence, not from browser timing.
