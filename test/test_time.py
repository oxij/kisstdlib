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
import typing as _t

import kisstdlib.base as _b
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
                assert res.tz == value.tz

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

    tninf = TimeStamp("-inf")
    tpinf = TimeStamp("inf")
    tn123 = TimeStamp(-123)
    t123 = TimeStamp(123)
    tn123d456 = TimeStamp("-123.456")
    t123d456 = TimeStamp("123.456")

    for itz in [""] + itz0 + [s + v for s in ("+", "-", " +", " -") for v in tz1]:
        check(
            f"@-inf{itz}",
            tninf,
        )
        check(
            [f"@inf{itz}", f"@+inf{itz}"],
            tpinf,
        )
        check(
            f"@-123{itz}",
            tn123,
        )
        check(
            [f"@123{itz}", f"@+123{itz}"],
            t123,
        )
        check(
            f"@-123.456{itz}",
            tn123d456,
        )
        check(
            [f"@123.456{itz}", f"@+123.456{itz}"],
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
        "@-inf",
        TimeStamp("-inf"),
    )
    check(
        ["@inf", "@+inf"],
        TimeStamp("inf"),
    )
    check(
        "@-123",
        TimeStamp(-122),
    )
    check(
        ["@123", "@+123"],
        TimeStamp(124),
    )
    check(
        "@-123.456",
        TimeStamp("-123.455"),
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
    for i in ("-inf", "inf", "+inf"):
        ui = "+inf" if i == "inf" else i

        til = timestamp(f"@{i}")
        ti0 = timestamp(f"@{i}", 0)
        ti1 = timestamp(f"@{i}", 3600)

        assert til.format().startswith(f"@{ui} ")

        assert (
            ti0.format(inf_fmt="{Y:04}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}") == "0001-01-01 00:00:00"
        )
        assert ti0.format() == ti0.format(tz="saved") == ti0.format(tz=0) == f"@{ui} +0000"
        assert ti0.format(tz=3600) == f"@{ui} +0100"
        assert ti0.format(tz=3723) == f"@{ui} +010203"

        assert ti1.format() == ti1.format(tz="saved") == ti1.format(tz=3600) == f"@{ui} +0100"

    assert timestamp("2024-12-31 12:07:16").format().startswith("2024-12-31 12:07:16 ")

    assert (
        timestamp("2024-12-31 12:07:16", 0).format(tz=0)
        == timestamp("2024-12-31 12:07:16 +0000").format(tz=0)
        == timestamp("2024-12-31 12:07:16 +0000", 0).format(tz=0)
        == timestamp("2024-12-31 13:07:16 +0100").format(tz=0)
        == timestamp("2024-12-31 13:07:16 +0100", 0).format(tz=0)
        == timestamp("2024-12-31 13:07:16 +0100", 3600).format(tz=0)
        == timestamp("2024-12-31 13:07:16 +0100", 7200).format(tz=0)
        == "2024-12-31 12:07:16 +0000"
    )

    assert timestamp("2024-12-31 12:07:16", 3600).format(tz=0) == "2024-12-31 11:07:16 +0000"
    assert timestamp("2024-12-31 12:07:16", 3600).format(tz=3723) == "2024-12-31 12:09:19 +010203"
    assert timestamp("2024-12-31 12:07:16", 5400).format(tz=7200) == "2024-12-31 12:37:16 +0200"

    assert (
        timestamp("2024-12-31 12:07:16", 0).format(precision=3, tz=0)
        == "2024-12-31 12:07:16.000 +0000"
    )
    assert timestamp("2024-12-31 12:07:16.001", 0).format(tz=0) == "2024-12-31 12:07:16.001 +0000"
    assert timestamp("2024-12-31 12:07:16.450", 0).format(tz=0) == "2024-12-31 12:07:16.45 +0000"
    assert (
        timestamp("2024-12-31 12:07:16.450", 0).format(precision=3, tz=0)
        == "2024-12-31 12:07:16.450 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.456789", 0).format(tz=0)
        == "2024-12-31 12:07:16.456789 +0000"
    )
    assert (
        timestamp("2024-12-31 12:07:16.456789", 0).format(precision=3, tz=0)
        == "2024-12-31 12:07:16.456 +0000"
    )


