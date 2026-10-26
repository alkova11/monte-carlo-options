// Runs the project's original Python estimator modules off the UI thread.
const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
let ready;
function status(text) { self.postMessage({ status: text }); }
async function initialise() {
  status("Preparing calculation engine…");
  const { loadPyodide } = await import(`${PYODIDE_BASE}pyodide.mjs`);
  const pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
  status("Loading numerical libraries…");
  await pyodide.loadPackage(["numpy", "scipy"]);
  const [source, metadata] = await Promise.all([
    fetch("/assets/python-engine.zip").then(r => { if (!r.ok) throw new Error("Engine source could not load."); return r.arrayBuffer(); }),
    fetch("/data/runtime.json").then(r => r.json()),
  ]);
  pyodide.unpackArchive(new Uint8Array(source), "zip", { extractDir: "/opt/options" });
  pyodide.runPython("import sys\nsys.path.insert(0, '/opt/options')\nfrom mc_options.browser import browser_run, configure_runtime");
  pyodide.globals.set("_metadata_json", JSON.stringify({ pyodide: "314.0.7", ...metadata }));
  pyodide.runPython("configure_runtime(_metadata_json)");
  status("Calculating prices…");
  return pyodide;
}
self.onmessage = async event => {
  const { id, config } = event.data;
  try {
    ready ??= initialise().catch(error => { ready = null; throw error; });
    const pyodide = await ready;
    pyodide.globals.set("_request_json", JSON.stringify(config));
    const text = await pyodide.runPythonAsync("browser_run(_request_json)");
    self.postMessage({ id, result: JSON.parse(text) });
  } catch (error) {
    const lines = String(error?.message ?? error).trim().split("\n");
    const message = lines.at(-1).replace(/^(ValueError|TypeError|KeyError): /, "");
    self.postMessage({ id, error: message || "Calculation failed. Please retry." });
  }
};
