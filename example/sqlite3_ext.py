#!/usr/bin/env python3
#
# Copyright (c) 2025 Jan Malakhovski <oxij@oxij.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""Some `kisstdlib.sqlite3_ext` examples/tests."""

import logging as _logging
import os as _os
import os.path as _op
import typing as _t

import pytest

from kisstdlib.failure import *
from kisstdlib.sqlite3_ext import *  # pylint: disable=redefined-builtin


class DummyDB(DictSettingsAppDB):
    """A very simple example AppDB."""

    APPLICATION_ID = 1
    MIN_VERSION = 0
    MAX_VERSION = 6

    def upgrade(self, cur: Cursor, target_version: int) -> None:
        if self.settings.get("forbidden", False):
            # this operation is currently forbidden, used for testing below
            raise RuntimeError("forbidden")

        if self.version == 0:
            # init
            cur.execute("CREATE TABLE test (id INTEGER PRIMARY KEY NOT NULL)")

        self.version += 1

        # if at version 6, mark as broken
        if target_version == 6:
            self.settings["broken"] = True

    def check(self, cur: Cursor, final: bool) -> None:
        if self.settings.get("broken", False):
            # this should fail to check, used for testing below
            raise RuntimeError("bad")


class NotDummy(DummyDB):
    """The same thing, but with a different `APPLICATION_ID`."""

    APPLICATION_ID = 2


