# Copyright (c) 2018-2025 Jan Malakhovski <oxij@oxij.org>
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

"""KISS IO File Object hierarchy.

What?

  An alternative to Python's `io` module.

Why?

  APIs of Python's `io` module are way too complex. It only really works well
  when you use either buffered raw or buffered textual IO and never try to mix
  them.

  The problem stems from the fact that Python's `io.RawIOBase` and
  `io.TextIOBase` are trying to give the same APIs, but they do different
  things. Which, after being multiplied with the differences of buffered and
  unbuffered `read`s and `write`s, essentially gives FOUR different file
  object semantics under the same file object API.

  Here, instead we have separate calls for `bytes` and `str` versions of
  `read` and `write` calls, buffering is completely transparent, reading and
  writing parts are split into different interfaces, and text encoding
  handling is split between them (because it has to be handled differently).

  This also provides `TIOEncoder` and (WIP `TIODecoder`) classes that can do
  simple serialization/de-serialization a-la Pascal.

"""

from .base import *
from .wrapper import *
from .encoder import *
