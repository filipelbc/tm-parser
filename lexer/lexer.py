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


class UndefinedMacro(ValueError):
    pass


class UndefinedMacroArgument(ValueError):
    pass


class Mode:
    DEFAULT = 1
    MULTILINE_STRING = 2
    MACRO_DEFINITION = 3
    MACRO_DETECTION = 4
    MACRO_EXPANSION = 5


MODE_TOKENS = {
    Mode.DEFAULT: [
        # tokens.SharpComment,
        # tokens.String,
        # tokens.MultilineStringStart,
        tokens.MacroDefinitionStart,
        # tokens.Name,
        # tokens.PositiveInteger,
        # tokens.EndOfLine,
        # tokens.WhiteSpace,
        # tokens.Other,
        tokens.WholeLine,
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
    Mode.MACRO_DETECTION: [
        tokens.MacroArgument,
        tokens.MacroCallStart,
        tokens.EndOfLine,
        tokens.NonMacroCall,
    ],
    Mode.MACRO_EXPANSION: [
        tokens.String,
        tokens.MultilineStringStart,
        tokens.WhiteSpace,
        tokens.EndOfLine,
        tokens.SharpComment,
        tokens.MacroCallEnd,
    ]
}


class MacroCall:

    def __init__(self, name, is_optional):
        self.name = name
        self.args = []
        self.is_optional = is_optional


    def __str__(self):
        return 'MacroCall(%r, %s, %s)' % (self.name, self.args, self.is_optional)


class Context:

    def __init__(self, source, current_call=None):
        self.line_stream = LineStream(source)
        self.available_macros = dict()
        self.acc = ''
        self.c_call = current_call
        self.n_call = None
        self.tokenizer = Tokenizer()

class Lexer:

    def __init__(self, source):
        self.x = Context(source)
        self.set_mode(Mode.MACRO_DETECTION)
        self.stack = []

    def set_mode(self, mode):
        self.mode = mode
        self.x.tokenizer.set_possible_tokens(MODE_TOKENS[mode])

    def add_macro(self, name, value):
        if self.x.line_stream.path:
            self.x.available_macros[name] = value
        else:
            self.stack[-1].available_macros[name] = value


    def __next__(self):
        if not self.x.tokenizer:
            line_info = next(self.x.line_stream)

            if line_info is None:
                if self.mode not in [Mode.MACRO_DETECTION, Mode.DEFAULT, Mode.MACRO_DEFINITION]:
                    raise UnexpectedEndOfInput()

                if self.stack:
                    self.x = self.stack.pop()
                    if self.mode == Mode.DEFAULT:
                        self.set_mode(Mode.MACRO_DETECTION)
                    if self.mode == Mode.MACRO_DEFINITION:
                        self.set_mode(Mode.MACRO_DEFINITION)
                    return next(self)
                return None

            (line, self._location) = line_info
            self.x.tokenizer.set_string(line)

        print('    ' * (len(self.stack) + 1), self.mode, self.x.tokenizer, end=' ')

        (token, column) = next(self.x.tokenizer)
        self._location = self._location.move_to(column)

        print(token, self.x.c_call)

        if self.mode == Mode.MACRO_DETECTION:

            if isinstance(token, tokens.MacroArgument):
                self.x.acc += self.x.c_call.args[token.value]

                x = Context(self.x.acc, self.x.c_call)
                self.stack.append(self.x)
                self.x.acc = ''
                self.x = x
                self.set_mode(Mode.MACRO_DETECTION)

            elif isinstance(token, tokens.MacroCallStart):
                self.x.n_call = MacroCall(*token.value)
                self.set_mode(Mode.MACRO_EXPANSION)

            else:
                self.x.acc += token.value or '\n'

                if not self.x.tokenizer:
                    x = Context(self.x.acc, self.x.n_call)
                    self.stack.append(self.x)
                    self.x.acc = ''
                    self.x = x
                    self.set_mode(Mode.DEFAULT)

            return next(self)

        elif self.mode == Mode.MACRO_EXPANSION:

            if isinstance(token, tokens.MultilineStringStart):
                token = self._handle_multiline_string(self.mode)

            if isinstance(token, (tokens.String, tokens.MultilineString)):
                self.x.n_call.args.append(token.value)

            elif isinstance(token, tokens.MacroCallEnd):
                self.x.acc += self.resolve_macro(self.x.n_call)

                x = Context(self.x.acc, self.x.n_call)
                self.stack.append(self.x)
                self.x.acc = ''
                self.x = x
                self.set_mode(Mode.MACRO_DETECTION)

            return next(self)

        elif self.mode == Mode.DEFAULT:

            # if isinstance(token, tokens.MultilineStringStart):
            #     token = self._handle_multiline_string(self.mode)

            if isinstance(token, tokens.MacroDefinitionStart):
                self.set_mode(Mode.MACRO_DEFINITION)

                name = token.value

                raw_lines = []
                (token, _) = next(self)
                while not isinstance(token, tokens.MacroDefinitionEnd):
                    if token.value:
                        raw_lines.append(token.value)
                    (token, _) = next(self)

                self.add_macro(name, ''.join(raw_lines))

                self.set_mode(Mode.MACRO_DETECTION)
                return next(self)

        return (token, self._location)

    def _handle_multiline_string(self, previous_mode):
        self.set_mode(Mode.MULTILINE_STRING)

        raw_lines = []
        (token, _) = next(self)
        while not isinstance(token, tokens.MultilineStringEnd):
            raw_lines.append(token.value)
            (token, _) = next(self)

        self.set_mode(previous_mode)
        return tokens.MultilineString(raw_lines)

    def resolve_macro(self, mc):
        for x in reversed(self.stack + [self.x]):
            print(x.available_macros)
            if mc.name in x.available_macros:
                return x.available_macros[mc.name]

        if not mc.is_optional:
            raise UndefinedMacro(mc.name)

        return ''

    def __iter__(self):
        return UntilNoneIterator(self)


if __name__ == '__main__':
    lexer = Lexer(Path(sys.argv[-1]))

    t = ''

    for token, location in lexer:
        print(token)
        t += token.value

    print(t)

