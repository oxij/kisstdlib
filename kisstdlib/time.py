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

    default_time_fmt = "{Y:04}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}{f} {z}"
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


# Parsing regexes
_at_timestamp_re = _re.compile(r"@(\d+)(?:\.(\d+))?")
_iso_like_datetime_re = _re.compile(
    r"(\d\d\d\d)(?:[_-]?(\d\d)(?:[_-]?(\d\d)(?:[T_-]?\s*(\d\d)(?:[h:_-]?(\d\d)(?:[h:_-]?(\d\d)(?:[sd,.]?(\d+))?)?)?)?)?)?"
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
        precision: int | None = None,
        gmtoff: int | None | _t.Literal["saved"] = None,
        *,
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

        The `gmtoff` argument controls the time zone of the output:

        - If `gmtoff` is an `int`, its value will be used as the time zone offset, ignoring the
          saved value of `self.gmtoff` completely.

        - If `gmtoff` is `"saved"`, the saved value of `self.gmtoff` will be used as `gmtoff`.

        - If `gmtoff` is `None`, the output will be formatted in local time.

        The latter option is the default.
        """
        t = self
        if t.is_infinite():
            if t < 0:
                return "-inf"
            return "+inf"

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
        ti, tr = p.regex(_at_timestamp_re)
        assert ti is not None

        gmtoff = TimeStamp._parse_timezone(p, gmtoff, parse_gmtoff)

        t = int(ti)
        if tr is not None:
            r = int(tr)
            rp = len(tr)
        else:
            r = rp = 0

        sr = _Decimal(r) / (10**rp)
        er = _Decimal(r + 1) / (10**rp)

        return TimeStamp(_Decimal(t) + sr, gmtoff), TimeStamp(_Decimal(t) + er, gmtoff)

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
            self.start.format(fmt, precision, gmtoff, **kwargs),
            self.end.format(fmt, precision, gmtoff, **kwargs),
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
            self.start.format(fmt, precision, gmtoff, **kwargs),
            self.end.format(fmt, precision, gmtoff, **kwargs),
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
    def parse(
        p: _p.Parser, gmtoff: int | None = None, parse_gmtoff: bool | None = None
    ) -> "TimeRange":
        """Parse a given string `value` into `TimeRange`."""
        if p.optional_string("*"):
            return anytime
        p.skip_optional_regex(_timestamp_pre_re)
        start, end = TimeStamp.parse_bare2(p, gmtoff, parse_gmtoff)
        stop = p.optional_string("*")
        p.skip_optional_regex(_timestamp_post_re)
        if not stop and p.skip_optional_regex(_timerange_delimiter_re):
            p.skip_optional_regex(_timestamp_pre_re)
            _, end = TimeStamp.parse_bare2(p, gmtoff, parse_gmtoff)
            p.skip_optional_regex(_timestamp_post_re)
        return TimeRange(start, end)


anytime = TimeRange(TimeStamp("-inf"), TimeStamp("+inf"), True, True)


def timerange(value: str, gmtoff: int | None = None, parse_gmtoff: bool | None = None) -> TimeRange:
    """A simple wrapper over `TimeRange.parse`."""
    return _p.run_parser(TimeRange.parse, True, value, gmtoff, parse_gmtoff)[0]