def test_DB(tmp_path: str) -> None:
    path = _op.join(tmp_path, "test.db")
    try:
        default_settings: DictSettings = {"name": "value", "default": "yes"}
        non_default_settings: DictSettings = {"default": "not"}

        # for illustrative purposes, always start in WAL mode
        setup = AppDB.SETUP_WAL

        # newly created databases starts with
        dummy = DummyDB(path, 1, default_settings, setup)
        # `version` set to (at least) `default_version`
        assert dummy.version == 1
        # `settings` set to `default_settings`
        assert dummy.settings == default_settings
        # everything written to disk
        assert not dummy.dirty
        # and a transaction open
        assert dummy.db.in_transaction
        # so, a commit is needed to save it all
        dummy.commit()
        dummy.close()

        # doing the same with `commit_intermediate` will leave all changes uncommited
        dummy = DummyDB(path + ".temp", 1, default_settings, setup, commit_intermediate=False)
        assert dummy.dirty
        dummy.close()

        # i.e., in the case of database creation, it will leave the database
        # completely empty
        dummy = DummyDB(path + ".temp", 0, {"forbidden": True}, setup, commit_intermediate=False)
        assert dummy.version == 0
        dummy.close()

        # but `commit_intermediate=False` setting exists to help in developing
        # new `upgrade` steps
        #
        # also, note that openinng with `default_version = 0` and
        # `commit_intermediate=False` will disable all `upgrade`s and `commit`s

        # newly created databases that fail to init (by either `upgrade` or
        # `check` failing) will be cleaned up after
        with pytest.raises(RuntimeError) as exc_info:
            dummy = DummyDB(path + ".trash", 1, {"forbidden": True}, setup)
        _logging.debug("%s", repr(exc_info.value))
        assert not _op.exists(path + ".trash")

        with pytest.raises(RuntimeError) as exc_info:
            dummy = DummyDB(path + ".trash", 1, {"broken": True}, setup)
        _logging.debug("%s", repr(exc_info.value))
        assert not _op.exists(path + ".trash")

        # for existing databases, `default_settings` gets ignored completely
        dummy = DummyDB(path, 1, non_default_settings, setup)
        # old `settings` persist
        assert dummy.settings == default_settings
        # and they usually start clean (unless some upgrades happened and
        # `autocommit_upgrades = False` or `APPLICATION_ID` was just assigned)
        assert not dummy.dirty

        # all changes need to be commited explcitly
        dummy.settings["A"] = 0
        dummy.settings["B"] = None
        # NB: `dirty` sigsifies metadata dirtyness, if you do
        #
        # > dummy.settings = {...}
        #
        # it will be set automatically, but changing `settings` in-place, as
        # above, will not set `dirty`, so it will need to be set explicitly
        assert not dummy.dirty
        # but we are also changing `version`
        dummy.version += 1
        # which sets it
        assert dummy.dirty

        # add some data
        cur = dummy.cursor()
        for i in range(0, 10):
            cur.execute("INSERT INTO test VALUES (?)", (i,))
        del cur

        # and commit
        dummy.commit()
        dummy.close()

        # now, the above changes persist
        dummy = DummyDB(path, 1, non_default_settings, setup)
        assert not dummy.dirty
        assert dummy.version == 2
        assert dummy.settings["default"] == "yes"
        assert dummy.settings["A"] == 0
        assert dummy.settings["B"] is None

        def stored(dummy: DummyDB) -> _t.Iterator[int]:
            return map(lambda x: x[0], dummy.db.execute("SELECT id from test"))

        assert list(stored(dummy)) == list(range(0, 10))

        # but without a `commit`, all changes get rolled back instead
        dummy.version = 3
        dummy.settings = non_default_settings
        assert dummy.dirty
        cur = dummy.cursor()
        for i in range(10, 20):
            cur.execute("INSERT INTO test VALUES (?)", (i,))
        del cur
        assert list(stored(dummy)) == list(range(0, 20))
        dummy.close()

        dummy = DummyDB(path, 1, non_default_settings, setup)
        # NB: old version! previous block did not commit!
        assert dummy.version == 2
        assert dummy.settings["default"] == "yes"
        assert list(stored(dummy)) == list(range(0, 10))
        dummy.close()

        # openning a database with a newer `want_version` (which inherists from
        # `default_version` by default) forces an upgrade, which, by default,
        # also gets commited to disk
        dummy = DummyDB(path, 3, non_default_settings, setup)
        assert not dummy.dirty
        assert dummy.version == 3
        # `settings` stay the same, since even though `upgrade` above
        # recreates the db, it reuses `settings`
        assert dummy.settings["default"] == "yes"
        assert dummy.settings["A"] == 0
        assert dummy.settings["B"] is None
        dummy.close()

        # and another upgrade
        dummy = DummyDB(path, 4, non_default_settings, setup)
        assert not dummy.dirty
        assert dummy.version == 4
        assert dummy.settings["default"] == "yes"
        dummy.close()

        # upgrades do not get rolled back
        dummy = DummyDB(path, 1, non_default_settings, setup)
        assert not dummy.dirty
        assert dummy.version == 4
        assert dummy.settings["default"] == "yes"
        dummy.close()

        # `AppDB` can make backups before upgrades
        dummy = DummyDB(path, 5, non_default_settings, setup, backup_before_upgrades=True)
        assert not dummy.dirty
        assert dummy.version == 5
        assert dummy.settings["default"] == "yes"
        # modify it a bit
        dummy.settings = non_default_settings
        dummy.commit()
        dummy.close()

        # check it exists and is at the old version
        dummy = DummyDB(_op.join(tmp_path, "test.db.v4.bak"), 1, non_default_settings, setup)
        assert not dummy.dirty
        assert dummy.version == 4
        assert dummy.settings["default"] == "yes"
        dummy.close()

        # updates that fail to `check` propagate `check`'s exceptions and get
        # rolled back
        with pytest.raises(RuntimeError) as exc_info:
            _dummy = DummyDB(path, 6, {}, setup)
        _logging.debug("%s", repr(exc_info.value))

        # and the db is left unmodified
        dummy = DummyDB(path, 1, default_settings, setup)
        assert dummy.version == 5
        assert dummy.settings == non_default_settings
        dummy.close()

        # specifying `default_version` outside of supported versions is an error
        with pytest.raises(AssertionFailure) as exc_info:
            _dummy = DummyDB(path, 7, {}, setup)
        _logging.debug("%s", repr(exc_info.value))

        # trying to reuse the database with a different `APPLICATION_ID` is an error
        with pytest.raises(InvalidDB) as exc_info:
            one = NotDummy(path, 2, {}, setup)
            one.close()
        _logging.debug("%s", repr(exc_info.value))
    finally:
        _os.unlink(path)


if __name__ == "__main__":
    _logging.basicConfig(level=_logging.DEBUG)
    _os.makedirs("test-appdb", exist_ok=True)
    test_DB("test-appdb")
