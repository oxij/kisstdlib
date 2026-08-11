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

"""Time-related things."""

import calendar as _calendar
import dataclasses as _dc
import re as _re
import time as _time
import typing as _t

from decimal import Decimal as _Decimal, InvalidOperation as _InvalidOperation
from functools import total_ordering as _total_ordering
from string import Formatter as _Formatter

from .base import (
    MINUTE as _MINUTE,
    HOUR as _HOUR,
    DAY as _DAY,
    WEEK as _WEEK,
    MILLI as _MILLI,
    MICRO as _MICRO,
    NANO as _NANO,
)
from . import failure as _f
from . import parsing as _p


def _gmtoff_to_timezone_str(gmtoff: int) -> str:
    if gmtoff >= 0:
        s = "+"
    else:
        gmtoff = -gmtoff
        s = "-"
    hours = gmtoff // _HOUR
    gmtoff = gmtoff % _HOUR
    minutes = gmtoff // _MINUTE
    gmtoff = gmtoff % _MINUTE
    seconds = int(gmtoff)
    tz = f"{s}{hours:02}{minutes:02}"
    if seconds > 0:
        tz += f"{seconds:02}"
    return tz


class TimeFormatter(_Formatter):
    """A `time.strftime`-alike `string.Formatter` implementation.

    See `TimeStamp.format` for more info.
    """

    default_time_fmt = "{Y:04}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}{f} {z}"
    default_inf_fmt = "@{s} {z}"
    default_delta_fmt = "{sign}{H}:{M:02}:{S:02}{f}"

    _map: dict[str, int] = {"Y": 0, "m": 1, "d": 2, "H": 3, "M": 4, "S": 5}

    def get_value(
        self, key: int | str, args: _t.Sequence[_t.Any], kwargs: _t.Mapping[str, _t.Any]
    ) -> _t.Any:
        if not isinstance(key, str):
            raise KeyError()

        try:
            return kwargs[key]
        except KeyError:
            pass

        if key == "f":
            r: _Decimal = kwargs["remainder"]
            precision: int = kwargs.get("precision", None)

            if precision is None:
                rs = str(r)[2:]
            elif precision > 0:
                x = str(r)[2 : precision + 2]
                rs = x + "0" * (precision - len(x))
            else:
                rs = ""

            if len(rs) == 0:
                return rs
            return kwargs.get("decimal_point", ".") + rs

        if not isinstance(args, _time.struct_time):
            raise ValueError()

        if key == "z":
            return _gmtoff_to_timezone_str(args.tm_gmtoff)

        try:
            return args[TimeFormatter._map[key]]
        except KeyError:
            pass

        return _time.strftime("%" + key, args)


_TimeFormatter = TimeFormatter()


# Parsing regexes
_at_timestamp_re = _re.compile(r"@([+-]?(?:\d+(?:\.(\d+))?|inf))")
_iso_like_datetime_re = _re.compile(
    r"""
# year
(\d\d\d\d)(?:y(?:ears?)?)?(?:
# month
[\s_-]?(\d\d)(?:m(?:o(?:n(?:ths?)?)?)?)?(?:
# day
[\s_-]?(\d\d)(?:d(?:ays?)?)?(?:
# day name
(?:[\s_-][^\s\d_-]+)?
# hour
[\s_-]?T?(\d\d)(?:h(?:ours?)?)?(?:
# minute
[:\s_-]?(\d\d)(?:m(?:in(?:utes?)?)?)?(?:
# second
[:\s_-]?(\d\d)(?:[.,]?(\d+)?)?(?:s(?:ec(?:onds?)?)?)?
)?)?)?)?)?
""",
    _re.VERBOSE | _re.IGNORECASE,
)
_iso_like_timezone_re = _re.compile(
    r"""
(?:\s*|_*)(?:
Z|
# tzsign, tzhour
([+-])(\d\d)(?:h(?:ours?)?)?(?:
# tzminute
[:\s_-]?(\d\d)(?:m(?:in(?:utes?)?)?)?(?:
# tzsecond
[:\s_-]?(\d\d)(?:s(?:ec(?:onds?)?)?)?
)?)?
)
""",
    _re.VERBOSE | _re.IGNORECASE,
)
_timestamp_pre_re = _re.compile(r"[([{<]")
_timestamp_post_re = _re.compile(r"[)\]}>]")


def _ts_to_struct_time(
    i: int, ts_gmtoff: int, gmtoff: int | None | _t.Literal["saved"] = None
) -> _time.struct_time:
    gmtoff = ts_gmtoff if gmtoff == "saved" else gmtoff
    if gmtoff is None:
        return _time.localtime(i)
    return _time.struct_time((*_time.gmtime(i + gmtoff)[:9], "", gmtoff))


def _timezone_to_gmtoff(tz: tuple[str | None, ...]) -> int:
    tzsign, tzhour, tzminute, tzsecond = tz
    return (1 if tzsign == "+" else -1) * (
        (int(tzhour) if tzhour is not None else 0) * _HOUR
        + (int(tzminute) * _MINUTE if tzminute is not None else 0)
        + (int(tzsecond) if tzsecond is not None else 0)
    )


