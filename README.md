# Every Test Point

Every Test Point is a KiCad 10 IPC plugin that turns the open PCB into a self-contained,
interactive test-point report.

One click in PCB Editor creates `<board-name>-testpoints/` next to the board with:

- `index.html` — searchable top/bottom board map and test-point table;
- `testpoints.csv` and `testpoints.json` — complete structured exports;
- `jigsapp-testpoints.csv` — TheJigsApp-compatible probe table;
- `images/top.png` and `images/bottom.png` — realistic KiCad 3D renders.

The extractor accepts both KiCad's pad fabrication property `Test point pad` and conventional
single-pad `TP…` footprints. Through-hole probes are shown on both sides.

## Install for development

1. Enable **Preferences → Plugins → Enable KiCad API** in KiCad 10.
2. Copy the `plugin` directory to the KiCad IPC plugin directory and rename it to
   `every-test-point`:
   - Windows: `%USERPROFILE%\Documents\KiCad\10.0\plugins\every-test-point`
   - Linux: `~/.local/share/KiCad/10.0/plugins/every-test-point`
   - macOS: `~/Documents/KiCad/10.0/plugins/every-test-point`
3. Restart PCB Editor. KiCad creates the plugin virtual environment and installs the declared
   Python dependencies automatically.
4. Open a board and run **Generate test-point map** from the PCB Editor toolbar or plugin menu.

The generated HTML is opened in the default browser. The board is saved before rendering so the
report always matches the visible editor state.

The renderer automatically measures the opaque Edge.Cuts surface inside each PNG. Marker
coordinates are mapped into that measured rectangle, excluding KiCad camera padding, shadows,
and any 3D models that extend beyond the board edge.

## Command line

The report generator can also be tested without the KiCad IPC connection:

```powershell
python -m plugin.everytestpoint.cli path\to\board.kicad_pcb --no-render
```

Remove `--no-render` to use `kicad-cli pcb render`.

## Build a PCM archive

```powershell
python scripts\build_pcm.py
```

The archive is written to `dist/every-test-point-0.1.0.zip` with the KiCad 10 PCM layout.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Design notes

KiCad 10's IPC API is used to identify and save the open board and to locate `kicad-cli`.
Test-point extraction intentionally reads the serialized `.kicad_pcb` S-expression: stable
`kicad-python` releases for KiCad 10 do not yet expose every pad fabrication-property field.
The parser never executes board content.

The original JigsApp plugin inspired the fabrication-property convention and compatible CSV
columns: <https://github.com/TheJigsApp/kicad-testpoints-pcm>.

## License

MIT. See `LICENSE`.
