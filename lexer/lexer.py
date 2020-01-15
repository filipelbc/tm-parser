import sys

from pathlib import Path
from io import StringIO

import tokens
from tokenizer import Tokenizer
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

    def move_to(self, column):
        """
        Creates a copy of the location, but uses the new column.
        """
        return Location(self.path, self.line_num, column)


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
        self.tokenizer = Tokenizer()
        self.set_mode(self.Mode.DEFAULT)
        self.macros = dict()

    def set_mode(self, mode):
        self.mode = mode
        self.tokenizer.set_possible_tokens(self.POSSIBLE_TOKENS[mode])

    def __next__(self):
        if not self.tokenizer:
            line_info = next(self.line_stream)
            if line_info is None:
                if self.mode != self.Mode.DEFAULT:
                    raise UnexpectedEndOfInput()
                return None
            (line, self._location) = line_info
            self.tokenizer.set_string(line)

        (token, column) = next(self.tokenizer)
        self._location = self._location.move_to(column)

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

        return (token, self._location)

    def __iter__(self):
        return UntilNoneIterator(self)


if __name__ == '__main__':
    lexer = Lexer(Path(sys.argv[-1]))

    for token, location in lexer:
        print(token, ',', location)
