# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Also, at the bottom of this file there is a [TODO list](#todo) with planned future changes.

## [v0.0.14] - 2026-11-06

### Added/Changed/Removed/Fixed: Incompatible changes

- `kisstdlib/time.py`:

  - Renamed all `*gmtoff` fields and arguments -\> `tz`.

- `kisstdlib/fs.py`:

  - Renamed:
    - `atomic_unlink` -\> `unlink_file`,
    - `atomic_rename` -\> `rename_file`,
    - `make_file` -\> `unsafe_make_file`,
    - `atomic_make_file` -\> `make_file`,
    - `atomic_write` -\> `write_file`,
    - `atomic_copy2` -\> `clone_file`,
    - `atomic_link` -\> `link_file`,
    - `atomic_symlink` -\> `symlink_file`,
    - `atomic_link_or_copy2` -\> `link_or_clone_file`,
    - `atomic_move` -\> `move_file`.
  - Edited all functions to use `follow_symlinks = False` by default.
  - Reworked all `simulate` arguments into callbacks.
  - Reworked the internals of `Deferred`:
    - Started processing `Deferred.unlink_file` after `Deferred.rename_file`.
    - Removed `Deferred.tmp_file`, since `unlink_file` can do its job now.
    - Renamed `Deferred.sync` -\> `Deferred.flush`.
    - Introduced `on_warning` and `on_error` arguments to `Deferred.flush`.
    - Introduced `cancel_*` methods.
    - Greatly simplified the implementation of `Deferred.flush`.
  - Re-implemented `fsync_file`, allowing it to (attempt to) `fsync` directories on Windows too.
  - Reworked the internals of most functions taking `sync` arguments, solving a bunch of `fsync`-is-out-of-order issues.
    Most notably, reworked `rename_file` to do barrier `fsync`s when needed.
  - Added `simulate` argument support to most of those functions.
  - Added `allow_overwrites`/`exists` arguments to most of them and allow those arguments to take `os.stat_result` inputs, thus making those functions check relevant `path`s with `unchanged_stat` before doing anything.
  - Therefore, replaced `unlink_maybe` with `unlink_file(..., exists = False)`.
  - Removed `fsync_many_files` and `unlink_many`, since these can now be implemented by trivial loops.

- `devscript/test-cli-lib.sh`:

  - Renamed:
    - `ok_stdio2` -\> `ok_stdio`,
    - `any_stdio2` -\> `any_result`,
    - `set_tmpdir` -\> `setup_tests`,
    - `TARGETS` -\> `INCLUDE`,
    - capitalized all other internal variable names, e.g., `errors` -\> `ERRORS`.

### Added/Changed

- `kisstdlib/base.py`:

  - Replaced `noop_` -\> `noop`, `identity_` -\> `identity`, `const_` -\> `const` since multi-argument versions work perfectly fine with new `mypy` versions now.
  - Made `compose(f, g)` propagate all of its resulting arguments to `g`.
  - Introduced `compose_wide` that propagates them to both `f` and `g`, similarly to how `compose_pipe` works.
  - introduced `raise_one` and `raise_all`.

- `kisstdlib/logging_ext.py`:

  - Introduced `log_exception*` functions.

- `kisstdlib/time.py`:

  - Implemented support for `tz: str`, i.e., named times zones, like "America/Los_Angeles".

- `kisstdlib/fs.py`:

  - Introduced:
    - `fsreencode`,
    - `equal_path`,
    - `unchanged_stat`,
    - `describe_file_type`,
    - `copy_file`,
    - `unsafe_write_file`,
    - `unsafe_symlink_file`,
    - `unsafe_copy_symlink`,
    - `unsafe_copy_file`,
    - `unsafe_clone_file`,
    - `unsafe_link_file`.

  - Improved `rename_file` implementation on POSIX a bit.

