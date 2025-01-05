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

"""`Timestamp`, `Timerange`, and related things."""

import calendar as _calendar
import dataclasses as _dc
import decimal as _dec
import re as _re
import time as _time
import typing as _t

import kisstdlib.failure as _f
import kisstdlib.parsing as _p


class Timevalue(_dec.Decimal):
    """Generic time value of arbitrary precision."""

    @staticmethod
    def now() -> "Timevalue":
        raise NotImplementedError()

    def to_Timestamp(self) -> "Timestamp":
        raise NotImplementedError()

    def is_neg_inf(self) -> bool:
        return self.is_infinite() and self < 0

    def is_pos_inf(self) -> bool:
        return self.is_infinite() and self > 0


class Timestamp(Timevalue):
    """Seconds since UNIX epoch, with arbitrary precision."""

    @staticmethod
    def from_ms(value: int) -> "Timestamp":
        return Timestamp(_dec.Decimal(value) / 1000)

    @staticmethod
    def from_ns(value: int) -> "Timestamp":
        return Timestamp(_dec.Decimal(value) / 1000000000)

    @staticmethod
    def now() -> "Timestamp":
        return Timestamp.from_ns(_time.time_ns())

    def to_Timestamp(self) -> "Timestamp":
        return self

    def __repr__(self) -> str:
        return f"<Timestamp {self.format(precision=9, utc=True)}>"

    def format(
        self, fmt: str = "%Y-%m-%d %H:%M:%S", *, precision: int = 0, utc: bool = False
    ) -> str:
        if self.is_infinite():
            if self < 0:
                return "-inf"
            return "+inf"

        i = int(self)
        r = self - i
        if fmt == "@":
            res = "@" + str(i)
        else:
            res = _time.strftime(fmt, _time.gmtime(i) if utc else _time.localtime(i))
        if precision > 0:
            x = str(r)[2 : precision + 2]
            res += "." + x + "0" * (precision - len(x))
        return res


at_timestamp_re = _re.compile(r"@(\d+)(?:\.(\d+))?")
iso_timestamp_re = _re.compile(
    r"(\d\d\d\d)(?:[_-]?(\d\d)(?:[_-]?(\d\d)(?:[T_-]?\s*(\d\d)(?:[h:_-]?(\d\d)(?:[h:_-]?(\d\d)(?:[sd,.]?(\d+))?)?\s*(?:([_+-])?(\d\d)[:h]?(\d\d)m?)?)?)?)?)?"
)


def parse_Timestamp(value: str, *, utc: bool = False) -> tuple[tuple[Timestamp, Timestamp], str]:
    """Parse a given string `value` into a pair of `Timestamp` values which
    represent the start and the end (non-inclusive) of the continiuous time
    interval for which all timestamps can be described as being part of
    given `value`.

    E.g.
    - `parse_Timestamp("2024") == (timestamp("2024-01-01 00:00:00"), timestamp("2025-01-01 00:00:00")), ""`
    - `parse_Timestamp("2024-12") == (timestamp("2024-12-01 00:00:00"), timestamp("2025-01-01 00:00:00")), ""`
    - `parse_Timestamp("2024-12-01 12:00:16") == (timestamp("2024-12-01 12:00:16"), timestamp("2024-12-01 12:00:17")), ""`
    - `parse_Timestamp("2024-12-01 12:00:16.5") == (timestamp("2024-12-01 12:00:16.5"), timestamp("2024-12-01 12:00:16.6")), ""`

    Also, return leftover part of `value`.

    When the `value` includes no time zone information, it is interpreted as local time, unless `utc` is set.
    """

    ending = True
    m = at_timestamp_re.match(value)
    if m is not None:
        hs_, rs = m.groups()
        hs = es = int(hs_)
    else:
        m = iso_timestamp_re.match(value)
        if m is not None:
            year, month, day, hour, minute, second, rs, sign, tzhour, tzminute = m.groups()
            res = (
                int(year),
                int(month) if month is not None else 1,
                int(day) if day is not None else 1,
                int(hour) if hour is not None else 0,
                int(minute) if minute is not None else 0,
                int(second) if second is not None else 0,
                0,
                1,
                -1,
            )

            hts = _time.struct_time(res)

            if month is None:
                ets = _time.struct_time((res[0] + 1, *res[1:]))
                ending = False
            elif day is None:
                if res[1] < 12:
                    ets = _time.struct_time((res[0], res[1] + 1, *res[2:]))
                else:
                    ets = _time.struct_time((res[0] + 1, 1, *res[2:]))
                ending = False

            if tzhour is not None:
                offset = (1 if sign == "+" else -1) * (3600 * int(tzhour) + 60 * int(tzminute))
                utc = True
            else:
                offset = 0

            if utc:
                hs = int(_calendar.timegm(hts)) - offset
                es = hs if ending else int(_calendar.timegm(ets)) - offset
            else:
                hs = int(_time.mktime(hts))
                es = hs if ending else int(_time.mktime(ets))

            if ending:
                if hour is None:
                    es += 86400
                    ending = False
                elif minute is None:
                    es += 3600
                    ending = False
                elif second is None:
                    es += 60
                    ending = False
        else:
            raise _p.ParseError("failed to parse `%s` as a timestamp", value)

    if rs is not None:
        r, rp = int(rs), len(rs)
    else:
        r, rp = 0, 0

    hrem = _dec.Decimal(r) / (10**rp)
    erem = _dec.Decimal(r + 1) / (10**rp) if ending else _dec.Decimal(0)

    return (Timestamp(_dec.Decimal(hs) + hrem), Timestamp(_dec.Decimal(es) + erem)), value[
        m.span()[1] :
    ]


