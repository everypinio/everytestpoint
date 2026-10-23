# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow semantic versioning.

## [Unreleased]

## [0.2.4] - 2026-10-23

### Changed

- Adopted the permanent KiCad PCM identifier `com.github.everypinio.everytestpoint`.
- Added reproducible package builds, schema validation, cross-platform CI, and tagged releases.
- Through-hole pads on fitted components are now assigned only to the side opposite the
  component; DNP through-hole footprints remain accessible from both sides.

### Added

- Interactive top and bottom test-point maps with CSV and JSON exports.
- Realistic KiCad 3D renders with project solder-mask colors.
- DFT spacing view with selectable pogo-pin pitch and highlighted violations.
- Everypin branding, light and dark logos, Golos Text, revision, and report timestamp.
- KiCad 10 IPC toolbar action and PCM installation package.

[Unreleased]: https://github.com/everypinio/everytestpoint/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/everypinio/everytestpoint/releases/tag/v0.2.4
