"""Reuse an explicitly supplied installed Electron runtime; never download or copy user data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def prepare(runtime, python, destination, scraper=None):
    desktop = Path(__file__).resolve().parent
    repo = desktop.parent
    runtime, python, destination = Path(runtime).resolve(), Path(python).resolve(), Path(destination).resolve()
    if destination != desktop / "local-runtime":
        raise ValueError("Destination must be this checkout's desktop/local-runtime")
    if runtime == destination or runtime in destination.parents or destination in runtime.parents:
        raise ValueError("Runtime source and destination must be separate")
    if not (runtime / "ProspectOS.exe").is_file() or not (runtime / "LICENSES.chromium.html").is_file():
        raise ValueError("Supply an existing ProspectOS Electron Windows runtime")
    if not python.is_file() or not (repo / "frontend/dist/index.html").is_file():
        raise ValueError("Python and built frontend are required")
    scraper_path = Path(scraper).resolve() if scraper else None
    if scraper_path and (not scraper_path.is_file() or scraper_path.name != "google-maps-scraper.exe"):
        raise ValueError("Supply the existing google-maps-scraper.exe explicitly")
    subprocess.run([str(python), "-c", "import flask, waitress, requests; import sqlite3"], check=True)
    destination.mkdir(parents=True, exist_ok=True)
    # Refuse unknown resources instead of launching an old app.asar or updater.
    resources = destination / "resources"
    if resources.exists() and any(p.name != "app" for p in resources.iterdir()):
        raise ValueError("Unexpected resources in destination; choose a fresh checkout")
    provenance = []
    for item in runtime.iterdir():
        if item.name == "resources":
            continue
        target = destination / item.name
        if item.is_dir():
            if item.name != "locales":
                continue
            shutil.copytree(item, target, dirs_exist_ok=True)
        elif item.is_file():
            shutil.copy2(item, target)
            with item.open("rb") as stream:
                provenance.append({"file": item.name, "sha256": hashlib.file_digest(stream, "sha256").hexdigest()})
    appdir = resources / "app"
    shutil.copytree(desktop / "local", appdir, dirs_exist_ok=True)
    shutil.copy2(desktop / "prospectos.ico", appdir / "prospectos.ico")
    data, validation = desktop / "local-data", desktop / "local-validation"
    data.mkdir(exist_ok=True)
    validation.mkdir(exist_ok=True)
    config = {"backend": str(repo / "backend"), "python": str(python), "data": str(data), "validation": str(validation)}
    if scraper_path:
        scraper_target = repo / "backend/google-maps-scraper.exe"
        if scraper_path != scraper_target:
            shutil.copy2(scraper_path, scraper_target)
        with scraper_target.open("rb") as stream:
            provenance.append({"file": "backend/google-maps-scraper.exe", "sha256": hashlib.file_digest(stream, "sha256").hexdigest()})
    (appdir / "local-config.json").write_text(json.dumps(config, indent=2), encoding="utf8")
    (validation / "runtime-provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf8")
    return str(destination / "ProspectOS.exe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--scraper", help="Optional existing local Maps executable; copied only, never executed")
    args = parser.parse_args()
    print(prepare(args.runtime, args.python, Path(__file__).resolve().parent / "local-runtime", args.scraper))
