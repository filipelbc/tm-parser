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

    def __init__(self, source, macro_call=None):
        self.line_stream = LineStream(source)
        self.macros = dict()
        self.acc = ''
        self.c_call = macro_call
        self.n_call = None
        self.tokenizer = Tokenizer()

    @property
    def is_file(self):
        return bool(self.line_stream.path)


class Lexer:

    def __init__(self, source):
        self.stack = []
        self.push(source)
        self.set_mode(Mode.PREPROCESSOR)
        self.in_multiline_string = 0

    @property
    def x(self):
        """
        Returns the current Context.
        """
        return self.stack[-1] if self.stack else None

    def push(self, source, macro_call=None):
        """
        Adds a new Context to the stack. Resets the accumulator and tokenizer
        of the current one.
        """
        if self.x:
            self.x.acc = ''
            self.x.tokenizer.set_string('')
        self.stack.append(Context(source, macro_call))

    def pop(self):
        """
        Removes the current Context from the stack and returns it.
        """
        return self.stack.pop()

    def set_mode(self, mode):
        self.mode = mode
        self.x.tokenizer.set_possible_tokens(MODE_TOKENS[mode])

    def add_macro(self, name, value):
        """
        Adds a new macro to the appropriate Context. Only the first or a file
        context can hold macros.
        """
        for x in reversed(self.stack):
            if x.is_file:
                x.macros[name] = value
                return
        self.x.macros[name] = value

    def resolve_macro(self, mc):
        for x in reversed(self.stack):
            if mc.name in x.macros:
                return x.macros[mc.name]

        if not mc.is_optional:
            raise UndefinedMacro(mc.name)

        return ''

    def resolve_path(self, string):
        parent = None
        for x in reversed(self.stack):
            if x.is_file:
                parent = x.line_stream.path.parent
                break

        if parent:
            return parent / Path(string)
        return Path(string)

    def __next__(self):
        if not self.x.tokenizer:
            line_info = next(self.x.line_stream)

            if line_info is None:
                if self.mode == Mode.MACRO_EXPANSION:
                    raise UnexpectedEndOfInput()

                if len(self.stack) > 1:
                    if self.x.is_file:
                        if self.in_multiline_string:
                            self.in_multiline_string -= 1
                    self.stack.pop()
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

        (token, column) = next(self.x.tokenizer)
        self._location = self._location.move_to(column)

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

                self.push(self.x.acc, self.x.c_call)
                self.set_mode(Mode.PREPROCESSOR)

            elif isinstance(token, tokens.MacroCallStart):
                self.x.n_call = MacroCall(*token.value)
                self.set_mode(Mode.MACRO_EXPANSION)

            elif isinstance(token, tokens.Include):
                self.push(self.resolve_path(token.value))
                self.set_mode(Mode.PREPROCESSOR)
                if self.in_multiline_string:
                    self.in_multiline_string += 1

            else:
                self.x.acc += token.value or '\n'

                if not self.x.tokenizer:
                    self.push(self.x.acc, self.x.n_call)
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

                self.push(self.x.acc, self.x.n_call)
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
