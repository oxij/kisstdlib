# Copyright (c) 2023-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Testing `kisstdlib.time` module."""

import locale

import kisstdlib.parsing as _p
from kisstdlib.time import *
from kisstdlib.failure import *

IS_ENG = locale.getlocale()[0] in ("C", "en_US")


def test_TimeStamp_parse() -> None:
    def check(
        xs: str | list[str], value: TimeStamp, leftovers: str = "", strict: bool = False
    ) -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            (res, _), p = _p.run_parser(TimeStamp.parse2, False, x, 0)
            assert (res, p.leftovers()) == (value, leftovers)
            if strict:
                assert res.gmtoff == value.gmtoff

    check(
        "@123",
        TimeStamp(123),
    )
    check(
        "@123.456",
        TimeStamp("123.456"),
    )
    check(
        [
            "2024",
        ],
        TimeStamp(1704067200),
    )
    check(
        [
            "2024-12",
            "202412",
        ],
        TimeStamp(1733011200),
    )
    check(
        [
            "2024-12-31",
            "20241231",
        ],
        TimeStamp(1735603200),
    )

    check(
        [
            "2024-12-31 12:07",
            "202412311207",
        ],
        TimeStamp(1735646820),
    )

    check(
        [
            "2024-12-31 12:07:16",
            "2024-12-31_12:07:16",
            "20241231120716",
        ],
        TimeStamp(1735646836),
    )

    check(
        [
            "2024-12-31 12:07:16.456",
            "20241231_120716.456",
            "20241231120716.456",
            "20241231120716456",
        ],
        TimeStamp("1735646836.456"),
    )

    check(
        [
            "2024-12-31 12:07:16 -01:00",
            "2024-12-31 12:07:16.0 -01:00",
            "2024-12-31 12:07:16.000 -01:00",
        ],
        # $ date +%s -d '2024-12-31 12:07:16 -01:00'
        TimeStamp(1735650436, -3600),
        strict=True,
    )

    check(
        [
            "2024-12-31 12:07:16 -01:00",
            "2024-12-31T12:07:16-01:00",
            "2024-12-31 12:07:16-01:00",
            "2024-12-31_12:07:16-0100",
            "20241231120716-0100",
        ],
        timestamp("2024-12-31 13:07:16", 0),
    )

    check(
        [
            "2024-12-31 12:07:16.456 -01:00",
            "2024-12-31T12:07:16.456-01:00",
            "2024-12-31T12:07:16,456-01:00",
            "2024-12-31T12:07:16,456000000-01:00",
            "20241231 120716.456 -0100",
            "20241231120716.456 -0100",
            "20241231120716.456-0100",
            "20241231120716456-0100",
        ],
        timestamp("2024-12-31 13:07:16.456", 0),
    )

    check(
        "2022-11-20 23:32:16+00:30",
        timestamp("2022-11-20 23:02:16", 0),
    )
    check(
        "2022-11-20 23:32:16 -00:30",
        timestamp("2022-11-21 00:02:16", 0),
    )

    check(
        "20241231120716456-0100 or so",
        TimeStamp("1735650436.456"),
        " or so",
    )
    check(
        "2024-12-31 12:07:16 -0100 or so",
        TimeStamp(1735650436),
        " or so",
    )


