# Copyright (c) 2020-2025 Jan Malakhovski <oxij@oxij.org>
#
# This file is a part of `kisstdlib` project.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""`sqlite3` module extensions for using SQLite databases as an application file
format.

See <https://www.sqlite.org/appfileformat.html> for more info.
"""

import errno as _errno
import json as _json
import logging as _logging
import os as _os
import typing as _t

from sqlite3 import *  # pylint: disable=redefined-builtin

import kisstdlib.failure as _kf


def iter_fetchmany(cur: Cursor) -> _t.Iterator[_t.Any]:
    """Iterate over `sqlite3.Cursor` by calling `fetchmany()` instead of
    `fetchone()`.

    My measurements show that in practice, usually, iteration with
    `.fetchmany()` is slower than both implicit fetches via `for a in cur` and
    explicit repeated calls to `.fetchone()`. But when loading data from a
    database (and then using that data to access other data on disk, and both
    the database and the other data are on the same spinning rust drive, then
    using `.fetchmany()` is much faster, because loading a bunch of data all at
    once saves on disk seeks.

    """
    while True:
        chunk = cur.fetchmany()
        if len(chunk) == 0:
            break
        yield from chunk


class DBFailure(_kf.Failure):
    pass


class BlankDB(DBFailure):
    pass


class InvalidDB(DBFailure):
    pass


SettingsType = _t.TypeVar("SettingsType")
SqliteValue: _t.TypeAlias = int | float | str | bytes | None
DictSettings = dict[str, SqliteValue]


class AppDB(_t.Generic[SettingsType]):
    """An application-bound, versioned, `sqlite3` database with an arbitrary
    settings type.

    I.e., this class contains all the boilerplate one usually needs to write to
    open, configure, and use an `sqlite3` database as an application file
    format, store app settings in there, track metadata "dirtyness", do atomic
    version upgrades (with optional old-version backups), accumulate and commit
    changes in batches, etc.
    """

    APPLICATION_ID: int = 0
    MIN_VERSION: int = 1
    MAX_VERSION: int = 1

    db: Connection
    _path: str
    dirty: bool  # whether the metadata is dirty
    _version: int
    _settings: SettingsType

    setup: dict[str, str]

    # `__init__(setup=...)` default value
    SETUP_DEFAULT: dict[str, str] = {}

    # `__init__(setup=...)` value for quick database creation
    SETUP_CREATE = {
        "journal_mode": "DELETE",
        "locking_mode": "EXCLUSIVE",
        "synchronous": "OFF",
    }

    # `__init__(setup=...)` value for EXCLUSIVE mode
    SETUP_EXCLUSIVE = {
        "locking_mode": "EXCLUSIVE",
    }

    # `__init__(setup=...)` value for WAL mode
    SETUP_WAL = {
        "journal_mode": "WAL",
    }

    arraysize: int | None
    _pending: int

    def __init__(
        self,
        path: str,
        default_version: int,
        default_settings: SettingsType,
        setup: dict[str, str] | None = None,
        *,
        backup_before_upgrades: bool = False,
        commit_intermediate: bool = True,
        arraysize: int | None = None,
        **kwargs: _t.Any,
    ) -> None:
        """`APPLICATION_ID` signifies the application which created the database. It
        will be stored in database's `application_id` field. See
        <https://www.sqlite.org/pragma.html#pragma_application_id> for more
        info.

        `version` is the logical version number of database's schema. It will be
        stored in database's `user_version` metadata field. See
        <https://www.sqlite.org/pragma.html#pragma_user_version> for more info.

        `MIN_VERSION` is the oldest supported `version`, not necessarily for
        working with a database at that version, but, at least, for upgrading
        out of it. `MAX_VERSION` is the newest known `version`.

        `SettingsType` is an arbitrary type for the `settings` field. It gets
        serialized to/from `DictSettings`, which gets stored as `_settings`
        table in the database.

        This method does the following:

        - It opens an `sqlite3` database at a given `path`.

        - Then, before doing anything else, even before the first transaction
          gets opened, it uses given `setup` `dict` to execute `PRAGMA`
          statements, in given order, on the underlying `sqlite3.Connection`.

          This is useful for setting `journal_mode`, `locking_mode`,
          `synchronous`, etc. See <https://www.sqlite.org/pragma.html> for more
          info.

        - If the database at `path` exits, this method checks that its
          `APPLICATION_ID` matches and `MIN_VERSION <= version <= MAX_VERSION`,
          or rasises `InvalidDB` exception if it does not.

          If database has no `_settings` table, `setting` is set to
          `default_settings`.

        - Then, if `backup_before_upgrades` is set and upgrades are required,
          backups the old database into `{path}.v{old_version}.bak`.

        - If the database does not exists, this method creates a new database
          with current `APPLICATION_ID`, `version` set to `0` and `setting` set
          to `default_settings`.

        - Then, this method upgrades the database to at least `default_version`
          by calling `upgrade` repeatedly.

          Database creation is an upgrade from `version == 0`.

          If `commit_intermediate` is set, then all `upgrade` steps as well as
          the resulting database state will be `check`ed and then `commit`ed.
          This option is set by default, because this way big upgrades can be
          split into multiple intermediate `version`s, which allows them to be
          interrupted in the middle and then continued from mostly where it left
          off. Disable this option while developing new `upgrade` steps to
          prevent bad states from being `commit`ed to disk.

        - Then, this method runs `check` on the final database state with
          `final` set to `True` (and `commit`s it if `commit_intermediate` is
          set).

        All but the last `check`s can raise `NotImplementedError`, which will
        make this method ignore them (and also skip the following intermediate
        `commit` if `commit_intermediate` is set).

        Specifying `arraysize` sets the default `arraysize` of each newly
        created `sqlite3.Cursor`.

        Other `kwargs` will be given to `sqlite3.connect`.
        """

        if setup is None:
            setup = self.SETUP_DEFAULT

        # pre-init
        self._path = path
        self.setup = setup
        self.arraysize = arraysize
        self._pending = 0

        # sanity checks
        self._check_version(None, default_version, _kf.AssertionFailure)

        # init
        self.logger = _logging.getLogger(f"kisstdlib.AppDB:{hex(id(self))}")

        created = False  # newly created blank database?
        self.dirty = False

        try:
            self.db = connect(path, autocommit=True, **kwargs)  # type: ignore
            cur = self.cursor()

            for k, v in setup.items():
                cur.execute(f"PRAGMA {k}={v}")

            self.db.autocommit = False  # type: ignore

            # create or open the database
            application_id = cur.execute("PRAGMA application_id").fetchone()[0]
            self._version = opened_version = cur.execute("PRAGMA user_version").fetchone()[0]
            tables = set(map(lambda x: x[1], cur.execute("PRAGMA main.table_list").fetchall()))

            if application_id == 0 and opened_version == 0 and len(tables) == 1:
                created = True
                self.dirty = True
            else:
                if application_id not in (self.APPLICATION_ID, 0):
                    # `0` is there to allow prototyping before deciding on `APPLICATION_ID`
                    raise InvalidDB(
                        "`%s`: wrong `application_id`, expected: `%s`, got: `%s`",
                        path,
                        self.APPLICATION_ID,
                        application_id,
                    )
                self._check_version(path, opened_version, InvalidDB)

                # backup before doing anything else
                if backup_before_upgrades and opened_version < default_version:
                    backup_path = path + f".v{opened_version}.bak"
                    self.db.autocommit = True  # type: ignore
                    cur.execute("VACUUM main INTO ?", (backup_path,))
                    self.db.autocommit = False  # type: ignore

                    # NB: ideally, this should happen within the same
                    # transaction so that `opened_version` would still be valid.
                    # I.e. `autocommit` should stay `False`. But sqlite does not
                    # support this.

                    reopened_version = cur.execute("PRAGMA user_version").fetchone()[0]
                    if reopened_version != opened_version:
                        raise _kf.AssertionFailure(
                            "`%s`: version changed while doing backup: %d -> %d",
                            path,
                            opened_version,
                            reopened_version,
                        )

            if "_settings" in tables:
                cur.execute("SELECT name, value FROM _settings")
                self._settings = self.deserialize_settings(self._version, dict(cur))
            else:
                self._settings = default_settings

            if application_id != self.APPLICATION_ID:
                # migrate from `0` in `APPLICATION_ID`
                self.dirty = True

            self.logger.debug(
                f"`%s`: {'created' if created else 'opened'} at version %d with settings of `%s`",
                path,
                self._version,
                str(self._settings),
            )

            # have we checked the current version yet?
            checked = False
            # do we want an intermediate `self.commit()`?
            want_commit = False

            # do upgrades
            while self._version < default_version:
                self.logger.info(
                    "`%s`: upgrading from version %d...",
                    path,
                    self._version,
                )

                if want_commit:
                    if not checked:
                        # ensure the current state is consistent
                        try:
                            self.check(cur, False)
                        except NotImplementedError:
                            pass
                        else:
                            checked = True

                    if checked:
                        # this state should be commited, do it
                        want_commit = False
                        self.commit()

                # upgrade
                prev_version = self._version
                self.upgrade(cur, default_version)

                # ensure the resulting `version` is ok
                self._check_version(path, self._version, _kf.AssertionFailure)
                if self._version <= prev_version:
                    raise _kf.AssertionFailure(
                        "`%s`: bad version upgrade: %d -> %d",
                        path,
                        prev_version,
                        self._version,
                    )

                # set flags
                checked = False
                want_commit = want_commit or commit_intermediate

            # finish up
            if not checked:
                self.check(cur, True)

            if commit_intermediate:
                self.commit()

            self.logger.debug(
                "`%s`: finished init at version %d with settings of `%s`",
                path,
                self._version,
                str(self._settings),
            )
        except:
            self.close()
            if created:
                _os.unlink(path)
            raise

    def close(self) -> None:
        if not hasattr(self, "db"):
            return

        self.logger.debug("`%s`: closed", self._path)
        self.db.close()
        del self.db

    def __del__(self) -> None:
        self.close()

    def _check_version(
        self,
        path: str | None,
        version: int,
        error_factory: _t.Any,
    ) -> None:
        if self.MIN_VERSION <= version <= self.MAX_VERSION:
            return

        if path is None:
            raise error_factory(
                "bad version, expected: `%d <= version <= %d`, got: `%d`",
                self.MIN_VERSION,
                self.MAX_VERSION,
                version,
            )

        raise error_factory(
            "`%s`: bad version, expected: `%d <= version <= %d`, got: `%d`",
            str(path),
            self.MIN_VERSION,
            self.MAX_VERSION,
            version,
        )

    @property
    def path(self) -> str:
        return self._path

    def get_version(self) -> int:
        return self._version

    def set_version(self, value: int) -> None:
        self._version = value
        self.dirty = True

    version = property(get_version, set_version)

    def get_settings(self) -> SettingsType:
        return self._settings

    def set_settings(self, value: SettingsType) -> None:
        self._settings = value
        self.dirty = True

    settings = property(get_settings, set_settings)

    @staticmethod
    def serialize_settings(version: int, data: SettingsType) -> DictSettings:
        """Serialize `SettingsType` to `DictSettings`."""
        raise NotImplementedError()

    @staticmethod
    def deserialize_settings(version: int, data: DictSettings) -> SettingsType:
        """Deserialize `SettingsType` from `DictSettings`."""
        raise NotImplementedError()

    def cursor(self) -> Cursor:
        if self.db is None:
            raise _kf.AssertionFailure("unattached AppDB")

        cur = self.db.cursor()
        if self.arraysize is not None:
            cur.arraysize = self.arraysize
        return cur

    def commit(self) -> None:
        if self.db is None:
            raise _kf.AssertionFailure("unattached AppDB")

        if self.dirty:
            self._check_version(self._path, self._version, _kf.AssertionFailure)
            settings = self.serialize_settings(self._version, self._settings)

            cur = self.cursor()
            cur.execute(f"PRAGMA application_id={self.APPLICATION_ID}")
            cur.execute(f"PRAGMA user_version={self._version}")

            cur.execute("DROP TABLE IF EXISTS _settings")
            cur.execute(
                "CREATE TABLE _settings (name TEXT NOT NULL PRIMARY KEY, value ANY) WITHOUT ROWID, STRICT"
            )
            for k, v in settings.items():
                cur.execute("INSERT INTO _settings VALUES (?, ?)", (k, v))

            cur.close()
        self.db.commit()
        self.dirty = False

    def commit_maybe(self, count: int = 1, max_pending: int = 1024) -> None:
        self._pending += count
        if self._pending > max_pending:
            self.commit()
            self._pending = 0

    def rollback(self) -> None:
        if self.db is None:
            raise _kf.AssertionFailure("unattached AppDB")

        self.db.rollback()

    def upgrade(self, cur: Cursor, target_version: int) -> bool | None:
        """Create or upgrade the database.

        This is where `cur.execute("CREATE TABLE ...", ...)` and/or
        `cur.execute("ALTER TABLE ...", ...)` ond other database upgrade calls
        should go.

        `version` and `settings` will already be set.

        Database creation is an upgrade from `version == 0`.

        The implementation can upgrade `version` to `target_version` in a single
        jump, but it can also do one upgrade step, in which case, this function
        will be called repeatedly with `check` and `commit` calls in-between
        while `version` grows monotonically towards `target_version`.

        Such an implementation can be useful if some of the upgrades are
        computationally expensive and intermediate states should be commited to
        disk. I.e. the implementation can split big upgrades into multiple
        ephemeral `version`s that will still be `commit`ed to disk.

        The implementation MUST NOT call `commit*`. Let the caller handle it
        instead.
        """
        raise NotImplementedError()

    def check(self, cur: Cursor, final: bool) -> None:
        """This is where various integrity checks should go.

        For `version`s which this can not or does not want to check, it should
        raise `NotImplementedError`, which will be handled properly, when such a
        thing is allowed.

        When `final` is set, however, raising an error will abort everything.
        """


class DictSettingsAppDB(AppDB[DictSettings]):
    """The simplest implementation of `DB`, uses `DictSettings` as `SettingsType`
    directly.
    """

    @staticmethod
    def serialize_settings(version: int, data: DictSettings) -> DictSettings:
        return data

    @staticmethod
    def deserialize_settings(version: int, data: DictSettings) -> DictSettings:
        return data


def load_overwritable_settings(
    data: DictSettings, field: str, parser: _t.Callable[[_t.Any], _t.Any]
) -> _t.Any:
    """Load setting from `field` of `data` by parsing them with `parser`.

    Then, if the result is `dict`, use the rest of `data` to perform overwrites.
    """

    value = data[field]
    settings = parser(value)
    if len(data) > 0:
        if not isinstance(settings, dict):
            raise _kf.AssertionFailure("overwriting non-`dict` `SettingsType` is not supported")
        for k, v in data.items():
            if k != field:
                settings[k] = v
    return settings


class JSONSettingsAppDB(AppDB[_t.Any]):
    """A simple implementation of `DB` that allows an arbitrary JSON-serializable
    type as `SettingsType`.

    Internally, it simply `json.dumps` and `json.loads` the settings to/from
    "_json" field of `DictSettings`.
    When loading, if the resulting value is `dict`, it also allows the rest of
    the `_settings` table to be used for simple overwrites.
    """

    @staticmethod
    def serialize_settings(version: int, data: _t.Any) -> DictSettings:
        return {"_json": _json.dumps(data)}

    @staticmethod
    def deserialize_settings(version: int, data: DictSettings) -> _t.Any:
        return load_overwritable_settings(data, "_json", _json.loads)