def test_TimeDiff_parse() -> None:
    def check(xs: str | list[str], value: TimeDiff, leftovers: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            res, p = _p.run_parser(TimeDiff.parse, False, x)
            assert (res, p.leftovers()) == (value, leftovers)

    for sg, s in (("+", 1), ("-", -1)):
        check(
            [
                f"{sg}0y",
                f"{sg}0m",
                f"{sg}0w",
                f"{sg}0d",
                f"{sg}0h",
                f"{sg}0min",
                f"{sg}0s",
            ],
            TimeDiff(),
        )

        check(
            f"{sg}1y",
            TimeDiff(s * 12),
        )
        check(
            f"{sg}1m",
            TimeDiff(s * 1),
        )
        check(
            f"{sg}1w",
            TimeDiff(0, s * 7 * _b.DAY),
        )
        check(
            f"{sg}1d",
            TimeDiff(0, s * _b.DAY),
        )
        check(
            f"{sg}1h",
            TimeDiff(0, s * _b.HOUR),
        )
        check(
            f"{sg}1min",
            TimeDiff(0, s * _b.MINUTE),
        )
        check(
            f"{sg}1s",
            TimeDiff(0, s),
        )
        check(
            f"{sg}1.1s",
            TimeDiff(0, s * _b.Decimal("1.1")),
        )

        check(
            [
                f"{sg}1m1min",
                f"{sg}1m{sg}1min",
                f"{sg}1mo{sg}1min",
            ],
            TimeDiff(s, s * _b.MINUTE),
        )

        check(
            f"{sg}1y2m3w5d6h7min8.912s",
            TimeDiff(s * 14, s * (26 * _b.DAY + 6 * _b.HOUR + 7 * _b.MINUTE + _b.Decimal("8.912"))),
        )

    check(
        [
            "+1y6m",
            "+6m1y",
            "+18m",
            "+2y-6m",
        ],
        TimeDiff(18),
    )
    check(
        [
            "+1y6m1w1d1h1min1s",
            "+1y6m1w1d2h-0h59min+1s",
            "+2y-6m+1w1d2h-0h59min+1s",
            "+1y6m-1w+15d2h-0d59min+1s",
        ],
        TimeDiff(18, 8 * _b.DAY + _b.HOUR + _b.MINUTE + 1),
    )


def test_TimeDiff_Timefun_format_parse() -> None:
    def check(x: TimeDiff, s: str, **kwargs: _t.Any) -> None:
        assert x.format(**kwargs) == s

        tf, p = _p.run_parser(TimeFun.parse, False, s)
        assert p.leftovers() == ""
        assert tf[0] == x

        assert TimeFun([x]).format(**kwargs) == s

    check(TimeDiff(0, _b.Decimal(1)), "+1s")
    check(TimeDiff(0, _b.Decimal(-1)), "-1s")
    check(TimeDiff(0, _b.Decimal(2 * _b.MINUTE + 3)), "+2min3s")
    check(TimeDiff(0, _b.Decimal(_b.HOUR + 2 * _b.MINUTE + 3)), "+1h2min3s")
    check(
        TimeDiff(0, _b.Decimal(_b.HOUR + 2 * _b.MINUTE + 3) + _b.Decimal("0.456")),
        "+1h2min3.456s",
    )
    check(TimeDiff(1, _b.MINUTE), "+1m1min")
    check(TimeDiff(-1, -_b.MINUTE), "-1m1min")
    check(TimeDiff(9, _b.HOUR + 2 * _b.MINUTE + 3), "+9m1h2min3s")
    check(TimeDiff(-9, _b.HOUR + 2 * _b.MINUTE + 3), "-9m+1h2min3s")
    check(TimeDiff(0, _b.Decimal(3661)), "+1h1min1s")
    check(
        TimeDiff(18, 8 * _b.DAY + _b.HOUR + _b.MINUTE + _b.Decimal("1.123")),
        "+1y6m1w1d1h1min1.123s",
    )
    check(TimeDiff(0, _b.Decimal("0.123")), "+0.123000000s", precision=9)


def test_TimeFun_parse_call_format_parse() -> None:
    def check(ts: TimeStamp, xs: str | list[str], y: str, z: str | None = None) -> None:
        if isinstance(xs, str):
            xs = [xs]
        for s in xs:
            sh, p = _p.run_parser(TimeFun.parse_human, False, s)
            assert p.leftovers() == ""
            res = sh(ts)
            value = timestamp(y, 0)
            assert res == value

            s2 = sh.format()
            if z is not None:
                assert s2 == z
                assert sh.format_human() == "now" + z
            elif s.startswith("now"):
                assert s2 == s[3:]
                assert sh.format_human() == s

            sh2, p = _p.run_parser(TimeFun.parse, False, s2)
            assert p.leftovers() == ""
            assert sh == sh2

    v = timestamp("2025-01-01 00:00:00", 0)
    check(v, "now-1y", "2024-01-01 00:00:00")
    check(v, "now+1y", "2026-01-01 00:00:00")
    check(v, "now-1m", "2024-12-01 00:00:00")
    check(v, "now+1m", "2025-02-01 00:00:00")
    check(v, "now-1d", "2024-12-31 00:00:00")
    check(v, "now+1d", "2025-01-02 00:00:00")
    check(v, "now-1s", "2024-12-31 23:59:59")
    check(v, "now+1s", "2025-01-01 00:00:01")
    check(v, "now-0.5s", "2024-12-31 23:59:59.5")
    check(v, "now+0.5s", "2025-01-01 00:00:00.5")

    v = timestamp("2025-01-01 12:34:45", 0)
    check(v, "now-1d", "2024-12-31 12:34:45")
    check(v, "now+1d", "2025-01-02 12:34:45")
    check(v, "now-1m", "2024-12-01 12:34:45")
    check(v, "now+1m", "2025-02-01 12:34:45")
    check(v, "now-1m1d", "2024-11-30 12:34:45")
    check(v, "now+1m1d", "2025-02-02 12:34:45")
    check(v, "now-1y", "2024-01-01 12:34:45")
    check(v, "now+1y", "2026-01-01 12:34:45")
    check(v, "now-1y1d", "2023-12-31 12:34:45")
    check(v, "now+1y1d", "2026-01-02 12:34:45")
    check(v, "now-18m", "2023-07-01 12:34:45", "-1y6m")
    check(v, "now+18m", "2026-07-01 12:34:45", "+1y6m")
    check(v, "now-18m7d3h2min1.25s", "2023-06-24 09:32:43.75", "-1y6m1w3h2min1.25s")
    check(v, "now+18m7d3h2min1.25s", "2026-07-08 15:36:46.25", "+1y6m1w3h2min1.25s")

    def prev(x: str) -> list[str]:
        return [f"last {x}", f"prev {x}", f"previous {x}"]

    def foll(x: str) -> list[str]:
        return [f"next {x}", f"following {x}"]

    v = timestamp("2026-06-18 12:34:45.123", 0)
    check(v, "this second", "2026-06-18 12:34:45", "-%s")
    check(v, prev("second"), "2026-06-18 12:34:44", "-%s-1s")
    check(v, foll("second"), "2026-06-18 12:34:46", "-%s+1s")
    check(v, "this second-1d", "2026-06-17 12:34:45", "-%s-1d")
    check(v, "this second+1d", "2026-06-19 12:34:45", "-%s+1d")
    check(v, "this minute", "2026-06-18 12:34:00", "-%min")
    check(v, prev("minute"), "2026-06-18 12:33:00")
    check(v, foll("minute"), "2026-06-18 12:35:00")
    check(v, "this minute-1d", "2026-06-17 12:34:00")
    check(v, "this minute+1d", "2026-06-19 12:34:00")
    check(v, "this hour", "2026-06-18 12:00:00", "-%h")
    check(v, prev("hour"), "2026-06-18 11:00:00")
    check(v, foll("hour"), "2026-06-18 13:00:00")
    check(v, "this hour-1d", "2026-06-17 12:00:00")
    check(v, "this hour+1d", "2026-06-19 12:00:00")
    check(v, ["this day", "today"], "2026-06-18 00:00:00", "-%d")
    check(v, ["this day-1d", *prev("day"), "yesterday"], "2026-06-17 00:00:00")
    check(v, ["this day+1d", *foll("day"), "tomorrow"], "2026-06-19 00:00:00")
    check(v, "this week", "2026-06-15 00:00:00", "-%w")
    check(v, prev("week"), "2026-06-08 00:00:00")
    check(v, foll("week"), "2026-06-22 00:00:00")
    check(v, "this week-1d", "2026-06-14 00:00:00")
    check(v, "this week+1d", "2026-06-16 00:00:00")
    check(v, "this month", "2026-06-01 00:00:00", "-%m")
    check(v, prev("month"), "2026-05-01 00:00:00")
    check(v, foll("month"), "2026-07-01 00:00:00")
    check(v, "this month-1d", "2026-05-31 00:00:00")
    check(v, "this month+1d", "2026-06-02 00:00:00")
    check(v, "this year", "2026-01-01 00:00:00", "-%y")
    check(v, prev("year"), "2025-01-01 00:00:00")
    check(v, foll("year"), "2027-01-01 00:00:00")
    check(v, "this year-1d", "2025-12-31 00:00:00")
    check(v, "this year+1d", "2026-01-02 00:00:00")


def test_TimeRange_parse_plain() -> None:
    def check(
        xs: str | list[str], value: TimeRange, leftovers: str = "", strict: bool = False
    ) -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            (res, _), p = _p.run_parser(TimeRange.parse, False, x, 0)
            assert (res, p.leftovers()) == (value, leftovers)
            if strict:
                assert res.start.tz == value.start.tz
                assert res.end.tz == value.end.tz

    check("*", anytime)

    r123t124 = TimeRange(TimeStamp(123), TimeStamp(124))
    r123t125 = TimeRange(TimeStamp(123), TimeStamp(125))
    r123t126 = TimeRange(TimeStamp(123), TimeStamp(126))
    r1d010000 = TimeRange(timestamp("2024-12-31 00:00", 0), timestamp("2025-01-01 00:00", 0))
    r1h311300 = TimeRange(timestamp("2024-12-31 12:00", 0), timestamp("2024-12-31 13:00", 0))
    r1m311201 = TimeRange(timestamp("2024-12-31 12:00", 0), timestamp("2024-12-31 12:01", 0))
    r1m010000 = TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-01 00:00", 0))
    r3d030000 = TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-03 00:00", 0))
    r2d020000 = TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-02 00:00", 0))
    r2d021200 = TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-02 12:00", 0))
    r2d021201 = TimeRange(timestamp("2024-12-31 23:59", 0), timestamp("2025-01-02 12:01", 0))

    for l, r in (("", ""), ("<", ">"), ("[", "]")):
        check(
            [
                f"{l}@123{r}",
                f"{l}@123*{r}",
            ],
            r123t124,
        )
        check(
            [
                f"{l}2024-12-31{r}",
                f"{l}2024-12-31*{r}",
            ],
            r1d010000,
        )
        check(
            [
                f"{l}2024-12-31 12{r}",
                f"{l}2024-12-31 12*{r}",
            ],
            r1h311300,
        )
        check(
            [
                f"{l}2024-12-31 12:00{r}",
                f"{l}2024-12-31 12:00*{r}",
            ],
            r1m311201,
        )
        check(
            [
                f"{l}2024-12-31 23:59{r}",
                f"{l}2024-12-31 23:59*{r}",
            ],
            r1m010000,
        )

        for d in ("--", " --", "-- ", " -- ", "---"):
            check(
                [
                    f"{l}@123{r}{d}{l}@125{r}",
                    f"{l}@123.^{r}{d}{l}@125{r}",
                    f"{l}@123*{r}{d}{l}@125{r}",
                    f"{l}@123*.^{r}{d}{l}@125{r}",
                ],
                r123t125,
            )
            check(
                [
                    f"{l}@123{r}{d}{l}@125.${r}",
                    f"{l}@123.^{r}{d}{l}@125*.${r}",
                    f"{l}@123*{r}{d}{l}@125*.${r}",
                    f"{l}@123*.^{r}{d}{l}@125*.${r}",
                ],
                r123t126,
            )
            check(
                [
                    f"{l}2024-12-31 23:59{r}{d}{l}2025-01-02{r}",
                    f"{l}2024-12-31 23:59*{r}{d}{l}2025-01-02{r}",
                ],
                r2d020000,
            )
            check(
                [
                    f"{l}2024-12-31 23:59{r}{d}{l}2025-01-02.${r}",
                    f"{l}2024-12-31 23:59.^{r}{d}{l}2025-01-02*.${r}",
                    f"{l}2024-12-31 23:59*{r}{d}{l}2025-01-02*.${r}",
                    f"{l}2024-12-31 23:59*.^{r}{d}{l}2025-01-02*.${r}",
                ],
                r3d030000,
            )
            check(
                [
                    f"{l}2024-12-31 23:59{r}{d}{l}2025-01-02 12:00{r}",
                    f"{l}2024-12-31 23:59*{r}{d}{l}2025-01-02 12:00{r}",
                ],
                r2d021200,
            )
            check(
                [
                    f"{l}2024-12-31 23:59{r}{d}{l}2025-01-02 12:00.${r}",
                    f"{l}2024-12-31 23:59.^{r}{d}{l}2025-01-02 12:00*.${r}",
                    f"{l}2024-12-31 23:59*{r}{d}{l}2025-01-02 12:00*.${r}",
                    f"{l}2024-12-31 23:59*.^{r}{d}{l}2025-01-02 12:00*.${r}",
                ],
                r2d021201,
            )

    check(
        [
            "[2024-12-31 23:59:00 +0100]--[2025-01-01 12:00:00 +0200]",
        ],
        TimeRange(timestamp("2024-12-31 23:59:00", 3600), timestamp("2025-01-01 12:00:00", 7200)),
        strict=True,
    )


def test_TimeRange_parse_Timefun() -> None:
    def check(ts: TimeStamp, xs: str | list[str], value: TimeRange, leftovers: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            res, p = _p.run_parser(TimeRange.parse, False, x, 0, now=ts)
            assert (res[0], p.leftovers()) == (value, leftovers)

    v = timestamp("2025-01-01 00:00", 0)
    check(v, "today", timerange("2025-01-01*", 0))
    check(v, "yesterday", timerange("2024-12-31*", 0))
    check(v, "tomorrow", timerange("2025-01-02*", 0))
    check(v, "today-2d", timerange("2024-12-30*", 0))
    check(v, "today+2d", timerange("2025-01-03*", 0))

    check(
        v,
        [
            "now--.^",
            "now--.$",
        ],
        timerange("2025-01-01 00:00--2025-01-01 00:00", 0),
    )
    check(
        v,
        [
            "now--tomorrow",
            "now--.^-%d+1d",
            "now--.$-%d+1d",
        ],
        timerange("2025-01-01 00:00--2025-01-02 00:00", 0),
    )
    check(
        v,
        [
            "now--tomorrow.$",
            "now--.^-%d+2d",
            "now--.$-%d+2d",
        ],
        timerange("2025-01-01 00:00--2025-01-03 00:00", 0),
    )
    check(
        v,
        [
            "yesterday--next month",
            "yesterday--.^+1m1d",
            "yesterday--.$+1m",
        ],
        timerange("2024-12-31 00:00--2025-02-01 00:00", 0),
    )
    check(
        v,
        [
            "yesterday--next month.$",
            "yesterday--.^+1m29d",
            "yesterday--.$+2m",
        ],
        timerange("2024-12-31 00:00--2025-03-01 00:00", 0),
    )
    check(
        v,
        [
            "last week--yesterday.$",
            "last week--today",
        ],
        timerange("2024-12-23 00:00--2025-01-01 00:00", 0),
    )
    check(
        v,
        [
            "last week--today.$",
            "last week--tomorrow",
        ],
        timerange("2024-12-23 00:00--2025-01-02 00:00", 0),
    )
    check(
        v,
        [
            "last week.$--today",
            "this week--today",
        ],
        timerange("2024-12-30 00:00--2025-01-01 00:00", 0),
    )
    check(
        v,
        [
            "last month--next year",
            "last month--.^+1y1m",
            "last month--.$+1y",
        ],
        timerange("2024-12-01 00:00--2026-01-01 00:00", 0),
    )
    check(
        v,
        [
            "last month--next year.$",
            "last month--.^+2y1m",
            "last month--.$+2y",
        ],
        timerange("2024-12-01 00:00--2027-01-01 00:00", 0),
    )
    check(
        v,
        [
            "last month.$+1m--next year",
            "this month.$--this year.$",
            "next month--this year+1y.^",
            "next month--this year.^+1y",
        ],
        timerange("2025-02-01 00:00--2026-01-01 00:00", 0),
    )

    check(
        v,
        [
            "2024-12-20.^+1d",
            "2024-12-20*.^+1d",
        ],
        timerange("2024-12-21*.^", 0),
    )
    check(
        v,
        [
            "2024-12-20.$+1d",
            "2024-12-20*.$+1d",
        ],
        timerange("2024-12-22*.^", 0),
    )
    check(
        v,
        [
            "2024-12-20.^+1d--.^+2d",
            "2024-12-20.^+1d--.$+2d",
            "2024-12-20.^+1d--2024-12-21+2d",
            "2024-12-20.^+1d--2024-12-21*+2d",
            "2024-12-20.^+1d--2024-12-21.^+2d",
            "2024-12-20.^+1d--2024-12-21*.^+2d",
        ],
        timerange("2024-12-21--2024-12-23", 0),
    )


def test_TimeRange_format() -> None:
    x = anytime
    assert x.format_delta() == "+inf"
    assert x.format3() == "@-inf +0000 -- @+inf +0000 => +inf"
    assert x.format_org() == "[@-inf]--[@+inf] =>  +inf"

    x = TimeRange(anytime.end, anytime.start)
    assert x.format_delta() == "-inf"
    assert x.format3() == "@+inf +0000 -- @-inf +0000 => -inf"
    assert x.format_org() == "[@+inf]--[@-inf] =>  -inf"

    x = timerange("2026-01-01 12:00:00.1*", 0)
    assert x.format_delta() == "0:00:00.1"
    assert x.format_delta(precision=0) == "0:00:00"
    assert x.format_delta(precision=1) == "0:00:00.1"
    assert x.format_delta(precision=2) == "0:00:00.10"
    assert (
        x.format3(tz=0) == "2026-01-01 12:00:00.1 +0000 -- 2026-01-01 12:00:00.2 +0000 => 0:00:00.1"
    )
    if IS_ENG:
        assert x.format_org(tz=0) == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 12:00] =>  0:00"

    x = timerange("2026-01-01 12:00*", 0)
    assert x.format_delta() == "0:01:00"
    assert x.format_delta(precision=0) == "0:01:00"
    assert x.format_delta(precision=1) == "0:01:00.0"
    assert x.format_delta(precision=2) == "0:01:00.00"
    assert x.format3(tz=0) == "2026-01-01 12:00:00 +0000 -- 2026-01-01 12:01:00 +0000 => 0:01:00"
    assert (
        x.format3(precision=0, tz=0)
        == "2026-01-01 12:00:00 +0000 -- 2026-01-01 12:01:00 +0000 => 0:01:00"
    )
    assert (
        x.format3(precision=1, tz=0)
        == "2026-01-01 12:00:00.0 +0000 -- 2026-01-01 12:01:00.0 +0000 => 0:01:00.0"
    )
    if IS_ENG:
        assert x.format_org(tz=0) == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 12:01] =>  0:01"

    x = TimeRange(x.end, x.start)
    assert x.format_delta() == "-0:01:00"
    assert x.format3(tz=0) == "2026-01-01 12:01:00 +0000 -- 2026-01-01 12:00:00 +0000 => -0:01:00"

    x = timerange("2026-01-01 12*", 0)
    assert x.format_delta() == "1:00:00"
    assert x.format3(tz=0) == "2026-01-01 12:00:00 +0000 -- 2026-01-01 13:00:00 +0000 => 1:00:00"
    if IS_ENG:
        assert x.format_org(tz=0) == "[2026-01-01 Thu 12:00]--[2026-01-01 Thu 13:00] =>  1:00"

    x = timerange("2026-01-01 00:00--2026-01-02 12:00", 0)
    assert x.format_delta() == "36:00:00"
    if IS_ENG:
        assert x.format_org(tz=0) == "[2026-01-01 Thu 00:00]--[2026-01-02 Fri 12:00] => 36:00"

    x = timerange("2026-01-01 00:00--2026-01-02 12:00.$", 0)
    assert x.format_delta() == "36:01:00"
    if IS_ENG:
        assert x.format_org(tz=0) == "[2026-01-01 Thu 00:00]--[2026-01-02 Fri 12:01] => 36:01"

    x = timerange("2025-01-02 12*", 3600)
    x.end.tz = 0
    assert x.format(tz="saved") == "2025-01-02 12:00:00 +0100--2025-01-02 12:00:00 +0000"
    assert x.format(tz="saved_start") == "2025-01-02 12:00:00 +0100--2025-01-02 13:00:00 +0100"
    assert x.format(tz="saved_end") == "2025-01-02 11:00:00 +0000--2025-01-02 12:00:00 +0000"
    assert x.format(tz=3723) == "2025-01-02 12:02:03 +010203--2025-01-02 13:02:03 +010203"


