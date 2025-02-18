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

from kisstdlib.time import *
from kisstdlib.failure import *


def test_parse_Timestamp() -> None:
    def check(xs: str | list[str], value: Timestamp, leftover: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            (res, _), left = parse_Timestamp(x, utc=True)
            if (res, left) != (value, leftover):
                raise CatastrophicFailure(
                    "while parsing `%s`, expected %s, got %s", x, (value, leftover), (res, left)
                )

    # fmt: off
    check("@123",                       Timestamp(123))
    check("@123.456",                   Timestamp("123.456"))
    check("2024",                       Timestamp(1704067200))
    check(["2024-12", "202412"],        Timestamp(1733011200))
    check(["2024-12-31", "20241231"],   Timestamp(1735603200))

    check(["2024-12-31 12:07",
           "202412311207"],             Timestamp(1735646820))

    check(["2024-12-31 12:07:16",
           "2024-12-31_12:07:16",
           "20241231120716"],           Timestamp(1735646836))

    check(["2024-12-31 12:07:16.456",
           "20241231_120716.456",
           "20241231120716.456",
           "20241231120716456"],        Timestamp("1735646836.456"))

    check(["2024-12-31 12:07:16 -01:00",
           "2024-12-31T12:07:16-01:00",
           "2024-12-31 12:07:16-01:00",
           "2024-12-31_12:07:16-0100",
           "20241231120716-0100"],      timestamp("2024-12-31 13:07:16", utc=True))

    check(["2024-12-31 12:07:16.456 -01:00",
           "2024-12-31T12:07:16.456-01:00",
           "2024-12-31T12:07:16,456-01:00",
           "2024-12-31T12:07:16,456000000-01:00",
           "20241231 120716.456 -0100",
           "20241231120716.456 -0100",
           "20241231120716.456-0100",
           "20241231120716456-0100"],   timestamp("2024-12-31 13:07:16.456", utc=True))

    check("2022-11-20 23:32:16+00:30",  timestamp("2022-11-20 23:02:16", utc=True))
    check("2022-11-20 23:32:16 -00:30", timestamp("2022-11-21 00:02:16", utc=True))

    check("20241231120716456-0100 or so",     Timestamp("1735650436.456"), " or so")
    check("2024-12-31 12:07:16 -0100 or so",  Timestamp(1735650436), " or so")
    # fmt: on


def test_format_Timestamp() -> None:
    assert (
        timestamp("2024-12-31 12:07:16.456789", utc=True).format(precision=3, utc=True)
        == "2024-12-31 12:07:16.456"
    )
    assert (
        timestamp("2024-12-31 12:07:16.450", utc=True).format(precision=3, utc=True)
        == "2024-12-31 12:07:16.450"
    )
    assert (
        timestamp("2024-12-31 12:07:16", utc=True).format(precision=3, utc=True)
        == "2024-12-31 12:07:16.000"
    )


def test_parse_Timestamp_end() -> None:
    def check(x: str, value: Timestamp, leftover: str = "") -> None:
        (_, res), left = parse_Timestamp(x, utc=True)
        if (res, left) != (value, leftover):
            raise CatastrophicFailure(
                "while parsing `%s`, expected %s, got %s", x, (value, leftover), res
            )

    # fmt: off
    check("@123",                       Timestamp(124))
    check("@123.456",                   Timestamp("123.457"))
    check("2024",                       timestamp("2025-01-01", utc=True))
    check("2024-11",                    timestamp("2024-12-01", utc=True))
    check("2024-12",                    timestamp("2025-01-01", utc=True))
    check("2024-10-30",                 timestamp("2024-10-31", utc=True))
    check("2024-11-30",                 timestamp("2024-12-01", utc=True))
    check("2024-12-31",                 timestamp("2025-01-01", utc=True))
    check("2024-12-31 12",              timestamp("2024-12-31 13:00", utc=True))
    check("2024-11-30 23",              timestamp("2024-12-01 00:00", utc=True))
    check("2024-12-31 23",              timestamp("2025-01-01 00:00", utc=True))
    check("2024-12-31 23:30",           timestamp("2024-12-31 23:31", utc=True))
    check("2024-12-31 23:59",           timestamp("2025-01-01 00:00", utc=True))
    check("2024-12-31 23:59:30",        timestamp("2024-12-31 23:59:31", utc=True))
    check("2024-12-31 23:59:59",        timestamp("2025-01-01 00:00", utc=True))
    check("2024-12-31 23:59:59.5",      timestamp("2024-12-31 23:59:59.6", utc=True))
    check("2024-12-31 23:59:59.9",      timestamp("2025-01-01 00:00", utc=True))
    # fmt: on


def test_parse_Timerange() -> None:
    def check(xs: str | list[str], value: Timerange, leftover: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            res = parse_Timerange(x, utc=True)
            if res != (value, leftover):
                raise CatastrophicFailure(
                    "while parsing `%s`, expected %s, got %s", x, (value, leftover), res
                )

    # fmt: off
    check("*",                          anytime)
    check(["@123--@125",
           "<@123>--<@125>"],           Timerange(Timestamp(123), Timestamp(126)))
    check(["2024-12-31",
           "2024-12-31*",
           "[2024-12-31]"],             Timerange(timestamp("2024-12-31 00:00", utc=True),
                                                  timestamp("2025-01-01 00:00", utc=True)))
    check("2024-12-31 12",              Timerange(timestamp("2024-12-31 12:00", utc=True),
                                                  timestamp("2024-12-31 13:00", utc=True)))
    check("2024-12-31 12:00",           Timerange(timestamp("2024-12-31 12:00", utc=True),
                                                  timestamp("2024-12-31 12:01", utc=True)))
    check("2024-12-31 23:59",           Timerange(timestamp("2024-12-31 23:59", utc=True),
                                                  timestamp("2025-01-01 00:00", utc=True)))
    check("[2024-12-31 23:59]--[2025-01-02]",
                                        Timerange(timestamp("2024-12-31 23:59", utc=True),
                                                  timestamp("2025-01-03 00:00", utc=True)))
    # fmt: on
