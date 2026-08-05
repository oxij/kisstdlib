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

from functools import total_ordering as _total_ordering
from string import Formatter as _Formatter

from .base import (
    Decimal as _Decimal,
    MINUTE as _MINUTE,
    HOUR as _HOUR,
    DAY as _DAY,
    MILLI as _MILLI,
    NANO as _NANO,
)
from . import failure as _f
from . import parsing as _p


class TimeFormatter(_Formatter):
    """A `time.strftime`-alike `string.Formatter` implementation.

    See `TimeStamp.format` for more info.
    """

    default_time_fmt = "{Y:04}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}{f}"
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

        try:
            return args[TimeFormatter._map[key]]
        except KeyError:
            pass

        return _time.strftime("%" + key, args)


_TimeFormatter = TimeFormatter()


class TimeValue(_Decimal):
    """Generic time value of arbitrary precision."""

    @staticmethod
    def from_now() -> "TimeValue":
        raise NotImplementedError()

    def to_TimeStamp(self) -> "TimeStamp":
        raise NotImplementedError()

    def is_neg_inf(self) -> bool:
        return self.is_infinite() and self < 0

    def is_pos_inf(self) -> bool:
        return self.is_infinite() and self > 0


# Parsing regexes
_at_timestamp_re = _re.compile(r"@(\d+)(?:\.(\d+))?")
_iso_like_timestamp_re = _re.compile(
    r"(\d\d\d\d)(?:[_-]?(\d\d)(?:[_-]?(\d\d)(?:[T_-]?\s*(\d\d)(?:[h:_-]?(\d\d)(?:[h:_-]?(\d\d)(?:[sd,.]?(\d+))?)?\s*(?:([_+-])?(\d\d)[:h]?(\d\d)m?)?)?)?)?)?"
)
_timestamp_pre_re = _re.compile(r"[([{<]")
_timestamp_post_re = _re.compile(r"[)\]}>]")


class TimeStamp(TimeValue):
    """Seconds since UNIX epoch, with arbitrary precision."""

    @staticmethod
    def from_ms(value: int) -> "TimeStamp":
        return TimeStamp(_Decimal(value) * _MILLI)

    @staticmethod
    def from_ns(value: int) -> "TimeStamp":
        return TimeStamp(_Decimal(value) * _NANO)

    @staticmethod
    def from_now() -> "TimeStamp":
        return TimeStamp.from_ns(_time.time_ns())

    def to_TimeStamp(self) -> "TimeStamp":
        return self

    def format(
        self,
        fmt: str = TimeFormatter.default_time_fmt,
        precision: int | None = None,
        *,
        utc: bool = False,
        formatter: _Formatter = _TimeFormatter,
        **kwargs: _t.Any,
    ) -> str:
        """Format `self: TimeStamp` into a human-readable string by using given formatting options.

        The `fmt` argument uses the `str.format`/`string.Formatter` formatting, while supporting all
        the same directives as `time.strftime`, with the following additions/modifications:

        - The "f" directive (`str`) gets replaced by the sub-second floating point remainder of "s"
          (UNIX epoch) or "S" (seconds) directives.

          Thus, floating point UNIX epoch value can be produced with "{s}{f}" and floating point number
          of seconds can be produced with "{S}{f}".

          The number of digits after the floating point is controlled by "precision" `kwargs` element. If
          that value is `None`, the natural precision of `self` is used. If "precision" is `0` or less,
          "f" will be an empty string. The natural precision is the default.

          The "decimal_point" `kwargs` element controls the symbol used as a prefix for non-empty
          resulting values of "f". The `"."` is the default.
        """
        t = self
        if t.is_infinite():
            if t < 0:
                return "-inf"
            return "+inf"

        i = int(t)
        st = _time.gmtime(i) if utc else _time.localtime(i)

        kwargs["s"] = i
        kwargs["remainder"] = _Decimal(t) - i
        kwargs["precision"] = precision

        return formatter.vformat(fmt, st, kwargs)

    def __str__(self) -> str:
        return f"[{self.format(utc=True)}]"

    def __repr__(self) -> str:
        return f"<TimeStamp {str(self)}>"

    def __add__(self, value: int | float | _Decimal) -> "TimeStamp":
        if isinstance(value, float):
            value = _Decimal(value)
        return TimeStamp(_Decimal.__add__(self, value))

    def __sub__(self, value: int | float | _Decimal) -> "TimeStamp":
        if isinstance(value, float):
            value = _Decimal(value)
        return TimeStamp(_Decimal.__sub__(self, value))

    @staticmethod
    def parse_absolute(  # pylint: disable=unused-argument
        p: _p.Parser, *, utc: bool = False
    ) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse an input in `@%s` format into a pair of `TimeStamp`s representing an interval determined by
        the number of digits after the dot, if any. See `TimeStamp.format` and `TimeStamp.parse2`
        for more info.
        """
        ti, tr = p.regex(_at_timestamp_re)
        assert ti is not None
        t = int(ti)
        if tr is not None:
            r = int(tr)
            rp = len(tr)
        else:
            r = rp = 0

        sr = _Decimal(r) / (10**rp)
        er = _Decimal(r + 1) / (10**rp)

        return TimeStamp(_Decimal(t) + sr), TimeStamp(_Decimal(t) + er)

    @staticmethod
    def parse_iso_like(p: _p.Parser, *, utc: bool = False) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse inputs in ISO 8601 and a number of similar formats into a pair of `TimeStamp`s representing
        the interval determined by how much of the date is specified by the input string. See
        `TimeStamp.format` and `TimeStamp.parse2` for more info.
        """
        year, month, day, hour, minute, second, rs, sign, tzhour, tzminute = p.regex(
            _iso_like_timestamp_re
        )
        assert year is not None
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

        if tzhour is not None:
            assert tzminute is not None
            offset = (1 if sign == "+" else -1) * (int(tzhour) * _HOUR + int(tzminute) * _MINUTE)
            utc = True
        else:
            offset = 0

        if utc:
            st = et = int(_calendar.timegm(sst)) - offset
            if not ending:
                et = int(_calendar.timegm(est)) - offset
        else:
            st = et = int(_time.mktime(sst))
            if not ending:
                et = int(_time.mktime(est))

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

        return TimeStamp(_Decimal(st) + sr), TimeStamp(_Decimal(et) + er)

    parse_bare2 = _p.Parser.mk_choice(parse_absolute, parse_iso_like)
    parse_bare2.__doc__ = """`TimeStamp.parse2` that only accepts bare values, without them being wrapped in braces."""

    @staticmethod
    def parse2(p: _p.Parser, *, utc: bool = False) -> tuple["TimeStamp", "TimeStamp"]:
        """Parse a string into a pair of `TimeStamp` values which represent the inclusive start and the
        non-inclusive end of the continuous time interval for which all timestamps contained in it
        can be described as being part of given input.

        E.g.:

        - `parse(TimeStamp.parse2, "2024") == (timestamp("2024-01-01 00:00:00"), timestamp("2025-01-01 00:00:00"))`
        - `parse(TimeStamp.parse2, "2024-12") == (timestamp("2024-12-01 00:00:00"), timestamp("2025-01-01 00:00:00"))`
        - `parse(TimeStamp.parse2, "2024-12-01 12:00:16") == (timestamp("2024-12-01 12:00:16"), timestamp("2024-12-01 12:00:17"))`
        - `parse(TimeStamp.parse2, "2024-12-01 12:00:16.5") == (timestamp("2024-12-01 12:00:16.5"), timestamp("2024-12-01 12:00:16.6"))`

        If the input specifies time zone offset, the resulting `TimeStamp`s will use that.
        """
        p.skip_optional_regex(_timestamp_pre_re)
        res = TimeStamp.parse_bare2(p, utc=utc)
        p.skip_optional_regex(_timestamp_post_re)
        return res