class TimeStamp(_Decimal):
    """UNIX Epoch (a number of seconds since seconds since 1970-01-01 00:00:00 UTC) up to arbitrary
    precision.

    In its `gmtoff` attribute this class preserves the original time zone offset, if any, the
    instance value originates from. `gmtoff` can be set manually, taken from `time.localtime`, or
    taken from a parsed string, when its format specifies its time zone offset.

    Note, however, that `gmtoff` it is only ever really used in formatting. `TimeStamp`s are in UTC,
    so all comparisons between `TimeStamp`s and computations on them completely ignore `gmtoff`s,
    just copying those values around as needed to preserve them, until those values need to be
    printed.

    And even then, `TimeStamp.format` function allows a different `gmtoff` to be used when
    formatting, which is actually how it works by default, using local time zone offset by default
    instead.
    """

    gmtoff: int

    def __new__(cls, value: int | float | _Decimal | str, gmtoff: int | None = None) -> "TimeStamp":
        self = super().__new__(cls, value)
        if gmtoff is None:
            gmtoff = 0 if self.is_infinite() else _time.localtime(int(self)).tm_gmtoff
        self.gmtoff = gmtoff
        return self

    # Additional constructors

    @staticmethod
    def from_ms(value: int, gmtoff: int | None = None) -> "TimeStamp":
        """Convert milliseconds from UNIX Epoch to a `TimeStamp`."""
        return TimeStamp(_Decimal(value) * _MILLI, gmtoff)

    @staticmethod
    def from_ns(value: int, gmtoff: int | None = None) -> "TimeStamp":
        """Convert nanoseconds from UNIX Epoch to a `TimeStamp`."""
        return TimeStamp(_Decimal(value) * _NANO, gmtoff)

    @staticmethod
    def from_now(gmtoff: int | None = None) -> "TimeStamp":
        """Capture current time as a `TimeStamp`."""
        return TimeStamp.from_ns(_time.time_ns(), gmtoff)

    # Operations

    def __add__(self, value: int | float | _Decimal) -> "TimeStamp":
        if isinstance(value, float):
            value = _Decimal(value)
        return TimeStamp(_Decimal.__add__(self, value), self.gmtoff)

    def __sub__(self, value: int | float | _Decimal) -> "TimeStamp":
        if isinstance(value, float):
            value = _Decimal(value)
        return TimeStamp(_Decimal.__sub__(self, value), self.gmtoff)

    # Printing

    def format(
        self,
        fmt: str = TimeFormatter.default_time_fmt,
        inf_fmt: str = TimeFormatter.default_inf_fmt,
        precision: int | None = None,
        gmtoff: int | None | _t.Literal["saved"] = None,
        *,
        formatter: _Formatter = _TimeFormatter,
        **kwargs: _t.Any,
    ) -> str:
        """Format `self: TimeStamp` into a human-readable string by using given formatting options.

        The `fmt` and `inf_fmt` arguments use the `str.format`/`string.Formatter` formatting, while
        supporting all the same directives as `time.strftime`, with the following
        additions/modifications:

        - The "f" directive (`str`) gets replaced by the sub-second floating point remainder of "s"
          (UNIX epoch) or "S" (seconds) directives.

          Thus, floating point UNIX epoch value can be produced with "{s}{f}" and floating point number
          of seconds can be produced with "{S}{f}".

          The number of digits after the floating point is controlled by "precision" `kwargs` element. If
          that value is `None`, the natural precision of `self` is used. If "precision" is `0` or less,
          "f" will be an empty string. The natural precision is the default.

          The "decimal_point" `kwargs` element controls the symbol used as a prefix for non-empty
          resulting values of "f". The `"."` is the default.

        - The "%z" directive (`str`) is formatted as "[+-]HHMMSS" when sub-minute precision is needed.
          When it's not, the normal "[+-]HHMM" format is used.

        The `gmtoff` argument controls the time zone of the output:

        - If `gmtoff` is an `int`, its value will be used as the time zone offset, ignoring the
          saved value of `self.gmtoff` completely.

        - If `gmtoff` is `"saved"` or if `gmtoff` is `None` and `self` is infinite, the saved value
          of `self.gmtoff` will be used as `gmtoff`.

        - If `gmtoff` is `None` and `self` is finite, the output will be formatted in local time.

        For finite timestamps, the latter option is the default. For infinite timestamp, the middle
        option is the default.

        """
        t = self
        if t.is_infinite():
            gmtoff = self.gmtoff if gmtoff is None or gmtoff == "saved" else gmtoff
            st = _time.struct_time((1, 1, 1, 0, 0, 0, 0, 1, 0, "", gmtoff))

            kwargs["s"] = "-inf" if t < 0 else "+inf"
            kwargs["f"] = ""

            return formatter.vformat(inf_fmt, st, kwargs)

        i = int(t)
        st = _ts_to_struct_time(i, self.gmtoff, gmtoff)

        kwargs["s"] = i
        kwargs["remainder"] = _Decimal(t) - i
        kwargs["precision"] = precision

        return formatter.vformat(fmt, st, kwargs)

    def __str__(self) -> str:
        return f"[{self.format(gmtoff=0)}]"

    def __repr__(self) -> str:
        return f"<TimeStamp {str(self)}>"

    # Parsing

    @staticmethod
    def _parse_timezone(
        p: _p.Parser, gmtoff: int | None = None, parse_gmtoff: bool | None = None
    ) -> int | None:
        tz = (
            None
            if parse_gmtoff is False
            else (p.regex if parse_gmtoff is True else p.optional_regex)(_iso_like_timezone_re)
        )
        if tz is not None:
            gmtoff = _timezone_to_gmtoff(tz)
        return gmtoff

    @staticmethod
    def parse_absolute(
        p: _p.Parser, gmtoff: int | None = None, parse_gmtoff: bool | None = None
    ) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse an input in `@%s` format into a pair of `TimeStamp`s representing an interval determined by
        the number of digits after the decimal point, if any. See `TimeStamp.format` and `TimeStamp.parse2`
        for more info.
        """
        whole, rs = p.regex(_at_timestamp_re)
        assert whole is not None

        gmtoff = TimeStamp._parse_timezone(p, gmtoff, parse_gmtoff)

        d = _Decimal(whole)
        e = _Decimal(1) / (10 ** (len(rs))) if rs is not None else 1

        return TimeStamp(d, gmtoff), TimeStamp(d + e, gmtoff)

    @staticmethod
    def parse_iso_like(
        p: _p.Parser, gmtoff: int | None = None, parse_gmtoff: bool | None = None
    ) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse inputs in ISO 8601 and a number of similar formats into a pair of `TimeStamp`s representing
        the interval determined by how much of the date is specified by the input string. See
        `TimeStamp.format` and `TimeStamp.parse2` for more info.
        """
        year, month, day, hour, minute, second, rs = p.regex(_iso_like_datetime_re)
        assert year is not None

        gmtoff = TimeStamp._parse_timezone(p, gmtoff, parse_gmtoff)

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

        sst = _time.struct_time(res)
        est: _time.struct_time
        ending = True

        if month is None:
            est = _time.struct_time((res[0] + 1, *res[1:]))
            ending = False
        elif day is None:
            if res[1] < 12:
                est = _time.struct_time((res[0], res[1] + 1, *res[2:]))
            else:
                est = _time.struct_time((res[0] + 1, 1, *res[2:]))
            ending = False

        if gmtoff is not None:
            st = et = int(_calendar.timegm(sst)) - gmtoff
            if not ending:
                et = int(_calendar.timegm(est)) - gmtoff
            egmtoff = gmtoff
        else:
            stg = etg = int(_calendar.timegm(sst))
            st = et = int(_time.mktime(sst))
            gmtoff = egmtoff = st - stg
            if not ending:
                etg = int(_calendar.timegm(est))
                et = int(_time.mktime(est))
                egmtoff = et - etg

        if ending:
            if hour is None:
                et += _DAY
                ending = False
            elif minute is None:
                et += _HOUR
                ending = False
            elif second is None:
                et += _MINUTE
                ending = False

        if rs is not None:
            r = int(rs)
            rp = len(rs)
        else:
            r = rp = 0

        sr = _Decimal(r) / (10**rp)
        er = _Decimal(r + 1) / (10**rp) if ending else _Decimal(0)

        return TimeStamp(_Decimal(st) + sr, gmtoff), TimeStamp(_Decimal(et) + er, egmtoff)

    parse_bare2 = _p.Parser.mk_choice(parse_absolute, parse_iso_like)
    parse_bare2.__doc__ = """`TimeStamp.parse2` that only accepts bare values, without them being wrapped in braces."""

    @staticmethod
    def parse2(
        p: _p.Parser, gmtoff: int | None = None, parse_gmtoff: bool | None = None
    ) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse a string into a pair of `TimeStamp` values which represent the inclusive start and the
        non-inclusive end of the continuous time interval for which all timestamps contained in it
        can be described as being part of given input.

        E.g.:

        - `parse(TimeStamp.parse2, "2024") == (timestamp("2024-01-01 00:00:00"), timestamp("2025-01-01 00:00:00"))`
        - `parse(TimeStamp.parse2, "2024-12") == (timestamp("2024-12-01 00:00:00"), timestamp("2025-01-01 00:00:00"))`
        - `parse(TimeStamp.parse2, "2024-12-01 12:00:16") == (timestamp("2024-12-01 12:00:16"), timestamp("2024-12-01 12:00:17"))`
        - `parse(TimeStamp.parse2, "2024-12-01 12:00:16.5") == (timestamp("2024-12-01 12:00:16.5"), timestamp("2024-12-01 12:00:16.6"))`

        Moreover:

        - If `parse_gmtoff` is `True`, the input will be required to specify its time zone offset.

        - If `parse_gmtoff` is `None`, which is the default, the input can optionally specify its
          time zone offset.

        - If `parse_gmtoff` is `False`, time zone offset won't be parsed at all (thus, if the input
          does specify it, that part of the input will be left unparsed).

        If the input specifies its time zone offset, the resulting `TimeStamp`s will use that.
        Otherwise, the value of `gmtoff` argument will be used. Thus, input's time zone offset, if
        any, has higher priority.
        """
        p.skip_optional_regex(_timestamp_pre_re)
        res = TimeStamp.parse_bare2(p, gmtoff, parse_gmtoff)
        p.skip_optional_regex(_timestamp_post_re)
        return res


def timestamp(value: str, gmtoff: int | None = None, parse_gmtoff: bool | None = None) -> TimeStamp:
    """A simple wrapper over `TimeStamp.parse2`."""
    return _p.run_parser(TimeStamp.parse2, True, value, gmtoff, parse_gmtoff)[0][0]


# Parsing regexes
_timefun_whitespace_re = _re.compile(r"[\s_]*")
_timefun_head_re = _re.compile(
    r"""