- `devscript/test-cli-lib.sh`:

  - Introduced `PACKAGE`, `TAG`, and `INPUT` configuration variables to better control the results of `setup_tests`.
  - Introduced `EXCLUDE` configuration variable, as a reverse of `INCLUDE`.
  - Introduced:
    - `should_start`,
    - `abbrev_file`,
    - `diff_files`,
    - `retcode`,
    - `retcode_stdio`,
    - `retcode_fixed_stdio`,
    - `ok_fixed_stdio`,
    - `ok_no_stdio`,
    - `equal_forest_dir`,
    - `to_kill`,
    - `kill_all_to_kill`
    functions.
  - Replaced `die` -\> `error` in all functions.
  - Made `fixed_dir` and `retcode_fixed_stdio` abort with an error when their main commands fail.
  - Made `error` and all of those functions return with non-zero codes on errors.
  - Homogenized implementations of all of those functions.
  - Improve their error messages.
  - The script now `trap`s `SIGINT` and `SIGTERM` to run `exit 1`.

## [v0.0.13] - 2026-09-14

### Added/Changed/Removed/Fixed: Incompatible changes

- `*`: Switched to `python-v3.13`, `black-v25.1.0`, `mypy-v1.20.1`, `pylint-v4.0.6`, edited all the code to pass all the checks.

  `python-v3.13` or later is required now.

- Renamed `kisstdlib/sorted.py` -\> `kisstdlib/collections_ext.py`.

- `kisstdlib/base.py`:

  - Introduced `SupportsCmp`, `SupportsCounting`, and `is_closer`, the latter of which replaced `nearer_to_than`.
  - Dropped `Number` and `AndNumber`.
  - Dropped all other placeholder `TypeVar`s and `ParamSpec`s, since they are no longer needed with the new `python-v3.13` features.
  - Dropped `AVG_MONTH` and `AVG_YEAR`.

- `kisstdlib/itertools_ext.py`:

  - Reworked `count_from_to` -\> `range_`.
  - Dropped `count_`, since normal `count` can do the same thing with the same types now.

- `kisstdlib/collections_ext.py`:

  - Re-worked all the `*SortedIndex` classes and their internals.
    The new versions are more general and better-typed.
  - Most notably, renamed `AbstractSortedIndex` -\> `ABCIndex`, `SortedIndex` -\> `SortedDictIndex`, their methods, and almost everything else related.
  - Introduced `DictIndex`, which `SortedDictIndex` is now a sub-class of.

- `kisstdlib/sqlite3_ext.py`:

  - Simplified the type of `AppDB.upgrade`.
  - Made the name of the settings table of `AppDB` configurable.

- `kisstdlib/fs.py`:

  - Renamed `DeferredSync` -\> `Deferred`.

- `kisstdlib/parsing`:

  - Dropped `unread`, thus making the `Parser`'s buffer immutable.
  - Reworked `leftovers` from property -\> function.
  - Added a bunch more useful functions.
  - Added a bunch of wrappers and function decorators.
  - Improve types and semantics of most existing functions.
  - Renamed most of them.

- `kisstdlib/time.py`:

  - Renamed `TimeStamp` -\> `TimeStamp`, `TimeRange` -\> `TimeRange`.
  - Dropped `TimeValue`.
  - In `TimeStamp` and `TimeRange`, renamed `now` -\> `from_now`.

- `kisstdlib/time.py`: `*.format*`:

  - Introduced `TimeFormatter`, which is a `strftime`-like `string.Formatter`.
  - Reworked everything else to use it, thus making arbitrary `precision`s to work properly in custom `fmt`s.
  - Dropped the special `fmt = "@"` support, since it can be expressed normally now.
  - Reworked `format_org_delta` -\> `format_delta`.
  - Introduced `format3`.
  - Re-implemented `format_org` using `format3`, making it use the time format identical to that of Emacs org-mode.
  - When `format`ting, all these function use the inherent precision of the underlying `Decimal` by default now.
  - Made `.format` print the time zone by default (see below).
  - Introduced `inf_fmt` arguments to all these functions to allow control over how the infinite timestamps should be formatted.

- `kisstdlib/time.py`: `*parse*`:

  - Reworked all `parse_*` functions into static methods of their corresponding classes.
  - Rework their code to use the new `parsing` machinery properly.
  - When parsing, `TimeStamp`s can be bracketed too now.
  - `TimeStamp.parse_iso_like` now admits more time formats, including the one produced by Emacs org-mode.
  - `TimeStamp.parse_absolute` now admits negative values and infinities.
  - From now on, result of `run_parser(TimeRange.parse, "<date1>--<date2>")` no longer includes all of `date2`.
    The old semantics can be recovered by adding ".\$" at the end of that expression (see below).

