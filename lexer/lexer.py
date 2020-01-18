from pathlib import Path

import tokens
from tokenizer import Tokenizer
from line_stream import LineStream


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
    PREPROCESSOR = 4
    MACRO_EXPANSION = 5


MODE_TOKENS = {
    Mode.DEFAULT: [
        tokens.SharpComment,
        tokens.String,
        tokens.MultilineStringStart,
        tokens.Name,
        tokens.PositiveInteger,
        tokens.EndOfLine,
        tokens.WhiteSpace,
        tokens.Other,
    ],
    Mode.MULTILINE_STRING: [
        tokens.MultilineStringEnd,
        tokens.MultilineStringContent,
    ],
    Mode.MACRO_DEFINITION: [
        tokens.MacroDefinitionStart,
        tokens.MacroDefinitionEnd,
        tokens.SharpComment,
        tokens.MacroContent,
    ],
    Mode.PREPROCESSOR: [
        tokens.MacroDefinitionStart,
        tokens.MacroArgument,
        tokens.Include,
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

    def __repr__(self):
        """
        >>> MacroCall('foo', True)
        MacroCall('foo', [], True)
        """
        return 'MacroCall(%r, %s, %s)' % (self.name,
                                          self.args,
                                          self.is_optional)


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
        self.set_mode(Mode.PREPROCESSOR)
        self.stack = []
        self.in_multiline_string = 0

    def set_mode(self, mode):
        self.mode = mode
        self.x.tokenizer.set_possible_tokens(MODE_TOKENS[mode])

    def add_macro(self, name, value):
        if self.x.line_stream.path or len(self.stack) == 0:
            self.x.available_macros[name] = value
        else:
            self.stack[-1].available_macros[name] = value

    def __next__(self):
        if not self.x.tokenizer:
            line_info = next(self.x.line_stream)

            if line_info is None:
                if self.mode == Mode.MACRO_EXPANSION:
                    raise UnexpectedEndOfInput()

                if self.stack:
                    if self.x.line_stream.path:
                        if self.in_multiline_string:
                            self.in_multiline_string -= 1
                    self.x = self.stack.pop()
                    if self.mode == Mode.MACRO_DEFINITION:
                        self.set_mode(Mode.MACRO_DEFINITION)
                    else:
                        self.set_mode(Mode.PREPROCESSOR)
                    return next(self)

                if self.mode == Mode.MULTILINE_STRING:
                    raise UnexpectedEndOfInput()

                return None

            (line, self._location) = line_info
            self.x.tokenizer.set_string(line)

        print('    ' * (len(self.stack) + 1), self.mode, self.in_multiline_string, end=' ')

        (token, column) = next(self.x.tokenizer)
        self._location = self._location.move_to(column)

        print(token, self.x.c_call)

        if self.mode == Mode.PREPROCESSOR:

            if isinstance(token, tokens.MacroDefinitionStart):
                self.set_mode(Mode.MACRO_DEFINITION)

                name = token.value

                raw_lines = []
                c = 0
                (token, _) = next(self)
                while not (isinstance(token, tokens.MacroDefinitionEnd) and c == 0):
                    if isinstance(token, tokens.MacroDefinitionStart):
                        c += 1
                        raw_lines.append(token.matched_string)
                    elif isinstance(token, tokens.MacroDefinitionEnd):
                        c -= 1
                        raw_lines.append(token.matched_string)
                    elif token.value:
                        raw_lines.append(token.value)
                    (token, _) = next(self)

                self.add_macro(name, ''.join(raw_lines))

                self.set_mode(Mode.PREPROCESSOR)

            elif isinstance(token, tokens.MacroArgument):
                self.x.acc += self.x.c_call.args[token.value]
                self.x.acc += self.x.tokenizer.remaining_string()

                x = Context(self.x.acc, self.x.c_call)
                self.stack.append(self.x)
                self.x.acc = ''
                self.x.tokenizer.set_string('')
                self.x = x
                self.set_mode(Mode.PREPROCESSOR)

            elif isinstance(token, tokens.MacroCallStart):
                self.x.n_call = MacroCall(*token.value)
                self.set_mode(Mode.MACRO_EXPANSION)

            elif isinstance(token, tokens.Include):
                x = Context(self.resolve_path(token.value))
                self.stack.append(self.x)
                self.x = x
                self.set_mode(Mode.PREPROCESSOR)
                if self.in_multiline_string:
                    self.in_multiline_string += 1

            else:
                self.x.acc += token.value or '\n'

                if not self.x.tokenizer:
                    x = Context(self.x.acc, self.x.n_call)
                    self.stack.append(self.x)
                    self.x.acc = ''
                    self.x = x
                    if self.in_multiline_string:
                        self.set_mode(Mode.MULTILINE_STRING)
                    else:
                        self.set_mode(Mode.DEFAULT)

            return next(self)

        elif self.mode == Mode.MACRO_EXPANSION:

            if isinstance(token, tokens.MultilineStringStart):
                token = self.handle_multiline_string(self.mode)

            if isinstance(token, (tokens.String, tokens.MultilineString)):
                self.x.n_call.args.append(token.value)

            elif isinstance(token, tokens.MacroCallEnd):
                self.x.acc += self.resolve_macro(self.x.n_call)
                self.x.acc += self.x.tokenizer.remaining_string()

                x = Context(self.x.acc, self.x.n_call)
                self.stack.append(self.x)
                self.x.acc = ''
                self.x.tokenizer.set_string('')
                self.x = x
                self.set_mode(Mode.PREPROCESSOR)

            return next(self)

        elif self.mode == Mode.DEFAULT:

            if isinstance(token, tokens.MultilineStringStart):
                token = self.handle_multiline_string(self.mode)

        return (token, self._location)

    def handle_multiline_string(self, previous_mode):
        self.set_mode(Mode.MULTILINE_STRING)
        self.in_multiline_string = 1

        raw_lines = []
        (token, _) = next(self)
        while not (isinstance(token, tokens.MultilineStringEnd) and self.in_multiline_string == 1):
            raw_lines.append(token.matched_string)
            (token, _) = next(self)

        self.set_mode(previous_mode)
        self.in_multiline_string = 0
        return tokens.MultilineString(raw_lines)

    def resolve_macro(self, mc):
        for x in reversed(self.stack + [self.x]):
            if mc.name in x.available_macros:
                return x.available_macros[mc.name]

        if not mc.is_optional:
            raise UndefinedMacro(mc.name)

        return ''

    def resolve_path(self, string):
        parent = None
        for x in reversed(self.stack + [self.x]):
            if isinstance(x.line_stream.path, Path):
                parent = x.line_stream.path.parent
                break

        if parent:
            return parent / Path(string)
        return Path(string)