def test_TimeStamp_parse_end() -> None:
    def check(xs: str | list[str], value: TimeStamp, leftovers: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            (_, res), p = _p.run_parser(TimeStamp.parse2, False, x, 0)
            assert (res, p.leftovers()) == (value, leftovers)

    check(
        "@123",
        TimeStamp(124),
    )
    check(
        "@123.456",
        TimeStamp("123.457"),
    )
    check(
        "2024",
        timestamp("2025-01-01", 0),
    )
    check(
        "2024-11",
        timestamp("2024-12-01", 0),
    )
    check(
        "2024-12",
        timestamp("2025-01-01", 0),
    )
    check(
        "2024-10-30",
        timestamp("2024-10-31", 0),
    )
    check(
        "2024-11-30",
        timestamp("2024-12-01", 0),
    )
    check(
        "2024-12-31",
        timestamp("2025-01-01", 0),
    )
    check(
        "2024-12-31 12",
        timestamp("2024-12-31 13:00", 0),
    )
    check(
        "2024-11-30 23",
        timestamp("2024-12-01 00:00", 0),
    )
    check(
        "2024-12-31 23",
        timestamp("2025-01-01 00:00", 0),
    )
    check(
        "2024-12-31 23:30",
        timestamp("2024-12-31 23:31", 0),
    )
    check(
        "2024-12-31 23:59",
        timestamp("2025-01-01 00:00", 0),
    )
    check(
        "2024-12-31 23:59:30",
        timestamp("2024-12-31 23:59:31", 0),
    )
    check(
        "2024-12-31 23:59:59",
        timestamp("2025-01-01 00:00", 0),
    )
    check(
        "2024-12-31 23:59:59.5",
        timestamp("2024-12-31 23:59:59.6", 0),
    )
    check(
        "2024-12-31 23:59:59.9",
        timestamp("2025-01-01 00:00", 0),
    )


def test_TimeStamp_format() -> None:
    assert timestamp("2024-12-31 12:07:16").format().startswith("2024-12-31 12:07:16 ")

    assert (
        timestamp("2024-12-31 12:07:16", 0).format(gmtoff=0)
        == timestamp("2024-12-31 12:07:16 +0000").format(gmtoff=0)
        == timestamp("2024-12-31 12:07:16 +0000", 0).format(gmtoff=0)
        == timestamp("2024-12-31 13:07:16 +0100").format(gmtoff=0)
        == timestamp("2024-12-31 13:07:16 +0100", 0).format(gmtoff=0)
        == timestamp("2024-12-31 13:07:16 +0100", 3600).format(gmtoff=0)
        == timestamp("2024-12-31 13:07:16 +0100", 7200).format(gmtoff=0)
        == "2024-12-31 12:07:16 +0000"
    )

    assert timestamp("2024-12-31 12:07:16", 3600).format(gmtoff=0) == "2024-12-31 11:07:16 +0000"
    assert (
        timestamp("2024-12-31 12:07:16", 3600).format(gmtoff=3723) == "2024-12-31 12:09:19 +010203"
    )
    assert timestamp("2024-12-31 12:07:16", 5400).format(gmtoff=7200) == "2024-12-31 12:37:16 +0200"

    assert (
        timestamp("2024-12-31 12:07:16", 0).format(precision=3, gmtoff=0)
        == "2024-12-31 12:07:16.000 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.001", 0).format(gmtoff=0) == "2024-12-31 12:07:16.001 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.450", 0).format(gmtoff=0) == "2024-12-31 12:07:16.45 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.450", 0).format(precision=3, gmtoff=0)
        == "2024-12-31 12:07:16.450 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.456789", 0).format(gmtoff=0)
        == "2024-12-31 12:07:16.456789 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.456789", 0).format(precision=3, gmtoff=0)
        == "2024-12-31 12:07:16.456 +0000"
    )


def test_TimeRange_parse() -> None:
    def check(
        xs: str | list[str], value: TimeRange, leftovers: str = "", strict: bool = False
    ) -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            res, p = _p.run_parser(TimeRange.parse, False, x, 0)
            assert (res, p.leftovers()) == (value, leftovers)
            if strict:
                assert res.start.gmtoff == value.start.gmtoff
                assert res.end.gmtoff == value.end.gmtoff

    check("*", anytime)
    check(
        [
            "@123--@125",
            "<@123>--<@125>",
        ],
        TimeRange(TimeStamp(123), TimeStamp(126)),
    )
    check(
        [
            "2024-12-31",
            "2024-12-31*",
            "[2024-12-31]",
        ],
        TimeRange(timestamp("2024-12-31 00:00", 0), timestamp("2025-01-01 00:00", 0)),
    )
    check(
        [
            "2024-12-31 12",
            "2024-12-31 12*",
            "[2024-12-31 12]",
            "[2024-12-31 12*]",
        ],
        TimeRange(timestamp("2024-12-31 12:00", 0), timestamp("2024-12-31 13:00", 0)),
    )
    check(
        [
            "2024-12-31 12:00",
            "2024-12-31 12:00*",
            "[2024-12-31 12:00]",
            "[2024-12-31 12:00*]",
        ],
        TimeRange(timestamp("2024-12-31 12:00", 0), timestamp("2024-12-31 12:01", 0)),
    )
    check(
        [
            "2024-12-31 23:59",
            "2024-12-31 23:59*",
            "[2024-12-31 23:59]",
            "[2024-12-31 23:59*]",
        ],
        TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-01 00:00", 0)),
    )
    check(
        [
            "[2024-12-31 23:59]--[2025-01-02]",
        ],
        TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-03 00:00", 0)),
    )

    check(
        [
            "[2024-12-31 23:59:00 +0100]--[2025-01-01 12:00:00 +0200]",
        ],
        TimeRange(timestamp("2024-12-31 23:59:00", 3600), timestamp("2025-01-01 12:00:01", 7200)),
        strict=True,
    )


