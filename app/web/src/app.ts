const browserMode = document.documentElement.dataset.runtime === "browser";
let browserRuntime: Promise<typeof import("./browser-runtime.js")> | null = null;
function publicRuntime() { return browserRuntime ??= import("./browser-runtime.js"); }
type Method = "ordinary" | "antithetic" | "control";
type Product = "European" | "Arithmetic Asian";
interface OptionConfig {
  spot: number; strike: number; rate: number; dividend_yield: number;
  volatility: number; maturity: number; option_type: "call" | "put";
}
interface Config {
  product: Product; option: OptionConfig; samples: number; seed: number;
  method: Method; observation_dates?: number[];
}
interface Estimate {
  method: Method; price: number; standard_error: number; ci_low: number; ci_high: number;
  absolute_error: number | null; benchmark_price: number | null; effective_samples: number;
  pilot_samples: number; requested_samples: number; used_samples: number;
  runtime_seconds: number; zero_payoff_frequency: number; beta: number; warning: string;
  confidence_method: string;
}
interface Figure { data: Record<string, unknown>[]; layout: Record<string, unknown> }
interface RunResult {
  run_id: string; config: Config; estimates: Partial<Record<Method, Estimate>>;
  control_reference: number | null;
  figures: { paths: Figure; methods: Partial<Record<Method, { payoffs: Figure; convergence: Figure }>> };
}
interface ResearchRow {
  method: Method; sample_count: number; rmse: number; coverage: number;
  coverage_low: number; coverage_high: number; variance_reduction: number | null;
  mean_runtime_seconds: number;
}
interface Research {
  available: boolean; run_id: string; cases: string[]; selected: string;
  replicates: number; case_count: number; estimate_count: number;
  overview: { method: Method; variance_reduction: number; coverage: number }[];
  rows: ResearchRow[]; figures: { rmse: Figure; error_time: Figure };
}
declare const Plotly: {
  react: (element: HTMLElement, data: unknown[], layout: Record<string, unknown>, config: Record<string, unknown>) => Promise<unknown>;
  Plots: { resize: (element: HTMLElement) => void };
};
const $ = <T extends HTMLElement = HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing interface element: ${id}`);
  return element as T;
};
const input = (id: string) => $<HTMLInputElement>(id);
const number = (id: string) => Number(input(id).value);
const labels: Record<Method, string> = { ordinary: "Ordinary MC", antithetic: "Antithetic", control: "Control variate" };
const colors: Record<Method, string> = { ordinary: "#62a8fa", antithetic: "#b89aff", control: "#c2ed83" };
const price = (v: number | null | undefined, digits = 5) => v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const integer = (v: number) => v.toLocaleString("en-US");
const percent = (v: number) => `${(100 * v).toFixed(1)}%`;
let current: RunResult | null = null;
let selected: Method = "control";
let kind: "call" | "put" = "call";
let running = false;
let touched = false;
let research: Research | null = null;
let researchRequest = 0;
let toastTimeout = 0;
const form = $<HTMLFormElement>("pricing-form");

function message(id: string, text: string) {
  $(id).textContent = text;
  $(id).hidden = !text;
}
function toast(text: string) {
  window.clearTimeout(toastTimeout);
  message("toast", text);
  toastTimeout = window.setTimeout(() => message("toast", ""), 4000);
}
function getConfig(): Config {
  const config: Config = {
    product: $<HTMLSelectElement>("product").value as Product,
    option: {
      spot: number("spot"), strike: number("strike"), rate: number("rate") / 100,
      dividend_yield: number("dividend") / 100, volatility: number("volatility") / 100,
      maturity: number("maturity"), option_type: kind,
    }, samples: number("samples"), seed: number("seed"), method: selected,
  };
  if (config.product === "Arithmetic Asian") {
    config.observation_dates = $<HTMLTextAreaElement>("dates").value.split(",").map(v => Number(v.trim()));
  }
  return config;
}
function signature(c: Config): string {
  // The view-only selected method never invalidates numerical samples.
  return JSON.stringify({ product: c.product, option: Object.entries(c.option).sort(([a], [b]) => a.localeCompare(b)), samples: c.samples, seed: c.seed, dates: c.observation_dates });
}
function markDirty() {
  touched = true;
  $("stale-note").hidden = !current || signature(getConfig()) === signature(current.config);
  document.querySelectorAll<HTMLButtonElement>("[data-budget]").forEach(button => {
    button.classList.toggle("chosen", Number(button.dataset.budget) === number("samples"));
  });
}
function setKind(value: "call" | "put", dirty = true) {
  kind = value;
  document.querySelectorAll<HTMLButtonElement>("[data-kind]").forEach(button => {
    const active = button.dataset.kind === kind;
    button.classList.toggle("chosen", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (dirty) markDirty();
}
function updateProduct() {
  const asian = $<HTMLSelectElement>("product").value === "Arithmetic Asian";
  $("asian-fields").hidden = !asian;
  // A displayed saved result stays inspectable even while draft inputs are edited.
  if (!current && asian && selected === "antithetic") selected = "control";
}
function loadForm(c: Config) {
  $<HTMLSelectElement>("product").value = c.product;
  const fields: Record<string, number> = {
    spot: c.option.spot, strike: c.option.strike, rate: c.option.rate * 100,
    dividend: c.option.dividend_yield * 100, volatility: c.option.volatility * 100,
    maturity: c.option.maturity, samples: c.samples, seed: c.seed,
  };
  Object.entries(fields).forEach(([id, value]) => { input(id).value = String(value); });
  if (c.observation_dates) $<HTMLTextAreaElement>("dates").value = c.observation_dates.join(", ");
  setKind(c.option.option_type, false);
  updateProduct();
  document.querySelectorAll<HTMLButtonElement>("[data-budget]").forEach(button => {
    button.classList.toggle("chosen", Number(button.dataset.budget) === c.samples);
  });
}
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  if (browserMode) return await (await publicRuntime()).request(url, init) as T;
  const response = await fetch(url, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data as T;
}
async function draw(id: string, figure: Figure) {
  const element = $(id);
  element.querySelector(".chart-empty")?.remove();
  const layout = { ...figure.layout, autosize: true, height: element.clientHeight, uirevision: current?.run_id ?? "research" };
  await Plotly.react(element, figure.data, layout, {
    responsive: true, displaylogo: false, displayModeBar: "hover",
    modeBarButtons: [["toImage"], ["zoom2d", "pan2d"],
      ["zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]], scrollZoom: false,
    toImageButtonOptions: { format: "png", scale: 2 },
  });
}
function cell(text: string, strong = false): HTMLTableCellElement {
  const td = document.createElement("td");
  if (strong) {
    const content = document.createElement("strong");
    content.textContent = text;
    td.append(content);
  } else td.textContent = text;
  return td;
}
function methodCell(method: Method): HTMLTableCellElement {
  const td = document.createElement("td");
  const content = document.createElement("span");
  content.className = "method-cell";
  const dot = document.createElement("i");
  dot.className = "method-indicator";
  dot.style.background = colors[method];
  const text = document.createElement("strong");
  text.textContent = labels[method];
  content.append(dot, text);
  td.append(content);
  return td;
}
function comparison(run: RunResult) {
  const body = $("comparison-body");
  body.replaceChildren();
  for (const method of ["ordinary", "antithetic", "control"] as Method[]) {
    const e = run.estimates[method];
    if (!e) continue;
    const row = document.createElement("tr");
    row.classList.toggle("selected-row", method === selected);
    row.append(methodCell(method), cell(price(e.price), true), cell(price(e.standard_error)),
      cell(`[${price(e.ci_low, 4)}, ${price(e.ci_high, 4)}]`), cell(price(e.absolute_error)),
      cell(integer(e.effective_samples)), cell(`${(e.runtime_seconds * 1000).toFixed(2)} ms`));
    body.append(row);
  }
}
async function render(run: RunResult, drawPaths = false) {
  if (!run.estimates[selected]) selected = run.estimates.control ? "control" : "ordinary";
  const e = run.estimates[selected]!;
  const figs = run.figures.methods[selected]!;
  const asian = run.config.product === "Arithmetic Asian";
  $("metric-price").textContent = price(e.price);
  $("metric-price-note").textContent = `${run.config.option.option_type === "call" ? "Call" : "Put"} · ${run.config.product}`;
  $("metric-se").textContent = price(e.standard_error);
  $("metric-se-note").textContent = `${integer(e.effective_samples)} independent units`;
  $("reference-label").firstChild!.textContent = asian ? "Geometric control" : "Black–Scholes";
  $("metric-reference").textContent = price(asian ? run.control_reference : e.benchmark_price);
  $("metric-reference-note").textContent = asian ? "Not the arithmetic price" : "Analytical reference";
  $("error-label").firstChild!.textContent = asian ? "95% CI width" : "Absolute error";
  $("metric-error").textContent = price(asian ? e.ci_high - e.ci_low : e.absolute_error);
  $("metric-error-note").textContent = asian ? "Normal approximation" : "Distance from reference";
  $("zero-caption").textContent = `${percent(e.zero_payoff_frequency)} zero payoffs · Raw discounted payoffs, before adjustment.`;
  $("benchmark-legend").textContent = asian ? "No analytical arithmetic reference" : "Black–Scholes";
  const dash = document.querySelector<HTMLElement>(".legend-dash")!;
  dash.hidden = asian;
  const dot = document.querySelector<HTMLElement>(".legend-dot")!;
  dot.style.background = colors[selected];
  message("warning", e.warning + (asian ? (e.warning ? " " : "") + "The geometric price is a control expectation. Arithmetic Asian has no analytical reference here; see Research / full results for its independent numerical benchmark." : ""));
  $("result-state").textContent = `${labels[selected].toUpperCase()} · SEED ${run.config.seed}`;
  $("result-dot").style.background = "#c2ed83";
  $("run-provenance").textContent = `RUN ${run.run_id.slice(0, 8)} · ${integer(run.config.samples)} total budget · seed ${run.config.seed}`;
  document.querySelectorAll<HTMLButtonElement>("[data-method]").forEach(button => {
    button.classList.toggle("chosen", button.dataset.method === selected);
    button.setAttribute("aria-pressed", String(button.dataset.method === selected));
    button.disabled = !run.estimates[button.dataset.method as Method];
  });
  comparison(run);
  for (const id of ["download-csv", "download-config", "download-zip"]) $<HTMLButtonElement>(id).disabled = false;
  const tasks = [draw("payoffs-chart", figs.payoffs), draw("convergence-chart", figs.convergence)];
  if (drawPaths) tasks.push(draw("paths-chart", run.figures.paths));
  await Promise.all(tasks);
}
async function submit() {
  if (running || !form.reportValidity()) return;
  const config = getConfig();
  if (config.product === "Arithmetic Asian" && selected === "antithetic") {
    config.method = "control";
  }
  if (config.product === "Arithmetic Asian" && ($<HTMLTextAreaElement>("dates").value.trim() === "" || config.observation_dates!.some(v => !Number.isFinite(v)))) {
    message("form-error", "Enter finite observation dates in years, separated by commas.");
    return;
  }
  running = true;
  touched = true;
  document.body.classList.add("busy");
  $<HTMLButtonElement>("run-button").disabled = true;
  $("run-label").textContent = "Simulating…";
  message("form-error", "");
  const before = $("result-state").textContent;
  $("result-state").textContent = "SAMPLING & SAVING…";
  try {
    const result = await api<RunResult>("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config),
    });
    current = result;
    selected = result.config.method;
    try { localStorage.setItem("mc-options.last-run", result.run_id); } catch { /* Storage is optional. */ }
    await render(result, true);
    $("stale-note").hidden = signature(getConfig()) === signature(result.config);
    toast("Simulation complete. Results saved on your computer.");
  } catch (error) {
    message("form-error", error instanceof Error ? error.message : "Could not complete the run.");
    $("result-state").textContent = before;
  } finally {
    running = false;
    document.body.classList.remove("busy");
    $<HTMLButtonElement>("run-button").disabled = false;
    $("run-label").textContent = "Run simulation";
  }
}
function download(resource: string) {
  if (!current) return;
  if (browserMode) {
    void publicRuntime().then(runtime => runtime.download(current!.run_id, resource))
      .catch(error => toast(error instanceof Error ? error.message : "Download failed."));
    return;
  }
  const anchor = document.createElement("a");
  anchor.href = `/api/runs/${current.run_id}/${resource}`;
  anchor.download = "";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}
function details() {
  const body = $("budget-details");
  body.replaceChildren();
  if (current) {
    for (const method of Object.keys(current.estimates) as Method[]) {
      const e = current.estimates[method]!;
      const line = document.createElement("div");
      line.className = "budget-line";
      const title = document.createElement("span"); title.textContent = labels[method];
      const count = document.createElement("strong"); count.textContent = `${integer(e.used_samples)} used · ${integer(e.effective_samples)} units · ${integer(e.pilot_samples)} pilot`;
      line.append(title, count); body.append(line);
    }
  }
  $<HTMLDialogElement>("details-dialog").showModal();
}
async function loadResearch(caseId?: string) {
  const request = ++researchRequest;
  try {
    const result = await api<Research>(`/api/research${caseId ? `?case=${encodeURIComponent(caseId)}` : ""}`);
    if (request !== researchRequest) return;
    if (!result.available) throw new Error("No saved research suite is available yet. Run the benchmark CLI to create one.");
    research = result;
    message("research-error", "");
    $("research-count").textContent = `${integer(result.estimate_count)} estimates. ${result.case_count} cases. ${result.replicates} seeds.`;
    const select = $<HTMLSelectElement>("research-case");
    if (!select.options.length) result.cases.forEach(value => {
      const option = document.createElement("option"); option.value = value;
      option.textContent = value.replaceAll("_", " · "); select.append(option);
    });
    select.value = result.selected;
    const metrics = $("research-metrics"); metrics.replaceChildren();
    result.overview.forEach(o => {
      const article = document.createElement("article"); article.className = "metric-card";
      const label = document.createElement("div"); label.className = "metric-label"; label.textContent = labels[o.method];
      const value = document.createElement("div"); value.className = "metric-value"; value.textContent = `${o.variance_reduction.toFixed(2)}×`;
      value.style.color = colors[o.method];
      const note = document.createElement("div"); note.className = "metric-note"; note.textContent = `Median variance reduction · ${percent(o.coverage)} coverage`;
      article.append(label, value, note); metrics.append(article);
    });
    const body = $("research-body"); body.replaceChildren();
    result.rows.forEach(r => {
      const row = document.createElement("tr");
      row.append(methodCell(r.method), cell(integer(r.sample_count)), cell(price(r.rmse)),
        cell(percent(r.coverage)), cell(`[${percent(r.coverage_low)}, ${percent(r.coverage_high)}]`),
        cell(r.variance_reduction == null ? "—" : `${r.variance_reduction.toFixed(2)}×`), cell(`${(r.mean_runtime_seconds * 1000).toFixed(3)} ms`));
      body.append(row);
    });
    await Promise.all([draw("research-rmse", result.figures.rmse), draw("research-time", result.figures.error_time)]);
  } catch (error) { message("research-error", error instanceof Error ? error.message : "Could not read research results."); }
}
function navigate(page: string) {
  const names: Record<string, string> = { lab: "Pricing lab", research: "Research", methodology: "Methodology" };
  if (!names[page]) page = "lab";
  document.querySelectorAll<HTMLElement>(".page").forEach(p => { p.hidden = p.id !== `page-${page}`; });
  document.querySelectorAll<HTMLButtonElement>("[data-page]").forEach(button => {
    const active = button.dataset.page === page;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  $("breadcrumb-current").textContent = names[page];
  history.replaceState(null, "", `#${page}`);
  if (page === "research" && !research) void loadResearch();
  window.dispatchEvent(new Event("resize"));
  window.scrollTo({ top: 0 });
}

