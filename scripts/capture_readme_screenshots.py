"""Capture README screenshots from the generated sample report."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROWSER_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def find_browser(explicit: Path | None) -> Path:
    if explicit:
        if explicit.is_file():
            return explicit
        raise FileNotFoundError(f"Browser not found: {explicit}")
    for candidate in DEFAULT_BROWSER_CANDIDATES:
        if candidate.is_file():
            return candidate
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser"):
        if executable := shutil.which(name):
            return Path(executable)
    raise FileNotFoundError("No supported Chromium browser was found")


def capture(browser: Path, source: Path, destination: Path, profile: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "--disable-background-networking",
        "--allow-file-access-from-files",
        "--force-device-scale-factor=1",
        "--window-size=1600,1200",
        "--virtual-time-budget=3000",
        f"--user-data-dir={profile}",
        f"--screenshot={destination.resolve()}",
        source.resolve().as_uri(),
    ]
    completed = subprocess.run(command, check=False, timeout=45)
    if completed.returncode != 0:
        raise RuntimeError(f"Browser exited with status {completed.returncode}")
    for _ in range(50):
        if destination.is_file() and destination.stat().st_size:
            return
        time.sleep(0.1)
    raise RuntimeError(f"Browser did not create {destination}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", type=Path, help="Path to Edge, Chrome, or Chromium")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    report = ROOT / "sample-report" / "index.html"
    html = report.read_text(encoding="utf-8")
    marker = "filterMap();updateDft();\n</script>"
    if marker not in html:
        raise RuntimeError("Could not locate report initialization script")
    dft_html = html.replace(
        marker,
        'filterMap();updateDft();$("pogoPitch").value="2.54";activateTab("dft");'
        'requestAnimationFrame(()=>window.scrollTo(0,0));\n</script>',
        1,
    )
    dft_report = report.with_name(".readme-dft.html")
    dft_report.write_text(dft_html, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_path = Path(temporary)
            capture(
                browser,
                report,
                ROOT / "docs" / "images" / "test-point-report.png",
                temporary_path / "map-profile",
            )
            capture(
                browser,
                dft_report,
                ROOT / "docs" / "images" / "dft-spacing-report.png",
                temporary_path / "dft-profile",
            )
    finally:
        dft_report.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
