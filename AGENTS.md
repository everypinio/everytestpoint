# AGENTS.md

This file applies to the entire repository.

## Project overview

Every Test Point is a Python IPC plugin for KiCad 10. It extracts test points from the open PCB,
renders both board sides with `kicad-cli`, and generates a self-contained interactive HTML report
plus CSV and JSON exports.

The plugin must continue to work on Python 3.10 and on Windows, Linux, and macOS.

## Repository map

- `plugin/generate_report.py` — KiCad IPC entry point.
- `plugin/everytestpoint/pcb.py` — `.kicad_pcb` extraction and test-point semantics.
- `plugin/everytestpoint/render.py` — KiCad CLI rendering and image geometry detection.
- `plugin/everytestpoint/report.py` — report assets, exports, HTML, CSS, and JavaScript.
- `plugin/everytestpoint/dft.py` — same-side probe-pair spacing calculations.
- `plugin/everytestpoint/sexpr.py` — non-executing KiCad S-expression parser.
- `tests/` — unit and release/package tests.
- `scripts/build_pcm.py` — reproducible KiCad PCM archive builder.
- `scripts/validate_release.py` — manifest, schema, and archive validation.
- `docs/RELEASING.md` — maintainer release procedure.

Treat `dist/`, `sample-report/`, and generated `*-testpoints/` directories as build artifacts. Do
not commit them.

## Development workflow

Use Python 3.10 or newer. Install both runtime and development dependencies:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r plugin\requirements.txt -r requirements-dev.txt
```

Before finishing a change, run the checks relevant to it. Before a release-related change, run all
three:

```powershell
python -m unittest discover -s tests -v
python scripts\build_pcm.py
python scripts\validate_release.py
```

For changes to IPC startup, rendering, coordinate mapping, packaging, toolbar integration, or the
report UI, also test the generated ZIP manually in KiCad 10. Verify the toolbar icon, top and
bottom renders, marker alignment, exports, and DFT tab.

The command-line generator can be used without a live KiCad connection:

```powershell
python -m plugin.everytestpoint.cli path\to\board.kicad_pcb --no-render
```

Remove `--no-render` when `kicad-cli` is available and the render path is under test.

## Implementation rules

- Keep runtime code compatible with Python 3.10. Do not depend on a newer language feature.
- Keep the report self-contained and usable from a local `file://` URL. Do not add CDN or network
  dependencies.
- Parse board input as data only. Never evaluate or execute content from a KiCad project.
- Preserve full floating-point precision during geometry calculations; round only exported or
  displayed values.
- Keep board coordinates, image coordinates, and mirrored bottom-view coordinates explicitly
  separated. Marker placement must use the measured board rectangle inside the rendered image,
  not the complete PNG dimensions.
- A through-hole pad on a fitted component is probe-accessible only from the side opposite the
  component. A through-hole pad on a DNP footprint is accessible from both sides.
- Probe distances are center-to-center and are calculated only for pairs that share an accessible
  fixture side.
- Keep package metadata and user-facing UI text in English for KiCad repository compatibility.
- Add or update focused tests for behavior changes. Update `CHANGELOG.md` for user-visible changes.
- Do not change release versions opportunistically. When preparing a release, update
  `plugin/VERSION` and the current version entry in `pcm/metadata.json` together.
- Do not add `download_*` fields to the embedded `pcm/metadata.json`; release tooling generates
  those fields for official-repository metadata.

## Packaging and assets

`scripts/build_pcm.py` includes every file under `plugin/` in the installable archive. Keep runtime
assets there and avoid adding development-only files to that directory.

The Golos Text font is distributed under the SIL Open Font License. Keep
`plugin/everytestpoint/GolosText-OFL.txt` alongside the font in all packages. Everypin logos and
icons are project assets; do not replace or relicense them without maintainer approval.

## Third-party compatibility

This project is an independent implementation. The fabrication-property convention and the
optional JigsApp-compatible CSV schema were informed by
`https://github.com/TheJigsApp/kicad-testpoints-pcm`, but its source code is not included here.

Do not copy code from GPL/LGPL KiCad plugins into this MIT-licensed repository. If third-party code
or assets are intentionally introduced, preserve their notices, document their origin and license,
and verify license compatibility before committing them. Interoperability field names and file
formats should remain isolated from implementation details and covered by tests.

## Change discipline

- Preserve unrelated user changes in the worktree.
- Prefer small, reviewable patches over broad rewrites.
- Do not commit secrets, private board files, customer data, or generated reports containing such
  data. Use minimal synthetic fixtures for tests.
- Keep the permanent package identifier `com.github.everypinio.everytestpoint` unchanged.
- Follow `docs/RELEASING.md` for tags and releases; a release tag must be exactly
  `v<plugin/VERSION>` and point to a commit on `main`.