form.addEventListener("submit", event => { event.preventDefault(); void submit(); });
form.addEventListener("input", markDirty);
form.addEventListener("change", markDirty);
$("product").addEventListener("change", updateProduct);
document.querySelectorAll<HTMLButtonElement>("[data-kind]").forEach(button => button.addEventListener("click", () => setKind(button.dataset.kind as "call" | "put")));
document.querySelectorAll<HTMLButtonElement>("[data-budget]").forEach(button => button.addEventListener("click", () => { input("samples").value = button.dataset.budget!; markDirty(); }));
document.querySelectorAll<HTMLButtonElement>("[data-method]").forEach(button => button.addEventListener("click", () => {
  selected = button.dataset.method as Method;
  if (current) void render(current).catch(() => toast("Could not render the chart. Refresh to retry."));
  else document.querySelectorAll<HTMLButtonElement>("[data-method]").forEach(b => b.classList.toggle("chosen", b === button));
}));
document.querySelectorAll<HTMLButtonElement>("[data-page]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.page!)));
$("research-case").addEventListener("change", () => void loadResearch($<HTMLSelectElement>("research-case").value));
$("reset").addEventListener("click", () => {
  form.reset(); setKind("call", false); updateProduct(); markDirty(); message("form-error", "");
  toast("Inputs reset. Saved results stay visible until you run again.");
});
$("download-csv").addEventListener("click", () => download("csv"));
$("download-config").addEventListener("click", () => download("config"));
$("download-zip").addEventListener("click", () => download("zip"));
$("show-details").addEventListener("click", details);
$("close-details").addEventListener("click", () => $<HTMLDialogElement>("details-dialog").close());
$("details-dialog").addEventListener("click", event => { if (event.target === $("details-dialog")) $<HTMLDialogElement>("details-dialog").close(); });
document.addEventListener("keydown", event => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !$("page-lab").hidden) { event.preventDefault(); void submit(); }
});
let resizeTimer = 0;
window.addEventListener("resize", () => {
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => document.querySelectorAll<HTMLElement>(".js-plotly-plot").forEach(element => {
    if (element.getBoundingClientRect().width && element.offsetParent) Plotly.Plots.resize(element);
  }), 100);
});

async function restore() {
  try {
    let id: string | null = null;
    try { id = localStorage.getItem("mc-options.last-run"); } catch { /* Storage optional. */ }
    let result: RunResult;
    if (id) {
      try { result = await api<RunResult>(`/api/runs/${encodeURIComponent(id)}/result`); }
      catch { result = await api<RunResult>("/api/latest"); }
    } else result = await api<RunResult>("/api/latest");
    if (touched || running) return;
    current = result; selected = result.config.method;
    loadForm(result.config);
    await render(result, true);
    $("result-state").textContent = `SAVED RUN · SEED ${result.config.seed}`;
  } catch { /* An empty workspace requires an explicit first run; no random sampling on load. */ }
}
navigate(location.hash.slice(1) || "lab");
window.addEventListener("options-engine-status", event => {
  if (running) $("run-label").textContent = (event as CustomEvent<string>).detail;
});
window.addEventListener("options-storage-warning", event => {
  toast((event as CustomEvent<string>).detail);
});
void restore();