- `devscript/test-cli-lib.sh`:

  - Renamed `start` -\> `begin`.
  - Re-introduced `start` as a predicate.
  - Make the usage of the `end` bits optional.

### Added: Misc

- `kisstdlib/base.py`:

  - Added more useful constants.
  - Introduced `noop` and `noop_`.

- `kisstdlib/collections_ext.py`:

  - Re-exported some stuff from Python's `collections`.
  - Introduced `LRUCache`.

- `kisstdlib/io/base.py`:

  - Introduced `BytesIOReader` by importing it from `hoardy_web/tool/hoardy_web/source.py`.

- `kisstdlib/{io/base.py, fs.py}`:

  - Added `chunk_size` arguments to `fileobj_data_equals`, `same_file_data`, and `file_data_equals`.

- `kisstdlib/sqlite3_ext.py`:

  - Introduced `SortedSqliteIndex` as a sub-class of `ABCIndex`.

- `kisstdlib/failure.py`:

  - For `CatastrophicFailure` and its sub-classes, introduced `subsume` method and its `__init__` equivalent.

- `kisstdlib/time.py`:

  - `TimeRange` is a `total_ordering` now.

  - Introduced `TimeStamp.gmtoff` and proper support for time zones:

    - Reworked `TimeStamp` to be a `Decimal` with an additional `gmtoff` attribute.
    - Edited all `TimeStamp` methods to propagate that value around properly.
    - Made all `.parse*` and `.format*` take `gmtoff` as an argument:
      - Made all `.parse*` use their `gmtoff` arguments if the input does not specify a time zone and make them set `gmtoff` from the input when it does.
      - Made it possible for `.format` to override `self.gmtoff`, which it now does by default to force user's local time zone by default.
    - Added support for sub-minute time zone formatting to `TimeFormatter`.
    - Made it possible for all `.parse*` functions to be run with time zone parsing disabled.

  - Introduced `TimeFun` and its dependencies.

    `TimeFun` represents a declaratively defined function over `TimeStamp`s.

    E.g., parsing "+1y2m3h" and then applying the result to a `TimeStamp` will move it one year, two months, and three hours forward.

    The list of supported operations is pretty simple, but their compositions can be used to produce rather advanced results.

    For the use cases where `TimeFun` gets applied to `TimeStamp.from_now()` or similar, there's also `TimeFun.parse_human` static method that admits human-readable strings and turns them into the appropriate `TimeFun`s, e.g.:

    - "now" becomes an identity over `TimeStamps`;
    - "today" becomes a rounding to the start of the day;
    - "last week" becomes a rounding to the start of the week followed by "-7d";
    - etc.

  - Generalized `TimeRange.parse` to admit `TimeFun`s and mixes of `TimeStamp`s and `TimeFun`s, which is why now it also takes an additional argument of `now: TimeStamp`.

    As a result, it can now parse and compute `TimeRange`s for expressions like "today", "today-1y--last_week+1d", etc.

    Also, notably, this parser now also admits `.^` and `.$` operations, which shrink the previous time interval into a single point, corresponding to its start or end, respectively.

    Thus, the old behaviour for, e.g., `2024--2025`, previously parsed as `2024-01-01--2026-01-01` and now parsed as `2024-01-01--2025-01-01` (see "Incompatible changes" above), can be recovered with `2024--2025.$`.

  - `TimeRange.parse` now also admits more delimiters, not just "--" between its two parts, when both are specified.

### Fixed: Misc

- `kisstdlib/time.py`:

  - Fixed `TimeRange.delta` to return an actual `Decimal` and not a sub-class.
  - `TimeRange.middle` and `.delta` produce results for all possible ranges now, instead of failing with `decimal.InvalidOperation` for some of them.

- `*`:

  - Fixed some docstring of typos.

## [v0.0.12] - 2025-12-03

### Fixed

- `kisstdlib/fs.py`: `realdir`: Fixed `realdir(".")` to work as expected.