(now)|
(today)|
(yesterday)|
(tomorrow)|
(this)|
(last|prev(?:ious)?)|
(next|following)
""",
    _re.VERBOSE | _re.IGNORECASE,
)
_timefun_sign_re = _re.compile(r"([+-])")
_timefun_value_re = _re.compile(r"(\d+)(?:\.(\d+))?")
_timefun_unit_re = _re.compile(
    r"""
# years
(y(?:ears?)?)|
# months
(m(?![isu])(?:o(?:n(?:ths?)?)?)?)|
# weeks
(w(?:eeks?)?)|
# days
(d(?:ays?)?)|
# hours
(h(?:ours?)?)|
# minutes
(mi(?:n(?:utes?)?)?)|
# seconds
(s(?:ec(?:onds?)?)?)|
# milliseconds
(ms|millis(?:ec(?:onds?)?)?)|
# microseconds
(mus|micros(?:ec(?:onds?)?)?)|
# nanoseconds
(ns|nanos(?:ec(?:onds?)?)?)
""",
    _re.VERBOSE | _re.IGNORECASE,
)

type TimeUnitLiteral = _t.Literal["y", "m", "w", "d", "h", "min", "s", "ms", "mus", "ns"]


class TimeUnit:
    """A value representing a unit of time."""

    unit: TimeUnitLiteral

    def __init__(self, value: _t.Union["TimeUnit", TimeUnitLiteral]) -> None:
        self.unit = value.unit if isinstance(value, TimeUnit) else value

    def __eq__(self, value: _t.Any) -> bool:
        return self.unit == value.unit if isinstance(value, TimeUnit) else self.unit == value

    # Parsing

    @staticmethod
    def parse_literal(p: _p.Parser) -> TimeUnitLiteral:
        is_y, is_m, is_w, is_d, is_h, is_min, is_s, is_ms, is_mus, is_ns = p.regex(_timefun_unit_re)  # fmt: skip
        if is_y is not None:
            return "y"
        if is_m is not None:
            return "m"
        if is_w is not None:
            return "w"
        if is_d is not None:
            return "d"
        if is_h is not None:
            return "h"
        if is_min is not None:
            return "min"
        if is_s is not None:
            return "s"
        if is_ms is not None:
            return "ms"
        if is_mus is not None:
            return "mus"
        if is_ns is not None:
            return "ns"
        assert False

    @staticmethod
    def parse(p: _p.Parser) -> "TimeUnit":
        return TimeUnit(TimeUnit.parse_literal(p))

    # Printing

    def format(self) -> str:
        """Format `TimeUnit` into a human-readable string."""
        return self.unit


class TimeRounding(TimeUnit):
    """A values representing time-rounding down to a year/month/week/day/etc."""

    # Operations

    def __call__(self, st: _time.struct_time, r: _Decimal) -> tuple[_time.struct_time, _Decimal]:
        """Apply `self` to the given `_time.struct_time` and an additional sub-second remainder."""
        unit = self.unit
        if unit == "y":
            return _time.struct_time((st[0], 1, 1, 0, 0, 0, -1, -1, -1, *st[9:])), _Decimal(0)
        if unit == "m":
            return _time.struct_time((*st[0:2], 1, 0, 0, 0, -1, -1, -1, *st[9:])), _Decimal(0)
        if unit == "w":
            return _time.struct_time((*st[0:3], 0, 0, 0, -1, -1, -1, *st[9:])), _Decimal(
                -st.tm_wday * _DAY
            )
        if unit == "d":
            return _time.struct_time((*st[0:3], 0, 0, 0, -1, -1, -1, *st[9:])), _Decimal(0)
        if unit == "h":
            return _time.struct_time((*st[0:4], 0, 0, -1, -1, -1, *st[9:])), _Decimal(0)
        if unit == "min":
            return _time.struct_time((*st[0:5], 0, -1, -1, -1, *st[9:])), _Decimal(0)
        if unit == "s":
            return st, _Decimal(0)
        if unit == "ms":
            return st, _MILLI * int(r / _MILLI)
        if unit == "mus":
            return st, _MICRO * int(r / _MICRO)
        if unit == "ns":
            return st, _NANO * int(r / _NANO)
        assert False

    # Parsing

    @staticmethod
    def parse(p: _p.Parser) -> "TimeRounding":
        p.skip_optional_regex(_timefun_whitespace_re, True)
        p.string("-%")
        return TimeRounding(TimeUnit.parse_literal(p))

    # Printing

    def format(self) -> str:
        """Format `TimeRounding` into a human-readable string."""
        return f"-%{self.unit}"


@_dc.dataclass
class TimeDiff:
    """A value representing a change in time: essentially, a tuple of `[int, Decimal]` designating a
    difference in months and seconds, respectively.

    It's represented this way because months have different lengths, so to move a `TimeStamp`, e.g.,
    "one month two days forward", one needs to have both values. On the other hand, years can be
    represented as multiples of months and weeks, days, hours, and minutes can be represented as
    multiples of seconds.
    """

    months: int
    seconds: _Decimal

    def __init__(
        self,
        months: int = 0,
        seconds: int | float | _Decimal | str = _Decimal(0),
    ) -> None:
        self.months = months
        self.seconds = seconds if isinstance(seconds, _Decimal) else _Decimal(seconds)

    # Additional constructors

    @staticmethod
    def from_scalar_units(s: int | _Decimal, v: TimeUnitLiteral | TimeUnit) -> "TimeDiff":
        if v == "w":
            return TimeDiff(0, s * _WEEK)
        if v == "d":
            return TimeDiff(0, s * _DAY)
        if v == "h":
            return TimeDiff(0, s * _HOUR)
        if v == "min":
            return TimeDiff(0, s * _MINUTE)
        if v == "s":
            return TimeDiff(0, s * 1)
        if v == "ms":
            return TimeDiff(0, s * _MILLI)
        if v == "mus":
            return TimeDiff(0, s * _MICRO)
        if v == "ns":
            return TimeDiff(0, s * _NANO)

        if isinstance(s, _Decimal):
            raise ValueError()

        if v == "y":
            return TimeDiff(s * 12, 0)
        if v == "m":
            return TimeDiff(s, 0)
        assert False

    # Operations

    def __add__(self, value: "TimeDiff") -> "TimeDiff":
        return TimeDiff(self.months + value.months, self.seconds + value.seconds)

    def __sub__(self, value: "TimeDiff") -> "TimeDiff":
        return TimeDiff(self.months - value.months, self.seconds - value.seconds)

    def __call__(
        self,
        st: _time.struct_time,
        r: _Decimal,
    ) -> tuple[_time.struct_time, _Decimal]:
        """Apply `self` to the given `_time.struct_time` and an additional sub-second remainder."""
        smonths = self.months
        if smonths != 0:
            years = st[0]
            months = st[1] + smonths
            if months > 12:
                nmonths = months - 1
                years += nmonths // 12
                months = nmonths % 12 + 1
            elif months < 1:
                nmonths = 12 - months
                years -= nmonths // 12
                months = 12 - (nmonths % 12)
            st = _time.struct_time((years, months, *st[2:]))
        return st, r + self.seconds

    # Parsing

    @staticmethod
    def _parse_atom(p: _p.Parser, s: int, acc: "TimeDiff") -> None:
        vs, rs = p.regex(_timefun_value_re)
        unit = TimeUnit.parse_literal(p)

        assert vs is not None
        v: int | _Decimal = s * int(vs)
        if rs is not None:
            r = int(rs)
            rp = len(rs)
            v = _Decimal(v) + _Decimal(s * r) / (10**rp)

        try:
            update = TimeDiff.from_scalar_units(v, unit)
        except ValueError:
            p.fail("decimal values can't be used with years or months")

        acc.months += update.months
        acc.seconds += update.seconds

    @staticmethod
    def _parse_block(p: _p.Parser, acc: "TimeDiff") -> None:
        p.skip_optional_regex(_timefun_whitespace_re, True)
        (sign,) = p.regex(_timefun_sign_re)
        s = 1 if sign == "+" else -1
        for _ in p.repeat(TimeDiff._parse_atom, 1, None, s, acc):
            pass

    @staticmethod
    def parse(p: _p.Parser) -> "TimeDiff":
        """Parse a string containing zero or more blocks consisting of a sign followed by one or more time
        length atoms into a corresponding `TimeDiff` value.

        I.e., parse strings like "+1y2m3w5d6h7min8.912s" into a corresponding `TimeDiff`.

        This function does some simple arithmetic on the values it parses, so multiple signed blocks
        with arbitrarily ordered and/or repeated atoms are permitted, e.g.:
        - "-2y+6m+1d12h" will be parsed to mean the same thing as "-1y6m+1d12h";
        - "-1y1m+2m2y+0d2w1y" will be parsed as "+2y1m2w".
        """
        acc = TimeDiff()
        for _ in p.repeat(TimeDiff._parse_block, 1, None, acc):
            pass
        return acc

    # Printing

    def format(
        self,
        precision: int | None = None,
        *,
        decimal_point: str = ".",
    ) -> str:
        """Format `TimeDiff` into a human-readable string by using given formatting options.

        The result will use the same format as `TimeDiff.parse` does, but with normalization and
        atom disambiguation applied.
        """
        res = []
        sign = 0
        months_ = self.months
        seconds_ = self.seconds
        years = months = 0

        if months_ != 0:
            sign = 1 if months_ >= 0 else -1
            res.append("+" if sign > 0 else "-")

            m = abs(months_)
            years = m // 12
            months = m % 12

            if years != 0:
                res.append(f"{years}y")
            if months != 0:
                res.append(f"{months}m")

        if seconds_ != 0:
            sign2 = 1 if seconds_ >= 0 else -1
            if sign2 != sign:
                res.append("+" if sign2 > 0 else "-")

            t = abs(seconds_)
            weeks = t // _WEEK
            t = t % _WEEK
            days = t // _DAY
            t = t % _DAY
            hours = t // _HOUR
            t = t % _HOUR
            minutes = t // _MINUTE
            t = t % _MINUTE
            seconds = int(t)
            r = t - seconds

            if precision is None:
                rs = str(r)[1:]
            elif precision > 0:
                x = str(r)[2 : precision + 2]
                rs = decimal_point + x + "0" * (precision - len(x))
            else:
                rs = ""

            if weeks != 0:
                res.append(f"{weeks}w")
            if days != 0:
                res.append(f"{days}d")
            if hours != 0:
                res.append(f"{hours}h")
            if minutes != 0:
                res.append(f"{minutes}min")
            if seconds != 0 or rs:
                res.append(f"{seconds}{rs}s")

        return "".join(res)

    def __str__(self) -> str:
        return f"[{self.format()}]"

    def __repr__(self) -> str:
        return f"<TimeDiff {str(self)}>"


class TimeFun(list[TimeRounding | TimeDiff]):
    """A multi-step transformation over `TimeStamp`s: a sequence of `TimeRounding`s and/or `TimeDiff`s.

    The values of this class represent common transformations between `TimeStamp`s, e.g.:
    - "a `TimeStamp` rounded up/down to years/months/weeks/days/etc";
    - "a `TimeStamp` plus/minus some number of years/months/weeks/days/etc";
    - "the Friday following a `TimeStamp`"
      (which is the `TimeStamp` rounded up to a week plus 5 days);
    - "second Friday of the month before a `TimeStamp`"
      (which is the `TimeStamp` rounded down to a month, minus 1 month, rounded up to a week, plus 5 days);
    - etc.
    """

    # Operations

    def __call__(
        self,
        value: TimeStamp,
        gmtoff: int | None | _t.Literal["saved"] = "saved",
    ) -> TimeStamp:
        """Apply `self` to the given `TimeStamp` while performing all operations in time zone `gmtoff`.

        If `gmtoff` is `"saved"`, the value of `gmtoff` will be taken from `value.gmtoff`.

        Returns a newly constructed `TimeStamp`.
        """
        i = int(value)
        r = _Decimal(value) - i
        st = _ts_to_struct_time(i, value.gmtoff, gmtoff)
        gmtoff = st.tm_gmtoff
        i_dirty = False

        for f in self:
            if abs(r) > 1:
                ri = int(r)
                r -= ri
                i = int(_calendar.timegm(st)) + ri
                st = _time.gmtime(i)
                i_dirty = False

            st_ = st
            st, r = f(st, r)
            i_dirty = i_dirty or st is not st_

        if i_dirty:
            i = int(_calendar.timegm(st))

        return TimeStamp(r + i - gmtoff, gmtoff)

    def apply2(
        self, value: TimeStamp, gmtoff: int | None | _t.Literal["saved"] = "saved"
    ) -> tuple[TimeStamp, TimeStamp]:
        start = end = self(value, gmtoff)

        for e in reversed(self):
            if isinstance(e, TimeRounding):
                end = TimeFun([TimeDiff.from_scalar_units(1, e)])(start, gmtoff)
                break

        return start, end

    # Parsing

    @staticmethod
    def _parse_rounding(p: _p.Parser, acc: "TimeFun") -> None:
        acc.append(TimeRounding.parse(p))

    @staticmethod
    def _parse_diff(p: _p.Parser, acc: "TimeFun") -> None:
        acc.append(TimeDiff.parse(p))

    # NB: try `_parse_diff` first, since it's more common
    _parse_either = _p.Parser.mk_choice(_parse_diff, _parse_rounding)

    @staticmethod
    def parse(p: _p.Parser) -> "TimeFun":
        """Parse a sequence of one or more `TimeFun`-atoms into a `TimeFun`."""
        acc = TimeFun()
        for _ in p.repeat(TimeFun._parse_either, 1, None, acc):
            pass
        return acc

    @staticmethod
    def parse_human(p: _p.Parser) -> "TimeFun":
        """Parse a human-readable time-string (like "now", "today", "last week", etc) followed by
        `TimeFun`-atoms into a `TimeFun`.
        """

        p.skip_optional_regex(_timefun_whitespace_re, True)
        is_now, is_today, is_yesterday, is_tomorrow, _is_this, is_prev, is_next = p.regex(_timefun_head_re)  # fmt: skip

        acc = TimeFun()

        if is_now is not None:
            pass
        elif is_today is not None:
            acc.append(TimeRounding("d"))
        elif is_yesterday is not None:
            acc.append(TimeRounding("d"))
            acc.append(TimeDiff(0, -_DAY))
        elif is_tomorrow is not None:
            acc.append(TimeRounding("d"))
            acc.append(TimeDiff(0, _DAY))
        else:
            p.skip_optional_regex(_timefun_whitespace_re, True)
            unit = TimeUnit.parse_literal(p)
            acc.append(TimeRounding(unit))
            if is_prev is not None:
                acc.append(TimeDiff.from_scalar_units(-1, unit))
            elif is_next is not None:
                acc.append(TimeDiff.from_scalar_units(1, unit))

        for _ in p.repeat(TimeFun._parse_either, 0, None, acc):
            pass

        return acc

    # Printing

    def format(self, precision: int | None = None, *, decimal_point: str = ".") -> str:
        """Format `TimeFun` using given formatting options."""
        res = []
        for v in self:
            if isinstance(v, TimeRounding):
                res.append(v.format())
            elif isinstance(v, TimeDiff):
                res.append(v.format(precision, decimal_point=decimal_point))
        return "".join(res)

    def format_human(self, precision: int | None = None, *, decimal_point: str = ".") -> str:
        """Format `TimeFun` into a human-readable string using given formatting options."""
        return "now" + self.format(precision, decimal_point=decimal_point)

    def __str__(self) -> str:
        return f"[{self.format()}]"

    def __repr__(self) -> str:
        return f"<TimeFun {str(self)}>"


# Parsing regexes
_timerange_delimiter_re = _re.compile(r"\s*-+\s*")


@_total_ordering
@_dc.dataclass
class TimeRange:
    """A continuous time interval between two `TimeStamp`s."""

    start: TimeStamp
    end: TimeStamp
    includes_start: bool = _dc.field(default=True)
    includes_end: bool = _dc.field(default=False)

    # For `total_ordering`

    def __lt__(self, other: "TimeRange") -> bool:
        if self.start < other.start:
            return True
        if self.start == other.start and self.includes_start != other.includes_start:
            # NB: contra-intuitive! This is why we can't just do `@dataclass(order=True)`.
            return self.includes_start > other.includes_start
        if self.end < other.end:
            return True
        if self.end == other.end and self.includes_end != other.includes_end:
            return self.includes_end < other.includes_end
        return False

    # Operations

    def __contains__(self, value: TimeStamp) -> bool:
        if self.includes_start and value == self.start or self.includes_end and value == self.end:
            return True
        return self.start < value < self.end

    @property
    def middle(self) -> TimeStamp:
        """The exact middle of the interval."""
        s = self.start
        e = self.end
        try:
            return TimeStamp((s + e) / 2)
        except _InvalidOperation:
            if e.is_infinite():
                return e
            return s

    @property
    def delta(self) -> _Decimal:
        """The length of the interval."""
        try:
            return _Decimal(self.end) - self.start
        except _InvalidOperation:
            return _Decimal("inf")

    # Printing

    def format(
        self,
        fmt: str = TimeFormatter.default_time_fmt,
        inf_fmt: str = TimeFormatter.default_inf_fmt,
        range_fmt: str = "{0}--{1}",
        precision: int | None = None,
        gmtoff: int | None | _t.Literal["saved", "saved_start", "saved_end"] = None,
        **kwargs: _t.Any,
    ) -> str:
        """Format `TimeRange` into a human-readable string by using given formatting options.

        See `TimeStamp.format` for `gmtoff` interpretation. Then, note that this function also
        accepts `"saved_start"` and `"saved_end"` as values to `gmtoff`, both of which work
        similarly to `"saved"`, but force formatted timestamps to use the same `gmtoff`, preferring
        the value used by the `.start` or the `.end`, respectively.
        """
        if gmtoff == "saved_start":
            gmtoff = self.end.gmtoff if self.start.is_infinite() else self.start.gmtoff
        elif gmtoff == "saved_end":
            gmtoff = self.start.gmtoff if self.end.is_infinite() else self.end.gmtoff
        return range_fmt.format(
            self.start.format(fmt, inf_fmt, precision, gmtoff, **kwargs),
            self.end.format(fmt, inf_fmt, precision, gmtoff, **kwargs),
        )

    def format_delta(
        self,
        fmt: str = TimeFormatter.default_delta_fmt,
        precision: int | None = None,
        *,
        formatter: _Formatter = _TimeFormatter,
        **kwargs: _t.Any,
    ) -> str:
        """Format the length of `TimeRange` interval into a human-readable string by using given formatting
        options.

        This function uses `string.Formatter` machinery to do the formatting and the actual
        `formatter` can be overridden. The default is `formatter = TimeFormatter()`.
        """
        t = self.delta
        if t.is_infinite():
            if t < 0:
                return "-inf"
            return "+inf"

        if t < 0:
            kwargs["sign"] = "-"
            t = -t
        else:
            kwargs["sign"] = ""

        hours = t // _HOUR
        t = t % _HOUR
        minutes = t // _MINUTE
        t = t % _MINUTE
        seconds = int(t)

        kwargs["H"] = hours
        kwargs["M"] = minutes
        kwargs["S"] = seconds
        kwargs["remainder"] = t - seconds
        kwargs["precision"] = precision

        return formatter.vformat(fmt, (), kwargs)

    def format3(
        self,
        fmt: str = TimeFormatter.default_time_fmt,
        inf_fmt: str = TimeFormatter.default_inf_fmt,
        delta_fmt: str = TimeFormatter.default_delta_fmt,
        range_fmt: str = "{0} -- {1} => {2}",
        precision: int | None = None,
        gmtoff: int | None | _t.Literal["saved", "saved_start", "saved_end"] = None,
        **kwargs: _t.Any,
    ) -> str:
        """Format `TimeRange` and its length into a human-readable string by using given formatting options.

        See `TimeRange.format` and `TimeRange.format_delta` for more info.
        """
        if gmtoff == "saved_start":
            gmtoff = self.end.gmtoff if self.start.is_infinite() else self.start.gmtoff
        elif gmtoff == "saved_end":
            gmtoff = self.start.gmtoff if self.end.is_infinite() else self.end.gmtoff
        return range_fmt.format(
            self.start.format(fmt, inf_fmt, precision, gmtoff, **kwargs),
            self.end.format(fmt, inf_fmt, precision, gmtoff, **kwargs),
            self.format_delta(delta_fmt, precision, **kwargs),
        )

    def format_org(
        self,
        gmtoff: int | None | _t.Literal["saved", "saved_start", "saved_end"] = None,
        **kwargs: _t.Any,
    ) -> str:
        """Format `TimeRange` by using the format used by Emacs org-mode."""
        return self.format3(
            "{Y:04}-{m:02}-{d:02} {a} {H:02}:{M:02}",
            "@{s}",
            "{H}:{M:02}",
            "[{0}]--[{1}] => {2:>5}",
            0,
            gmtoff,
            **kwargs,
        )

    def __str__(self) -> str:
        return f"{'[' if self.includes_start else '('}{self.format(gmtoff=0)}{']' if self.includes_end else ')'}"

    def __repr__(self) -> str:
        return f"<TimeRange {str(self)}>"

    # Parsing

    @staticmethod
    def _parse1(
        p: _p.Parser,
        now: TimeStamp | None,
        prev: tuple[TimeStamp, TimeStamp] | None,
        gmtoff: int | None = None,
        parse_gmtoff: bool | None = None,
    ) -> tuple[TimeStamp | None, TimeStamp, TimeStamp, bool]:
        p.skip_optional_regex(_timestamp_pre_re)

        tf = p.optional(TimeFun.parse_human)
        if tf is not None:
            if now is None:
                now = TimeStamp.from_now(gmtoff)
            start, end = tf.apply2(now)
            wide = start is not end
        else:
            apply_to = p.optional_string_in([".^", ".$"])
            if apply_to is not None:
                if prev is None:
                    p.fail(
                        "initial `.^` and `.$` operators can only be used in the second part of the format"
                    )
                start = end = prev[0] if apply_to == ".^" else prev[1]
                wide = False

                tf = p.optional(TimeFun.parse)
                if tf is not None:
                    start, end = tf.apply2(start)
                    wide = start is not end
            else:
                start, end = TimeStamp.parse_bare2(p, gmtoff, parse_gmtoff)
                wide = p.optional_string("*") is not None

        reduce_to = p.optional_string_in([".^", ".$"])
        shift = p.optional(TimeFun.parse)
        if reduce_to is not None:
            start = end = start if reduce_to == ".^" else end
            wide = False
            if shift is not None:
                start = end = shift(start)
        elif shift is not None:
            start = shift(start)
            end = shift(end)

        p.skip_optional_regex(_timestamp_post_re)

        return now, start, end, wide

    @staticmethod
    def parse(
        p: _p.Parser,
        gmtoff: int | None = None,
        parse_gmtoff: bool | None = None,
        *,
        includes_start: bool = True,
        includes_end: bool = False,
        now: TimeStamp | None = None,
    ) -> tuple["TimeRange", bool]:
        """Parse a given string `value` into a `TimeRange` and a `bool` that signifies if the input was
        actually formatted as an interval.

        It can be used to simply wrap `TimeStamp.parse2` with an optional "*" at the end into a
        `TimeRange`:

        ```
        parse(TimeRange.parse, "2024") == TimeRange(timestamp("2024-01-01 00:00:00"), timestamp("2025-01-01 00:00:00")), False
        parse(TimeRange.parse, "2024*") == TimeRange(timestamp("2024-01-01 00:00:00"), timestamp("2025-01-01 00:00:00")), True
        ```

        But this function also admits two operators that narrow intervals back into `TimeStamps`:

        ```
        parse(TimeRange.parse, "2024*.^") == TimeRange(timestamp("2024-01-01 00:00:00"), timestamp("2024-01-01 00:00:00")), False
        parse(TimeRange.parse, "2024*.$") == TimeRange(timestamp("2025-01-01 00:00:00"), timestamp("2025-01-01 00:00:00")), False
        ```

        As well as `TimeFun`s, optionally followed by said narrowing operators:

        ```
        parse(TimeRange.parse, "today", now=now)
        parse(TimeRange.parse, "today.^", now=now)
        parse(TimeRange.parse, "today.$", now=now)
        parse(TimeRange.parse, "next year", now=now)
        parse(TimeRange.parse, "this month+1m5d", now=now)
        ```

        As well as explicit intervals:

        ```
        parse(TimeRange.parse, "*") == anytime, True
        parse(TimeRange.parse, "2024-02--2025") == parse(TimeRange.parse, "2024-02*--2025") == TimeRange(timestamp("2024-02-01 00:00:00"), timestamp("2025-01-01 00:00:00")), True
        parse(TimeRange.parse, "2024-02.$--2025") == parse(TimeRange.parse, "2024-03--2025") == TimeRange(timestamp("2024-03-01 00:00:00"), timestamp("2025-01-01 00:00:00")), True
        ```

        As well as mixes and matches of all of them:

        ```
        parse(TimeRange.parse, "2025-02-01.^+1m--last week+2d", now=now)
        parse(TimeRange.parse, "today-1m2d--.$+1w", now=now) == parse(TimeRange.parse, "today-1m2d--today-1m2d.$+1w", now=now)
        ```

        Note how a narrowing operator written right after a "--" starts its computations from the
        value before the "--".
        """
        if p.optional_string("*"):
            return anytime, True

        now, start, end, is_interval = TimeRange._parse1(p, now, None, gmtoff, parse_gmtoff)
        if p.skip_optional_regex(_timerange_delimiter_re):
            _, end, _, _ = TimeRange._parse1(p, now, (start, end), gmtoff, parse_gmtoff)
            is_interval = True

        return TimeRange(start, end, includes_start, includes_end), is_interval


anytime = TimeRange(TimeStamp("-inf"), TimeStamp("+inf"), True, True)


def timerange(
    value: str,
    gmtoff: int | None = None,
    parse_gmtoff: bool | None = None,
    *,
    includes_start: bool = True,
    includes_end: bool = False,
) -> TimeRange:
    """A simple wrapper over `TimeRange.parse`."""
    return _p.run_parser(
        TimeRange.parse,
        True,
        value,
        gmtoff,
        parse_gmtoff,
        includes_start=includes_start,
        includes_end=includes_end,
    )[0][0]
