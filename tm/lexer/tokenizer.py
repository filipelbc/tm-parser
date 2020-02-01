import re


class Tokenizer:
    """
    Provider an interface for tokenizing a string, producing a stream of tokens.
    Tokens are returned with their corresponding position.

    At each iteration, the list of possible tokens can be changed.

    >>> from .tokens import Name, DoubleQuotedString, EndOfLine, WhiteSpace
    >>> t = Tokenizer()
    >>> t.set_string('bar "wololo"\\n')
    >>> t.set_possible_tokens([Name, DoubleQuotedString, EndOfLine, WhiteSpace])
    >>> while t: next(t)
    (Name('bar'), 0)
    (WhiteSpace(' '), 3)
    (String('wololo'), 4)
    (EndOfLine('\\n'), 12)
    """

    def __init__(self):
        self.set_string('')
        self.set_possible_tokens([])

    def __bool__(self):
        return len(self.string) > self.position

    def __next__(self):
        m = self._pattern.match(self.string, self.position)
        if not m:
            return None

        token_name = m.lastgroup
        value = m.group()
        position = self.position
        self.position += len(value)

        token_class = self.possible_tokens[token_name]
        return (token_class(value), position)

    def set_string(self, string):
        self.string = string
        self.position = 0

    def set_possible_tokens(self, possible_tokens):
        self.possible_tokens = {t.__name__: t for t in possible_tokens}
        patterns = [
            '(?P<%s>%s)' % (t.__name__, t.pattern)
            for t in possible_tokens
        ]
        self._pattern = re.compile('|'.join(patterns))

    def remaining_string(self):
        return self.string[self.position:]

    def __repr__(self):
        """
        >>> t = Tokenizer()
        >>> t.set_string("foo bar")
        >>> t
        Tokenizer('foo bar', 0)
        """
        return 'Tokenizer(%r, %r)' % (self.string, self.position)