- `kisstdlib/itertools_ext.py`: `nth`: Fixed a bug.

### Added

- `kisstdlib/parsing.py`, `kisstdlib/io/adapter.py`: Implemented `BytesTransformer` and its IO-adapter friends.

- `test/test_basics.py`: Added better tests for `nth`.

- `test/test_parsing.py`, `test/test_io.py`: Added tests for `BytesTransformer` adapters.

### Changed

- `kisstdlib/io/adapter.py`: `UpdateFinalizeReader`: Reordered arguments a bit.

- `kisstdlib/sqlite3_ext.py`: Improved debug messages.

## [v0.0.11] - 2025-03-30

### Added

- `kisstdlib.fs`:  introduced `realdir`.

- `kisstdlib.io.adapter`: imported from `hoardy-adb/hoardy_adb/__main__.py`, improved a bit.

### Removed

- `kisstdlib.argparse_ext`: Removed `store_map` and `append_map`.

  These can be implemented with mainstream `argparse` by simply setting `type=func`.

### Changed

- Updated for `mypy v1.14.1`.

- `kisstdlib.fs`: `setup_fs`: put `pid` in front of `prog`.

## [v0.0.10] - 2025-03-17

### Added

- `kisstdlib.signal_ext`: Introduced `GentleSignalInterrupt` simplifying the API usage a bit.

- `kisstdlib.base`: Now re-exports `partial` and `partialmethod`.

- `kisstdlib.string_ext`: Introduced `path_escaper` and related singletons.

- `kisstdlib.logging_ext:ANSILogHandler`: Simplified the API by merging `rollback` functionality into `flush`.

- `kisstdlib.fs`:

  - Introduced `atomic_unlink`.

  - Introduced `setup_fs`, making temp file suffixes configurable.

    Also, `kisstdlib:setup_kisstdlib` now runs this function too.

### Fixed

- `kisstdlib.signal_ext`: From now on, `delay_signal_handler` will flush delayed signals when raising `SignalInterrupt`.

  This prevents `raise_first_delayed_signal` and `raise_delayed_signals` from raising them again, which was a bug.

- `kisstdlib.io.stdio`: Fixed `printf` to count implicit eols properly.

- `kisstdlib.fs`:

  - `iter_subtree`: Fixed error format.

  - `atomic_make_file`: Added `fsync` before `rename`, which should have been there.

- `kisstdlib:run_kisstdlib_main`: Now handles `BrokenPipeError`s when finishing up.

### Changed

- `devscript/test-cli-lib.sh`: Improved a bit.

- `kisstdlib.argparse_ext.py`:

  - Renamed and registered `OptionallyMarkdownHelpAction` as `help_omd`, similarly to how `argparse` does it.

  - Introduced `store_map` and `append_map` actions.

    Which do the same thing as `store` and `append`, but map values with a given function.

- `kisstdlib.fs`:

  - Replace `fsdecode_maybe` and `fsencode_maybe` with imports from `os`.

    Those functions have this functionality too.

  - `DeferredSync`:

    - Renamed `commit` -\> `sync`, `finish` -\> `flush`.

    - Action deference can now be optional, i.e. `DeferredSync` can now be used to only defer the `fsync` alone.

  - `atomic_*`:

    - Renamed `dsync` arguments -\> `sync`, now allowing them to be `bool`s.

      I.e., added no-`fsync`/async mode to all of those functions.

    - Added `prog` program name and its `pid` to temp file suffixes.

      Though, it's configurable via `setup_fs`.

- `kisstdlib:setup_kisstdlib`: Simplified the API a bit.

  Users should now call `setup_delay_signals` themselves if they need non-default `signals`.

## [v0.0.9] - 2025-03-10

### Changed (1)

- Renamed `kisstdlib.argparse.better` module -\> `kisstdlib.argparse_ext`.

- Renamed `kisstdlib.util` module -\> `kisstdlib.base`.

- Renamed `kisstdlib.logging` module -\> `kisstdlib.logging_ext`.

