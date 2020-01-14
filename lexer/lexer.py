import sys
import re

from copy import copy
from pathlib import Path
from io import StringIO

import tokens
from utils import UntilNoneIterator


class Location:
    """
    Holds the information about the position of a character (in practice, the
    first character of a token) in a file or string.
    """

    def __init__(self, path, line_num, column=0):
        self.path = path
        self.line_num = line_num
        self.column = column

    def __str__(self):
        """
        >>> print(Location("foo.tjp", 2, 10))
        Location('foo.tjp', 2, 10)
        """
        return '%s(%r, %s, %s)' % (self.__class__.__name__,
                                   self.path,
                                   self.line_num,
                                   self.column)


class LineStream:
    """
    Provides an interface to get a stream of lines from either a file or a
    string. Lines are provided together with their corresponding location.
    """

    def __init__(self, source):
        if isinstance(source, str):
            self.path = None
            self.file = StringIO(source)
        elif isinstance(source, Path):
            self.path = source
            self.file = open(source, 'r')
        else:
            raise ValueError(source)
        self.line_num = 0

    def __next__(self):
        line = self.file.readline()
        if not line:
            return None
        self.line_num += 1
        return (line, Location(self.path, self.line_num))

    def __iter__(self):
        return UntilNoneIterator(self)


class LineTokenizer:
    """
    Provider an interface for tokenizing a line, producing a stream of tokens.
    Tokens are returned with their corresponding location.

    At each iteration, the list of possible tokens can be changed.

    >>> from tokens import Name, String, EndOfLine, WhiteSpace
    >>> lt = LineTokenizer()
    >>> lt.set_line('bar "wololo"\\n', Location(None, 1))
    >>> lt.set_possible_tokens([Name, String, EndOfLine, WhiteSpace])
    >>> for t, l in lt: print(t, l)
    Name('bar') Location(None, 1, 0)
    WhiteSpace(' ') Location(None, 1, 3)
    String('wololo') Location(None, 1, 4)
    EndOfLine('\\n') Location(None, 1, 12)
    """

    def __init__(self):
        self.line = ""
        self.location = Location(None, 0)
        self.set_possible_tokens([])

    def __bool__(self):
        return len(self.line) > self.location.column

    def __next__(self):
        location = copy(self.location)
        m = self._pattern.match(self.line, location.column)
        if not m:
            return None

        kind = m.lastgroup
        value = m.group()
        self.location.column += len(value)

        token_class = getattr(tokens, kind)
        return (token_class(value), location)

    def set_line(self, line, location):
        self.line = line
        self.location = location

    def set_possible_tokens(self, possible_tokens):
        patterns = [
            '(?P<%s>%s)' % (t.__name__, t.pattern)
            for t in possible_tokens
        ]
        self._pattern = re.compile('|'.join(patterns))

    def __iter__(self):
        return UntilNoneIterator(self)


class UnexpectedEndOfInput(RuntimeError):
    pass


class Lexer:

    class Mode:
        DEFAULT = 1
        MULTILINE_STRING = 2
        MACRO_DEFINITION = 3

    POSSIBLE_TOKENS = {
        Mode.DEFAULT: [
            tokens.SharpComment,
            tokens.String,
            tokens.MultilineStringStart,
            tokens.MacroDefinitionStart,
            tokens.Name,
            tokens.PositiveInteger,
            tokens.EndOfLine,
            tokens.WhiteSpace,
            tokens.Other,
        ],
        Mode.MULTILINE_STRING: [
            tokens.MultilineStringEnd,
            tokens.WholeLine,
        ],
        Mode.MACRO_DEFINITION: [
            tokens.MacroDefinitionEnd,
            tokens.SharpComment,
            tokens.MacroContent,
        ],
    }

    def __init__(self, source):
        self.line_stream = LineStream(source)
        self.line_tokenizer = LineTokenizer()
        self.set_mode(self.Mode.DEFAULT)
        self.macros = dict()

    def set_mode(self, mode):
        self.mode = mode
        self.line_tokenizer.set_possible_tokens(self.POSSIBLE_TOKENS[mode])

    def __next__(self):
        if not self.line_tokenizer:
            line_info = next(self.line_stream)
            if line_info is None:
                if self.mode != self.Mode.DEFAULT:
                    raise UnexpectedEndOfInput(self.line_tokenizer.location)
                return None
            self.line_tokenizer.set_line(*line_info)

        (token, location) = next(self.line_tokenizer)

        if self.mode == self.Mode.DEFAULT:
            if isinstance(token, tokens.MultilineStringStart):
                self.set_mode(self.Mode.MULTILINE_STRING)

                raw_lines = []
                (token, _) = next(self)
                while not isinstance(token, tokens.MultilineStringEnd):
                    raw_lines.append(token.value)
                    (token, _) = next(self)

                self.set_mode(self.Mode.DEFAULT)
                token = tokens.MultilineString(raw_lines)

            elif isinstance(token, tokens.MacroDefinitionStart):
                self.set_mode(self.Mode.MACRO_DEFINITION)

                macro_name = token.value

                raw_lines = []
                (token, _) = next(self)
                while not isinstance(token, tokens.MacroDefinitionEnd):
                    if token.value:
                        raw_lines.append(token.value)
                    (token, _) = next(self)

                self.macros[macro_name] = ''.join(raw_lines)

                self.set_mode(self.Mode.DEFAULT)
                return next(self)

        return (token, location)

    def __iter__(self):
        return UntilNoneIterator(self)


if __name__ == '__main__':
    lexer = Lexer(Path(sys.argv[-1]))

    for token, location in lexer:
        print(token, ',', location)
