const DB_NAME = "mc-options-public-v1";
const KEEP_RUNS = 5;
let worker = null;
let active = false;
let sequence = 0;
let research = null;
let example = null;
const memory = new Map();
const jobs = new Map();
async function database() {
    return new Promise((resolve, reject) => {
        const opening = indexedDB.open(DB_NAME, 1);
        opening.onupgradeneeded = () => { opening.result.createObjectStore("runs", { keyPath: "run_id" }); };
        opening.onsuccess = () => resolve(opening.result);
        opening.onerror = () => reject(opening.error);
    });
}
async function allRuns() {
    const db = await database();
    return new Promise((resolve, reject) => {
        const tx = db.transaction("runs", "readonly");
        const query = tx.objectStore("runs").getAll();
        query.onsuccess = () => resolve(query.result);
        query.onerror = () => reject(query.error);
        tx.oncomplete = () => db.close();
    });
}
async function save(run) {
    memory.set(run.run_id, run);
    try {
        const old = await allRuns();
        const db = await database();
        await new Promise((resolve, reject) => {
            const tx = db.transaction("runs", "readwrite");
            const store = tx.objectStore("runs");
            store.put({ ...run, savedAt: Date.now() });
            const expired = old.sort((a, b) => (b.savedAt ?? 0) - (a.savedAt ?? 0)).slice(KEEP_RUNS - 1);
            expired.forEach(item => store.delete(item.run_id));
            tx.oncomplete = () => { db.close(); resolve(); };
            tx.onerror = () => { db.close(); reject(tx.error); };
            tx.onabort = () => { db.close(); reject(tx.error); };
        });
    }
    catch {
        window.dispatchEvent(new CustomEvent("options-storage-warning", { detail: "Browser storage is unavailable. Download your run to keep it." }));
    }
}
async function exampleRun() {
    example ??= fetch("/data/example.json").then(async (response) => {
        if (!response.ok)
            throw new Error("Saved example could not be loaded.");
        return await response.json();
    });
    return example;
}
async function findRun(id) {
    const held = memory.get(id);
    if (held)
        return held;
    try {
        const saved = (await allRuns()).find(r => r.run_id === id);
        if (saved)
            return saved;
    }
    catch { /* Optional storage. */ }
    const savedExample = await exampleRun();
    if (savedExample.run_id === id)
        return savedExample;
    throw new Error("This run is not stored in this browser. Run it again or use its downloaded archive.");
}
function engine() {
    if (worker)
        return worker;
    worker = new Worker(new URL("/static/pricing-worker.mjs", location.origin), { type: "module" });
    worker.onmessage = event => {
        const message = event.data;
        if (message.status)
            window.dispatchEvent(new CustomEvent("options-engine-status", { detail: message.status }));
        if (message.id == null)
            return;
        const job = jobs.get(message.id);
        if (!job)
            return;
        window.clearTimeout(job.timer);
        jobs.delete(message.id);
        if (message.error)
            job.reject(new Error(message.error));
        else
            job.resolve(message.result);
    };
    worker.onerror = () => {
        for (const job of jobs.values()) {
            window.clearTimeout(job.timer);
            job.reject(new Error("The pricing engine could not load. Check your connection and retry."));
        }
        jobs.clear();
        worker?.terminate();
        worker = null;
    };
    return worker;
}
async function compute(config) {
    if (active)
        throw new Error("A calculation is already running in this browser.");
    active = true;
    try {
        const result = await new Promise((resolve, reject) => {
            const id = ++sequence;
            const timer = window.setTimeout(() => {
                jobs.delete(id);
                worker?.terminate();
                worker = null;
                reject(new Error("The engine took too long. Check your connection or try a smaller budget."));
            }, 180_000);
            jobs.set(id, { resolve, reject, timer });
            engine().postMessage({ id, config });
        });
        await save(result);
        return result;
    }
    finally {
        active = false;
    }
}
export async function request(url, init) {
    const parsed = new URL(url, location.origin);
    if (parsed.pathname === "/api/run" && init?.method === "POST") {
        return compute(JSON.parse(String(init.body)));
    }
    if (parsed.pathname === "/api/latest") {
        const inMemory = Array.from(memory.values()).at(-1);
        if (inMemory)
            return inMemory;
        try {
            const saved = (await allRuns()).sort((a, b) => (b.savedAt ?? 0) - (a.savedAt ?? 0))[0];
            if (saved)
                return saved;
        }
        catch { /* Use an actual saved example if browser storage is disabled. */ }
        return exampleRun();
    }
    if (parsed.pathname === "/api/research") {
        research ??= fetch("/data/research.json").then(async (response) => {
            if (!response.ok)
                throw new Error("Research evidence could not be loaded.");
            return await response.json();
        });
        const bundle = await research;
        const selected = parsed.searchParams.get("case") ?? bundle.default_case;
        if (!bundle.payloads[selected])
            throw new Error("Unknown research case.");
        return bundle.payloads[selected];
    }
    const match = parsed.pathname.match(/^\/api\/runs\/([0-9a-f-]+)\/result$/);
    if (match)
        return findRun(match[1]);
    throw new Error("This operation is not available in the public browser demo.");
}
function csvCell(value) {
    const text = value == null ? "" : String(value);
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
export async function download(runId, resource) {
    const result = await findRun(runId);
    let blob;
    let name;
    if (resource === "config") {
        blob = new Blob([JSON.stringify(result.config, null, 2)], { type: "application/json" });
        name = "configuration.json";
    }
    else if (resource === "csv") {
        const rows = Object.values(result.estimates);
        const keys = Object.keys(rows[0]);
        const csv = [keys.join(","), ...rows.map(row => keys.map(key => csvCell(row[key])).join(","))].join("\r\n");
        blob = new Blob([csv], { type: "text/csv" });
        name = "estimates.csv";
    }
    else if (resource === "zip") {
        if (result.archive_base64) {
            const bytes = Uint8Array.from(atob(result.archive_base64), c => c.charCodeAt(0));
            blob = new Blob([bytes], { type: "application/zip" });
        }
        else {
            const response = await fetch("/data/example.zip");
            if (!response.ok)
                throw new Error("Example archive could not be downloaded.");
            blob = await response.blob();
        }
        name = `options-${runId.slice(0, 8)}.zip`;
    }
    else
        throw new Error("Unknown download format.");
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000);
}
