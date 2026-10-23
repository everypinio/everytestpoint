# Releasing Every Test Point

The release process produces a KiCad 10 PCM archive, a SHA-256 checksum, and a second metadata
file suitable for submission to the official KiCad add-on repository.

## Prepare the release

1. Choose the version and update both `plugin/VERSION` and the first version entry in
   `pcm/metadata.json`.
2. Change the metadata status from `development` to `testing` or `stable` only when that accurately
   describes the release.
3. Move completed notes from `Unreleased` into a dated version section in `CHANGELOG.md` and add a
   new empty `Unreleased` section.
4. Run:

   ```powershell
   python -m pip install -r plugin\requirements.txt -r requirements-dev.txt
   python -m unittest discover -s tests -v
   python scripts\build_pcm.py
   python scripts\validate_release.py
   ```

5. Install the generated ZIP through **Plugin and Content Manager → Install from File** on a clean
   KiCad 10 profile. Verify the toolbar icon, report generation, both board renders, and DFT tab.
6. Commit the release changes and merge them into `main`. Wait for the CI workflow to pass.

## Publish on GitHub

Create and push an annotated tag that exactly matches `v` plus `plugin/VERSION`:

```powershell
$version = Get-Content plugin\VERSION
git tag -a "v$version" -m "Every Test Point $version"
git push origin "v$version"
```

The Release workflow rejects a mismatched tag, reruns all tests, validates both KiCad schemas,
builds the package, and creates a GitHub release with these assets:

- `every-test-point-<version>.zip` — package users install in KiCad;
- `every-test-point-<version>.zip.sha256` — integrity checksum;
- `metadata.repository.json` — metadata with the final URL, SHA-256, and sizes.

Do not replace the ZIP asset after publication. Any source change requires a new version and tag.

## Submit to the official KiCad repository

The permanent package identifier is `com.github.everypinio.everytestpoint`.

1. Fork [KiCad's package metadata repository](https://gitlab.com/kicad/addons/metadata).
2. Create `packages/com.github.everypinio.everytestpoint/metadata.json` in that repository using
   the released `metadata.repository.json` asset. Copy this repository's `pcm/icon.png` into the
   same directory. For later releases, add the new version object to the existing official
   metadata and preserve all previous version entries.
3. Confirm its `download_url` is publicly accessible and its `download_sha256` matches the release
   ZIP.
4. Optionally run KiCad's `python tools/packager.py` helper in the metadata repository for the same
   checks its CI performs.
5. Push a branch to your GitLab fork and wait for both validation and build jobs to pass. The build
   log provides a temporary PCM repository; add it to KiCad and install the plugin from there.
6. Open a merge request to the KiCad metadata repository.

The `download_*` fields belong only in the metadata repository copy. They must not be added to the
`metadata.json` embedded in the ZIP.

## Existing development installs

Early development packages used `com.everypin.every-test-point`. KiCad treats the permanent ID as
a different plugin. Remove the old package once from Plugin and Content Manager before installing
a package built from this repository.