def test_TimeStamp_TimeRange_tz_str() -> None:
    # TZ=America/Los_Angeles date --date @$1
    # TZ=Europe/Warsaw date --date @$1

    x = timerange("2020-03-08 01:02:03.456", "America/Los_Angeles")
    assert x.start == _b.Decimal("1583658123.456")
    assert x.end == _b.Decimal("1583658123.457")
    assert x.format(tz="saved") == "2020-03-08 01:02:03.456 -0800--2020-03-08 01:02:03.457 -0800"

    x = timerange("2020-03-08 01:02:03.456", "Europe/Warsaw")
    assert x.start == _b.Decimal("1583625723.456")
    assert x.end == _b.Decimal("1583625723.457")
    assert x.format(tz="saved") == "2020-03-08 01:02:03.456 +0100--2020-03-08 01:02:03.457 +0100"

    # American daylight saving transitions

    x = timerange("2020-03-08 00", "America/Los_Angeles")
    assert x.start == 1583654400
    assert x.end == 1583658000
    assert x.format(tz="saved") == "2020-03-08 00:00:00 -0800--2020-03-08 01:00:00 -0800"

    x = timerange("2020-03-08 01", "America/Los_Angeles")
    assert x.start == 1583658000
    assert x.end == 1583661600
    assert x.format(tz="saved") == "2020-03-08 01:00:00 -0800--2020-03-08 03:00:00 -0700"

    x = timerange("2020-03-08 02", "America/Los_Angeles")
    assert x.start == 1583661600
    assert x.end == 1583665200
    assert x.format(tz="saved") == "2020-03-08 03:00:00 -0700--2020-03-08 04:00:00 -0700"
    # NB: not                   == "2020-03-08 02:00:00 -0800--2020-03-08 04:00:00 -0700"

    x = timerange("2020-11-01 00", "America/Los_Angeles")
    assert x.start == 1604214000
    assert x.end == 1604217600
    assert x.format(tz="saved") == "2020-11-01 00:00:00 -0700--2020-11-01 01:00:00 -0700"

    x = timerange("2020-11-01 01", "America/Los_Angeles")
    assert x.start == 1604217600
    assert x.end == 1604221200
    assert x.format(tz="saved") == "2020-11-01 01:00:00 -0700--2020-11-01 01:00:00 -0800"

    x = timerange("2020-11-01 02", "America/Los_Angeles")
    assert x.start == 1604224800
    assert x.end == 1604228400
    assert x.format(tz="saved") == "2020-11-01 02:00:00 -0800--2020-11-01 03:00:00 -0800"

    # European daylight saving transitions

    x = timerange("2020-03-29 00", "Europe/Warsaw")
    assert x.start == 1585436400
    assert x.end == 1585440000
    assert x.format(tz="saved") == "2020-03-29 00:00:00 +0100--2020-03-29 01:00:00 +0100"

    x = timerange("2020-03-29 01", "Europe/Warsaw")
    assert x.start == 1585440000
    assert x.end == 1585443600
    assert x.format(tz="saved") == "2020-03-29 01:00:00 +0100--2020-03-29 03:00:00 +0200"

    x = timerange("2020-03-29 02", "Europe/Warsaw")
    assert x.start == 1585443600
    assert x.end == 1585447200
    assert x.format(tz="saved") == "2020-03-29 03:00:00 +0200--2020-03-29 04:00:00 +0200"
    # NB: not                   == "2020-03-29 02:00:00 +0100--2020-03-29 04:00:00 +0200"

    x = timerange("2020-10-25 01", "Europe/Warsaw")
    assert x.start == 1603580400
    assert x.end == 1603584000
    assert x.format(tz="saved") == "2020-10-25 01:00:00 +0200--2020-10-25 02:00:00 +0200"

    x = timerange("2020-10-25 02", "Europe/Warsaw")
    assert x.start == 1603584000
    assert x.end == 1603587600
    assert x.format(tz="saved") == "2020-10-25 02:00:00 +0200--2020-10-25 02:00:00 +0100"

    x = timerange("2020-10-25 03", "Europe/Warsaw")
    assert x.start == 1603591200
    assert x.end == 1603594800
    assert x.format(tz="saved") == "2020-10-25 03:00:00 +0100--2020-10-25 04:00:00 +0100"


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


def test_TimeRange_middle_delta() -> None:
    def check(x: TimeRange, middle: TimeStamp, delta: _b.Decimal | None = None) -> None:
        assert x.middle == middle
        assert x.delta == (_b.Decimal("inf") if delta is None else delta)

    check(anytime, TimeStamp("inf"))
    check(TimeRange(TimeStamp("-inf"), TimeStamp("-inf")), TimeStamp("-inf"))
    check(TimeRange(TimeStamp("inf"), TimeStamp("inf")), TimeStamp("inf"))

    for i in range(-10, 11):
        check(TimeRange(TimeStamp("-inf"), TimeStamp(i)), TimeStamp("-inf"))
        check(TimeRange(TimeStamp(i), TimeStamp("inf")), TimeStamp("inf"))