- `kisstdlib.base`:

  - Renamed `(In|Out|Extra)Type` -\> `(A|B|E)Type`.
  - Added more placeholder types, similarly named.
  - Re-imported `Decimal` here.
  - Moved `NumericType` here.
  - Renamed `NumericType` -\> `AnyNumber`.
  - Moved `BytesLike` and byte sizes here.
  - Renamed `str_Exception` -\> `get_traceback`, generalized it a bit.
  - Renamed `map_optionals` -\> `map_optional2list`.
  - Generalized `compose_*calls` into a single `compose_pipe`.
  - Switched to using positional-only parameters where appropriate.

- `kisstdlib.fs`:

  - Renamed `walk_orderly` -\> `iter_subtree`, improved its type.
  - Renamed `describe_walk` -\> `describe_forest`.
  - Improved and simplified the API of `describe_forest`.
  - Renamed `fsync_path` -\> `fsync_file`.
  - Renamed `fsync_many_paths` -\> `fsync_many_files`.
  - Renamed `unlink_many_paths` -\> `unlink_many`
  - Improved the behaviour of `unlink_many` and `fsync_many_files`.
  - Added `makedirs` arguments to all relevant functions.

- `kisstdlib.sorted:SortedIndex`:

 - Generalized it into an `AbstractSortedIndex` with the original `SortedIndex` as its implementation.
 - Renamed all internal API methods to `internal_*`.

- `kisstdlib.io.wrapper:TIOWrappedWriter`:

  - From now on, it allows `eol` to be `str`.
  - Improved it a bit.

- `kisstdlib.io.stdio`:

  - Edited it to play nicely with `sys.std(in|out|err)`.

- `kisstdlib.logging_ext`:

  - Renamed `CountHandler` -\> `LogCounter`.
  - In `LogCounter`:
      - Switched to inheriting from `Handler` instead, for thread safety.
      - From now on, it will count everything below `INFO` as `debugs`.

### Added (1)

- `kisstdlib.base`:

  - Introduced `Number` type with a bunch of operations for it.
  - Introduced some more constants.
  - Introduced `Missing` and `MISSING`.
  - Introduced `identity_`, `const`, `const_`.
  - Introduced `Maybe`, `maybe`, `map_maybe`, `map_maybe2list`.
  - Introduced `Either`, `either`, `map_left`, `map_right`.
  - Introduced `optional`, `optional2list`.
  - Introduced `fst`, `snd`.
  - Introduced `singleton`, `optlist`, `optslist`.
  - Introduced `first_def` and `first_ok`.
  - Introduced `flat_exceptions`.

- `kisstdlib.string_ext`:

  - Introduced the module.
  - Introduced `abbrev`.
  - Introduced `StringLexer`, which is a simple parser generator for simple string lexing syntaxes.
  - Introduced `escaper`, `escape`, `unescape`, which do `lex`-style string processing.
  - Introduced `quoter`, `url_quote`, `url_unquote`, which do what similar `urllib.parse` functions do, but faster, and with more options.
  - Introduced a bunch of related constants.

- `kisstdlib.fs`:

  - Introduced `same_file_data` and `same_symlink_data`.
  - Added `sep` and `sepb`.
  - Introduced `hash_file` and `sha256_file`.

- `kisstdlib.itertools_ext`:

  - Introduced the module with a bunch of commonly useful iteration-related stuff.
  - Introduced `diff_sorted`.

- `kisstdlib.time:Timestamp`

  - Implemented `__add__` and `__sub__`.

- `kisstdlib.sorted:AbstractSortedIndex`, `kisstdlib.sorted:SortedIndex`:

 - In `internal_from_to`:
     - Added support for reverse walking.
     - added support for inclusion and exclusion of bounds.

 - Introduced `internal_from_to_step` which adds `step`ping support to any `internal_from_to`.
 - Introduced `iter_range` which adds `predicate` support to `internal_from_to_step`.
 - Introduced a bunch of other convenience functions.

- `kisstdlib.sqlite3_ext`:

  - Introduced the module with a bunch of commonly useful `sqlite3`-related stuff.

- `kisstdlib.signal_ext`:

  - Introduced the module with a bunch of stuff useful for signal handling.

- `kisstdlib.getpass_ext`:

  - Introduced the module with a bunch `getpass`-related stuff.

