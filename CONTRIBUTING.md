# Contributing

Bug reports and focused pull requests are welcome. Please do not publish confidential board files
in an issue; use a minimal reproducible board or redact project-specific data.

## Development setup

Use Python 3.10 or newer:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r plugin\requirements.txt -r requirements-dev.txt
```

On Linux or macOS, activate the virtual environment using the platform's usual `bin` path.

## Checks

Run these before opening a pull request:

```powershell
python -m unittest discover -s tests -v
python scripts\build_pcm.py
python scripts\validate_release.py
```

Changes to IPC launch behavior, rendering, or report layout should also be tested manually in
KiCad 10. Explain that manual check in the pull request.

## Project conventions

- Keep package metadata and UI text in English for KiCad repository compatibility.
- Update `CHANGELOG.md` for user-visible changes.
- Change the version only in `plugin/VERSION` and the current entry in `pcm/metadata.json`.
- Never add `download_*` fields to `pcm/metadata.json`; the release workflow generates those for
  the official repository after the ZIP is built.
