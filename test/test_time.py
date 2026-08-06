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

    itz0 = ["", "Z"] + [
        s + v
        for s in ("+", "-", " +", " -")
        for v in (
            "00",
            "0000",
            "000000",
            "00:00",
            "00:00:00",
            "00h",
            "00h00",
            "00h00m",
            "00h00m00",
            "00h00m00s",
        )
    ]

    tz1 = [
        "01",
        "0100",
        "010000",
        "01:00",
        "01:00:00",
        "01h",
        "01h00",
        "01h00m",
        "01h00m00",
        "01h00m00s",
    ]

    t123 = TimeStamp(123)
    t123d456 = TimeStamp("123.456")

    for itz in [""] + itz0 + [s + v for s in ("+", "-", " +", " -") for v in tz1]:
        check(
            f"@123{itz}",
            t123,
        )
        check(
            f"@123.456{itz}",
            t123d456,
        )

    # $ date-d '2024-12-01 00:00:00 -00:00' +%s
    t1733011200 = TimeStamp(1733011200)

    # $ date -d '2024-12-31 00:00:00 -00:00' +%s
    t1735603200 = TimeStamp(1735603200)

    # $ date -d '2024-12-31 12:00:00 -00:00' +%s
    t1735646400 = TimeStamp(1735646400)

    # $ date -d '2024-12-31 12:07:00 -00:00' +%s
    t1735646820 = TimeStamp(1735646820)

    # $ date -d '2024-12-31 12:07:16 -00:00' +%s
    t1735646836 = TimeStamp(1735646836)

    # same, with milliseconds
    t1735646836d456 = TimeStamp("1735646836.456")

    # $ date -d '2024-12-31 12:07:16 +01:00' +%s
    t1735643236 = TimeStamp(1735643236, 3600)

    # $ date -d '2024-12-31 12:07:16 -01:00' +%s
    t1735650436 = TimeStamp(1735650436, -3600)

    t1735650436d456 = TimeStamp("1735650436.456")

    check(
        [
            "2024",
            "2024y",
        ],
        TimeStamp(1704067200),
    )

    for y in ("", " ", "_", "-", "y", "y "):
        for m in ("", "m", "mo"):
            check(
                f"2024{y}12{m}",
                t1733011200,
            )

        for m in ("", " ", "_", "-", "m", "mo", "m ", "mo "):
            for d in ("", "d"):
                check(
                    f"2024{y}12{m}31{d}",
                    t1735603200,
                )

            for d in ("", " ", "_", "-", "d", "d ", "T"):
                for h in ("", "h"):
                    check(
                        f"2024{y}12{m}31{d}00{h}",
                        t1735603200,
                    )

                    check(
                        f"2024{y}12{m}31{d}12{h}",
                        t1735646400,
                    )

                for h in ("", ":", " ", "_", "-", "h", "h "):
                    for m_ in ("", "m", "min"):
                        check(
                            f"2024{y}12{m}31{d}12{h}07{m_}",
                            t1735646820,
                        )

                    for m_ in ("", ":", " ", "_", "-", "m", "min", "m ", "min "):
                        for s in ("", "s", "sec"):
                            check(
                                f"2024{y}12{m}31{d}12{h}07{m_}00{s}",
                                t1735646820,
                            )

    for y in ("", "-", "y"):
        for m in ("", "-", "m"):
            for d in ("", "-", "_", "d", "T"):
                for h in ("", ":", "h"):
                    for m_ in ("", ":", "m", "min"):
                        for s in ("", "s", "sec"):
                            for itz in itz0:
                                check(
                                    f"2024{y}12{m}31{d}12{h}07{m_}16{s}{itz}",
                                    t1735646836,
                                )

                                check(
                                    [
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.456{s}{itz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.456000{s}{itz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.456000000{s}{itz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.456000000000{s}{itz}",
                                    ],
                                    t1735646836d456,
                                )

                        for i in ("+", " +"):
                            for tz in tz1:
                                check(
                                    [
                                        f"2024{y}12{m}31{d}12{h}07{m_}16{s}{i}{tz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.0{s}{i}{tz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.000{s}{i}{tz}",
                                    ],
                                    t1735643236,
                                    strict=True,
                                )

                        for i in ("-", " -"):
                            for tz in tz1:
                                check(
                                    [
                                        f"2024{y}12{m}31{d}12{h}07{m_}16{s}{i}{tz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.0{s}{i}{tz}",
                                        f"2024{y}12{m}31{d}12{h}07{m_}16.000{s}{i}{tz}",
                                    ],
                                    t1735650436,
                                    strict=True,
                                )

    check(
        "2022-11-20 23:32:16 +00:30",
        timestamp("2022-11-20 23:02:16", 0),
    )
    check(
        "2022-11-20 23:32:16 -00:30",
        timestamp("2022-11-21 00:02:16", 0),
    )
    check(
        "2022-11-20 23:32:16 +00:00:01",
        timestamp("2022-11-20 23:32:15", 0),
    )
    check(
        "2022-11-20 23:32:16 -00:00:01",
        timestamp("2022-11-20 23:32:17", 0),
    )

    # for a in C pl_PL ru_RU ja_JP; do
    #     TZ=GMT+1 LANG=$a.UTF-8 date -d '2024-12-31 12:07:16 -01:00' '+%Y-%m-%d %a %H:%M:%S %z'
    # done

    for r, t in (("", t1735650436), (".456", t1735650436d456)):
        for sp in ("", " ", "_", "-"):
            check(
                [
                    f"2024-12-31120716{r}-0100{sp}or so",
                    f"2024-12-31 12:07:16{r} -0100{sp}or so",
                    f"2024-12-31 Tue 12:07:16{r} -0100{sp}or so",
                    f"2024-12-31 wto 12:07:16{r} -0100{sp}or so",
                    f"2024-12-31 Вт 12:07:16{r} -0100{sp}or so",
                    f"2024-12-31 火 12:07:16{r} -0100{sp}or so",
                ],
                t,
                f"{sp}or so",
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