def timestamp(value: str, start: bool = True, *, utc: bool = False) -> Timestamp:
    """A simple wrapper over `parse_Timestamp`."""
    (sres, eres), left = parse_Timestamp(value, utc=utc)
    if len(left) > 0:
        raise _p.ParseError("failed to parse `%s` as a timestamp", value)
    return sres if start else eres


def test_parse_Timestamp() -> None:
    def check(xs: str | list[str], value: Timestamp, leftover: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            (res, _), left = parse_Timestamp(x, utc=True)
            if (res, left) != (value, leftover):
                raise _f.CatastrophicFailure(
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
            raise _f.CatastrophicFailure(
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


timerange_pre_re = _re.compile(r"[([{<]?")
timerange_post_re = _re.compile(r"[)\]}>]?")
timerange_delimiter_re = _re.compile("--?")


@_dc.dataclass
class Timerange:
    """Continious time interval between two `Timestamp` timestamps."""

    start: Timestamp
    end: Timestamp
    includes_start: bool = _dc.field(default=True)
    includes_end: bool = _dc.field(default=False)

    def __contains__(self, value: Timestamp) -> bool:
        if self.includes_start and value == self.start or self.includes_end and value == self.end:
            return True
        return self.start < value < self.end

    @property
    def middle(self) -> Timestamp:
        return Timestamp((self.start + self.end) / 2)

    @property
    def delta(self) -> _dec.Decimal:
        return self.end - self.start

    def format(
        self, fmt: str = "%Y-%m-%d %H:%M:%S", *, precision: int = 0, utc: bool = False
    ) -> str:
        return (
            self.start.format(fmt, precision=precision, utc=utc)
            + "--"
            + self.end.format(fmt, precision=precision, utc=utc)
        )

    def __repr__(self) -> str:
        return f"<Timerange {'[' if self.includes_start else '('}{self.format(precision=9, utc=True)}{']' if self.includes_end else ')'}>"

    def format_org_delta(self, precision: int = 0) -> str:
        r = self.delta
        hours = r // 3600
        r = r % 3600
        minutes = r // 60
        r = r % 60
        seconds = int(r)
        r = r - seconds
        res = str(hours) + ":" + format(minutes, "02") + ":" + format(seconds, "02")
        if precision > 0:
            x = str(r)[2 : precision + 2]
            res += "." + x + "0" * (precision - len(x))
        return res

    def format_org(self, *, precision: int = 0, utc: bool = False) -> str:
        return f"[{self.start.format(precision=precision, utc=utc)}]--[{self.end.format(precision=precision, utc=utc)}] => {self.format_org_delta(precision=precision)}"


anytime = Timerange(Timestamp("-inf"), Timestamp("+inf"), True, True)


def parse_Timerange(value: str, *, utc: bool = False) -> tuple[Timerange, str]:
    """Parse a given string `value` into `Timerange`."""
    p = _p.Parser(value)
    if p.opt_string("*"):
        return anytime, p.leftovers
    try:
        p.opt_regex(timerange_pre_re)
        start, end = p.chomp(parse_Timestamp, utc=utc)
        stop = p.opt_string("*")
        p.opt_regex(timerange_post_re)
        if not stop:
            try:
                p.regex(timerange_delimiter_re)
            except _p.ParseError:
                pass
            else:
                p.opt_regex(timerange_pre_re)
                _, end = p.chomp(parse_Timestamp, utc=utc)
                p.opt_regex(timerange_post_re)
        return Timerange(start, end), p.leftovers
    except _p.ParseError as exc:
        raise _p.ParseError("failed to parse `%s` as a time interval", value) from exc


def timerange(value: str, utc: bool = False) -> Timerange:
    """A simple wrapper over `parse_Timerange`."""
    res, left = parse_Timerange(value, utc=utc)
    if len(left) > 0:
        raise _p.ParseError("failed to parse `%s` as a time interval", value)
    return res


def test_parse_Timerange() -> None:
    def check(xs: str | list[str], value: Timerange, leftover: str = "") -> None:
        if isinstance(xs, str):
            xs = [xs]
        for x in xs:
            res = parse_Timerange(x, utc=True)
            if res != (value, leftover):
                raise _f.CatastrophicFailure(
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