def timestamp(value: str, *, utc: bool = False) -> TimeStamp:
    """A simple wrapper over `TimeStamp.parse2`."""
    return _p.run_parser(TimeStamp.parse2, True, value, utc=utc)[0][0]


# Parsing regexes
_timerange_delimiter_re = _re.compile("--?")


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
        return TimeStamp((self.start + self.end) / 2)

    @property
    def delta(self) -> _Decimal:
        """The length of the interval."""
        return _Decimal(self.end) - self.start

    # Printing

    def format(
        self,
        fmt: str = TimeFormatter.default_time_fmt,
        range_fmt: str = "{0}--{1}",
        precision: int | None = None,
        *,
        utc: bool = False,
        **kwargs: _t.Any,
    ) -> str:
        """Format `TimeRange` into a human-readable string by using given formatting options."""
        return range_fmt.format(
            self.start.format(fmt, precision, utc=utc, **kwargs),
            self.end.format(fmt, precision, utc=utc, **kwargs),
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
        delta_fmt: str = TimeFormatter.default_delta_fmt,
        range_fmt: str = "{0} -- {1} => {2}",
        precision: int | None = None,
        *,
        utc: bool = False,
        **kwargs: _t.Any,
    ) -> str:
        """Format `TimeRange` and its length into a human-readable string by using given formatting options.

        See `TimeRange.format` and `TimeRange.format_delta` for more info.
        """
        return range_fmt.format(
            self.start.format(fmt, precision, utc=utc, **kwargs),
            self.end.format(fmt, precision, utc=utc, **kwargs),
            self.format_delta(delta_fmt, precision, **kwargs),
        )

    def format_org(self, *, utc: bool = False, **kwargs: _t.Any) -> str:
        """Format `TimeRange` by using the format used by Emacs org-mode."""
        return self.format3(
            "{Y:04}-{m:02}-{d:02} {a} {H:02}:{M:02}",
            "{H}:{M:02}",
            "[{0}]--[{1}] => {2:>5}",
            utc=utc,
            **kwargs,
        )

    def __str__(self) -> str:
        return f"{'[' if self.includes_start else '('}{self.format(utc=True)}{']' if self.includes_end else ')'}"

    def __repr__(self) -> str:
        return f"<TimeRange {str(self)}>"

    @staticmethod
    def parse(p: _p.Parser, *, utc: bool = False) -> "TimeRange":
        """Parse a given string `value` into `TimeRange`."""
        if p.optional_string("*"):
            return anytime
        p.skip_optional_regex(_timestamp_pre_re)
        start, end = TimeStamp.parse_bare2(p, utc=utc)
        stop = p.optional_string("*")
        p.skip_optional_regex(_timestamp_post_re)
        if not stop and p.skip_optional_regex(_timerange_delimiter_re):
            p.skip_optional_regex(_timestamp_pre_re)
            _, end = TimeStamp.parse_bare2(p, utc=utc)
            p.skip_optional_regex(_timestamp_post_re)
        return TimeRange(start, end)


anytime = TimeRange(TimeStamp("-inf"), TimeStamp("+inf"), True, True)


def timerange(value: str, *, utc: bool = False) -> TimeRange:
    """A simple wrapper over `TimeRange.parse`."""
    return _p.run_parser(TimeRange.parse, True, value, utc=utc)[0]