- `kisstdlib.io.wrapper:TIOWrappedWriter`:

  - Implemented ANSI TTY Escape Sequences support, making a pretty nice API for it.
  - Added ANSI box and wrapped text drawing.
  - Introduced `terminal_size` API.

  Also, note that `TIOWrappedWriter`, by default, will automatically fallback to non-ANSI plain-text mode when the output is not a TTY of when `NO_COLOR=1` environment variable is set.

  Also, those newly introduced `ansi_*` API functions fallback to plain-text output when ANSI mode is disabled in a way that is designed to work pretty well with very little care taken in the code that uses them.

  I.e. you can just color things, draw boxes, scroll text around, and etc without care, and it will make the output readable in plain-text mode for you for free.

- `kisstdlib.io.stdio`:

  - Introduced `setup_stdio`.
  - Introduced `printf` and `printf_err` with ANSI TTY color support.

- `kisstdlib.logging_ext`:

  - Introduced `ANSILogHandler`, which use `printf` to render the log very prettily on an ANSI TTY.
  - Introduced `die`.
  - Introduced `setup_logging`.
  - Re-exported common logging things from `logging`.

### Removed

- `kisstdlib.fs`:

  - Removed `describe_path`, `describe_forest` is simple enough now.

- `kisstdlib.base`:

  - Replaced `first` with a more general version in `itertools_ext`.

### Fixed

- `kisstdlib.fs:iter_subtree`:

  - From now on it will sort directories as if they have `os.path.sep` after their name.

    Otherwise, `list(map(first, iter_subtree(..., include_directories=False)))` won't be sorted.

    This was broken since 730b1422ea6714349693163f6ae9965a80c00c5d.

    Also, added those separators to the outputs of `describe_forest`.

- `kisstdlib.failure:CatastrophicFailure`:

  - Implemented `__repr__`.

- `kisstdlib.sorted`:

  - Fixed a bug in `internal_from_nearest` found by tests.

- `kisstdlib.argparse_ext`:

  - In `BetterArgumentParser`, fixed it to properly format subparser headers to arbitrary `depth`.

### Changed (2)

- `kisstdlib.argparse_ext`:

  - Switched to using `kisstdlib.io.stdio` and `kisstdlib.logging_ext`.
  - Improved and simplified Markdown formatting code.
  - Simplified `BetterArgumentParser.format_help`, make it play better with default `argparse` things.
  - Made `MarkdownBetterHelpFormatter` produce proper Markdown headers independent of `width`.
  - Improved `BetterArgumentParser` defaults.

### Added (2)

- `kisstdlib.argparse_ext`:

  - Introduced `OptionallyMarkdownHelpAction`.
  - Implemented `--help` and `--markdown` directly in `BetterArgumentParser`.
  - Introduced `make_argparser_and_run`.

- `kisstdlib`:

  - Introduced `setup_kisstdlib` and `run_kisstdlib_main`.
  - Re-exported all the commonly useful things.

- Examples:

  - Added a bunch of new examples.

- Tests:

  - Added a bunch more `./test/*` unit tests.
  - Added `./test-example.sh` with fixed-output tests testing that examples produce the same results between versions.

### Changed (3)

- Renamed `describe-dir` script -\> `describe-forest`.

- `describe-forest`:

  - Improved `describe-forest--help`.
  - Added `describe-forest --version`.
  - Added more command-line options.
  - Improved output format.

- `test-cli-lib.sh`:

  - Added a bunch more functions there.
  - Generalized and simplified it all.
  - Improved logging.

- `*`:

  - Improved documentation and docstrings.

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

[v0.0.14]: https://github.com/oxij/kisstdlib/compare/v0.0.13...v0.0.14
[v0.0.13]: https://github.com/oxij/kisstdlib/compare/v0.0.12...v0.0.13
[v0.0.12]: https://github.com/oxij/kisstdlib/compare/v0.0.11...v0.0.12
[v0.0.11]: https://github.com/oxij/kisstdlib/compare/v0.0.10...v0.0.11
[v0.0.10]: https://github.com/oxij/kisstdlib/compare/v0.0.9...v0.0.10
[v0.0.9]: https://github.com/oxij/kisstdlib/compare/v0.0.8...v0.0.9
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