def test_TimeRange_format() -> None:
    # fmt: off
    x = timerange("2026-01-01 12:00:00.1*", 0)
    assert x.format_delta()            == "0:00:00.1"
    assert x.format_delta(precision=0) == "0:00:00"
    assert x.format_delta(precision=1) == "0:00:00.1"
    assert x.format_delta(precision=2) == "0:00:00.10"
    assert x.format3(gmtoff=0)         == "2026-01-01 12:00:00.1 +0000 -- 2026-01-01 12:00:00.2 +0000 => 0:00:00.1"
    if IS_ENG:
        assert x.format_org(gmtoff=0)  == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 12:00] =>  0:00"

    x = timerange("2026-01-01 12:00*", 0)
    assert x.format_delta()            == "0:01:00"
    assert x.format_delta(precision=0) == "0:01:00"
    assert x.format_delta(precision=1) == "0:01:00.0"
    assert x.format_delta(precision=2) == "0:01:00.00"
    assert x.format3(gmtoff=0)         == "2026-01-01 12:00:00 +0000 -- 2026-01-01 12:01:00 +0000 => 0:01:00"
    assert x.format3(precision=0, gmtoff=0) == "2026-01-01 12:00:00 +0000 -- 2026-01-01 12:01:00 +0000 => 0:01:00"
    assert x.format3(precision=1, gmtoff=0) == "2026-01-01 12:00:00.0 +0000 -- 2026-01-01 12:01:00.0 +0000 => 0:01:00.0"
    if IS_ENG:
        assert x.format_org(gmtoff=0)  == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 12:01] =>  0:01"

    x = TimeRange(x.end, x.start)
    assert x.format_delta()            == "-0:01:00"
    assert x.format3(gmtoff=0)         == "2026-01-01 12:01:00 +0000 -- 2026-01-01 12:00:00 +0000 => -0:01:00"

    x = timerange("2026-01-01 12*", 0)
    assert x.format_delta()            == "1:00:00"
    assert x.format3(gmtoff=0)         == "2026-01-01 12:00:00 +0000 -- 2026-01-01 13:00:00 +0000 => 1:00:00"
    if IS_ENG:
        assert x.format_org(gmtoff=0)  == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 13:00] =>  1:00"

    x = timerange("2026-01-01 00:00--2026-01-02 12:00", 0)
    assert x.format_delta()            == "36:01:00"
    if IS_ENG:
        assert x.format_org(gmtoff=0)  == "[2026-01-01 Thu 00:00]--[2026-01-02 Fri 12:01] => 36:01"

    x = timerange("2025-01-02 12*", 3600)
    x.end.gmtoff = 0
    assert x.format(gmtoff="saved") == "2025-01-02 12:00:00 +0100--2025-01-02 12:00:00 +0000"
    assert x.format(gmtoff="saved_start") == "2025-01-02 12:00:00 +0100--2025-01-02 13:00:00 +0100"
    assert x.format(gmtoff="saved_end") == "2025-01-02 11:00:00 +0000--2025-01-02 12:00:00 +0000"
    assert x.format(gmtoff=3723) == "2025-01-02 12:02:03 +010203--2025-01-02 13:02:03 +010203"
    # fmt: on


def test_TimeRange_order() -> None:
    assert timerange("2025*", 0) == timerange("2025*", 0)

    def check(x: TimeRange, y: TimeRange) -> None:
        assert x < y
        assert y > x
        if x == y:
            assert x <= y
            assert y >= x

    def no_start(x: TimeRange) -> TimeRange:
        x.includes_start = False
        return x

    def yes_end(x: TimeRange) -> TimeRange:
        x.includes_end = True
        return x

    check(timerange("2024*", 0), timerange("2025*", 0))
    check(timerange("2025*", 0), no_start(timerange("2025*", 0)))
    check(timerange("2025*", 0), yes_end(timerange("2025*", 0)))
