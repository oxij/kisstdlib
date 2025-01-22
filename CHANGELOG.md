# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Also, at the bottom of this file there is a [TODO list](#todo) with planned future changes.

## [v0.0.8] - 2025-01-22

### Changed

- Split tests into `test/*` directory to remove them from resulting installations.
- Greatly improved syncing behaviour of `DeferredSync` and its `atomic_*` friends.
- `atomic_move` now has `follow_symlinks = False` by default, like `mv(1)` does.

### Added

- Imported and generalized a bunch of stuff from `hoardy-web`.
- Added a tests for `DeferredSync` and its `atomic_*` friends.

### Fixed

- `walk_orderly`: fixed `include_files` filtering.

## [v0.0.7] - 2025-01-17

### Fixed

- Fixed `fsync`ing of directories on Linux.
  The previous Windows support fix broke it.

## [v0.0.6] - 2025-01-17 [YANKED]

### Changed

- Improved the API a bit.
- Improved error handling.

### Fixed

- Improved Windows support.

## [v0.0.5] - 2025-01-13

### Added

- Imported a bunch of code from `hoardy-*` projects.

### Changed

- Improved newly imported code quite a bit.
- Formatted code using `black`.
- Fixed issues found by `pylint`.
- Improved error handling.
- Improved the API a bit.

### Fixed

- Improved Windows support.

## [v0.0.4] - 2024-11-09

### Changed

- `walk_orderly`:

    - Improved the API a bit.
    - It works on Windows now.
    - Improved performance.

## [v0.0.3] - 2024-04-02

### Changed

- Improved the API a bit.

## [v0.0.2] - 2024-02-22

### Added

- `walk_orderly`:

  - Added `order_by` argument.

## [v0.0.1] - 2023-10-26

### Added

- Initial release.

[v0.0.8]: https://github.com/oxij/kisstdlib/compare/v0.0.7...v0.0.8
[v0.0.7]: https://github.com/oxij/kisstdlib/compare/v0.0.6...v0.0.7
[v0.0.6]: https://github.com/oxij/kisstdlib/compare/v0.0.5...v0.0.6
[v0.0.5]: https://github.com/oxij/kisstdlib/compare/v0.0.4...v0.0.5
[v0.0.4]: https://github.com/oxij/kisstdlib/compare/v0.0.3...v0.0.4
[v0.0.3]: https://github.com/oxij/kisstdlib/compare/v0.0.2...v0.0.3
[v0.0.2]: https://github.com/oxij/kisstdlib/compare/v0.0.1...v0.0.2
[v0.0.1]: https://github.com/oxij/kisstdlib/releases/tag/v0.0.1

# TODO

- Publish the rest of this.
