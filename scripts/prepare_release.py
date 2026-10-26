"""Build a reviewed, checksummed source archive without invoking Git or publishing."""

import hashlib
import json
import re
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    ".gitignore",
    ".env.example",
    "reports/experiments/.gitkeep",
}
DIRECTORIES = (
    "src",
    "app",
    "configs",
    "tests",
    "docs",
    "reports/published",
    "reports/figures",
    ".github",
    "scripts",
    "LICENSES",
)
BLOCKED = {
    "__pycache__",
    "node_modules",
    ".venv",
    ".bootstrap",
    ".python",
    ".uv-cache",
    ".npm-cache",
    ".browsers",
    ".git",
    "release",
    ".pytest_cache",
    ".ruff_cache",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def candidates():
    files = [ROOT / name for name in TOP_FILES]
    files += [
        p
        for directory in DIRECTORIES
        for p in (ROOT / directory).rglob("*")
        if p.is_file()
        and not any(part in BLOCKED for part in p.relative_to(ROOT).parts)
        and p.name != ".DS_Store"
        and p.suffix not in {".pyc", ".pyo"}
    ]
    return sorted(set(files), key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    evidence = json.loads((ROOT / "reports/published/publication_index.json").read_text())
    for group in evidence.values():
        for item in group["copies"]:
            path = (ROOT / item["path"]).resolve()
            if not path.is_relative_to(ROOT) or digest(path.read_bytes()) != item["sha256"]:
                raise ValueError("published research evidence failed checksum validation")
    files = candidates()
    records = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if not path.exists() or path.is_symlink():
            raise ValueError(f"missing or symlinked release file: {relative}")
        data = path.read_bytes()
        if len(data) > 25_000_000:
            raise ValueError(f"unexpected large file: {relative}")
        if path.suffix in {".py", ".ts", ".js", ".json", ".md", ".html", ".css", ".yml"}:
            text = data.decode()
            if re.search(r"(?:/Users/|/home/)[A-Za-z0-9_.-]+/", text):
                raise ValueError(f"personal absolute path in public source: {relative}")
            if re.search(
                r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)",
                text,
            ):
                raise ValueError(f"credential-like content in public source: {relative}")
        records.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
    manifest = {
        "schema_version": "1.0",
        "version": version,
        "license": "MIT",
        "publication_state": "prepared_not_published",
        "files": records,
    }
    destination = ROOT / "release"
    destination.mkdir(exist_ok=True)
    target = destination / f"monte-carlo-options-v{version}-source.zip"
    prefix = f"monte-carlo-options-{version}"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(
                f"{prefix}/{path.relative_to(ROOT).as_posix()}", date_time=(2026, 10, 25, 0, 0, 0)
            )
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
        archive.writestr(f"{prefix}/RELEASE_MANIFEST.json", json.dumps(manifest, indent=2))
    checksum = digest(target.read_bytes())
    (target.with_suffix(target.suffix + ".sha256")).write_text(f"{checksum}  {target.name}\n")
    (destination / "source-manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for item in records:
            assert digest(archive.read(f"{prefix}/{item['path']}")) == item["sha256"]
    print(
        json.dumps(
            {
                "archive": str(target.relative_to(ROOT)),
                "files": len(files),
                "compressed_bytes": target.stat().st_size,
                "sha256": checksum,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
