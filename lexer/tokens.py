import json
import re
from textwrap import dedent


class BaseToken:
    """
    @value Instance attribute. The value that was matched, after being
           post-processed.
    """

    def __init__(self, value):
        self.value = self.process(value)

    @staticmethod
    def process(value):
        """
        Override this method to perform any necessary post-processing on the
        value of the token.
        """
        return value

    def __str__(self):
        return '%s(%r)' % (self.kind, self.value)

    @property
    def kind(self):
        return self.__class__.__name__


class BaseTokenWithPattern(BaseToken):
    """
    @pattern Class attribute. The regular expression that matches the token
             type. Use it to check if the next token on a string is of this
             type.

             Concrete tokens must set this to a regular expression pattern
             string.
    """
    pattern = None


class SharpComment(BaseTokenWithPattern):
    """
    Matches a Python-style comment. Newline character is not included in the
    match. For instance:

    # This is a comment.

    >>> import re; This = SharpComment
    >>> re.match(This.pattern, '# foo\\n')
    <_sre.SRE_Match object; span=(0, 5), match='# foo'>

    >>> re.match(This.pattern, '#')
    <_sre.SRE_Match object; span=(0, 1), match='#'>

    >>> re.match(This.pattern, '#\\n')
    <_sre.SRE_Match object; span=(0, 1), match='#'>

    >>> re.match(This.pattern, '#foo')
    <_sre.SRE_Match object; span=(0, 4), match='#foo'>

    >>> print(This('# comment text'))
    Comment(None)
    """
    pattern = r'#.*'

    @property
    def kind(self):
        return 'Comment'

    @staticmethod
    def process(value):
        return None


class String(BaseTokenWithPattern):
    """
    Matches a standard, double quoted, string. Examples:

    "foo bar"
    "string containing scaped double quote: \\" here"

    >>> import re; This = String
    >>> re.match(This.pattern, r'"foo \\"bar\\" buu" "wololo"')
    <_sre.SRE_Match object; span=(0, 17), match='"foo \\\\"bar\\\\" buu"'>

    >>> print(This('"foo"'))
    String('foo')

    >>> print(This(r'"fo\\no"'))
    String('fo\\no')
    """
    pattern = r'"(\\"|[^"])+"'

    @staticmethod
    def process(value):
        """
        Handle escaped characters, specially the double quote.
        """
        return json.loads(value)


class MultilineString(BaseToken):
    """
    Token type for multiline strings. Does not have a pattern attached to it.
    Its kind is the same as the String token.

    >>> print(MultilineString("foo bar"))
    String('foo bar')

    >>> print(MultilineString(["foo bar\\n", "  buu\\n"]))
    String('foo bar\\n  buu')

    >>> print(MultilineString(["   foo bar\\n", "  buu\\n"]))
    String('foo bar\\nbuu')
    """

    @staticmethod
    def process(raw_lines):
        return dedent(''.join(raw_lines)).strip()

    @property
    def kind(self):
        return String.__name__


class MultilineStringStart(BaseTokenWithPattern):
    """
    Matches the start delimiter of a multiline string. It can follow another
    token in the same line, but may only be followed by whitespace.

    >>> import re; This = MultilineStringStart
    >>> re.match(This.pattern, "-8<-  \\n")
    <_sre.SRE_Match object; span=(0, 7), match='-8<-  \\n'>
    """
    pattern = r'-8<-\s*$'

    @staticmethod
    def process(value):
        return None


class MultilineStringEnd(BaseTokenWithPattern):
    """
    Matches the end delimiter of a multiline string. It must be alone in the
    line.

    >>> import re; This = MultilineStringEnd
    >>> re.match(This.pattern, "  ->8-  \\n")
    <_sre.SRE_Match object; span=(0, 9), match='  ->8-  \\n'>

    >>> re.match(MultilineStringStart.pattern, "foo ->8-")

    >>> re.match(MultilineStringStart.pattern, "->8- foo")
    """
    pattern = r'\s*->8-\s*$'

    @staticmethod
    def process(value):
        return None


class WholeLine(BaseTokenWithPattern):
    """
    Matches everything next. Useful for handling the contents of a multiline
    string.

    >>> import re; This = WholeLine
    >>> re.match(This.pattern, "foo bar \\n")
    <_sre.SRE_Match object; span=(0, 9), match='foo bar \\n'>

    >>> re.match(This.pattern, "\\n")
    <_sre.SRE_Match object; span=(0, 1), match='\\n'>
    """
    pattern = r'(.|\n)+$'


class Name(BaseTokenWithPattern):
    """
    Matches a standard C identifier. For instance:

        foo_bar
        _FOO_123
    """
    pattern = r'[a-zA-Z_]\w*'


class PositiveInteger(BaseTokenWithPattern):
    """
    Matches a positive integer.

    >>> print(PositiveInteger('123'))
    PositiveInteger(123)
    """
    pattern = r'[1-9]\d*'

    @staticmethod
    def process(value):
        """
        Converts the value from string to integer.
        """
        return int(value)


class EndOfLine(BaseTokenWithPattern):
    """
    Matches the end of a line.
    """
    pattern = r'\n'


class WhiteSpace(BaseTokenWithPattern):
    """
    Matches any positive amount of whitespace.
    """
    pattern = r'\s+'


class Other(BaseTokenWithPattern):
    """
    Matches any single character.
    """
    pattern = r'.'


class MacroDefinitionStart(BaseTokenWithPattern):
    """
    Matches the start of a macro defition. It must happen at the begining of a
    line (i.e. match only happens at position 0), although whitespace is not
    considered.

    >>> import re; This = MacroDefinitionStart
    >>> p = re.compile(This.pattern)
    >>> p.match(" macro foo [", 0)
    <_sre.SRE_Match object; span=(0, 12), match=' macro foo ['>

    >>> p.match(" macro foo [", 1)

    >>> print(This("macro foo ["))
    MacroDefinitionStart('foo')
    """
    pattern = r'^\s*macro\s+([a-zA-Z_]\w*)\s+\['

    @classmethod
    def process(cls, value):
        return re.match(cls.pattern, value).group(1)


class MacroDefinitionEnd(BaseTokenWithPattern):
    """
    >>> import re; This = MacroDefinitionEnd
    >>> re.match(This.pattern, "] \\n")
    <_sre.SRE_Match object; span=(0, 3), match='] \\n'>
    """
    pattern = r']\s+'

    @classmethod
    def process(cls, value):
        return None


class MacroContent(BaseTokenWithPattern):
    """
    Matches everything up to the beggining of a SharpComment or
    MacroDefinitionEnd.

    >>> import re; This = MacroContent
    >>> re.match(This.pattern, "foo bar ]")
    <_sre.SRE_Match object; span=(0, 8), match='foo bar '>

    >>> re.match(This.pattern, "foo bar #c")
    <_sre.SRE_Match object; span=(0, 8), match='foo bar '>

    >>> re.match(This.pattern, "foo bar \\n")
    <_sre.SRE_Match object; span=(0, 9), match='foo bar \\n'>
    """
    pattern = r'[^\]#]+'


class MacroCallStart(BaseTokenWithPattern):
    """
    Matches the start of a macro call.

    >>> import re; This = MacroCallStart
    >>> re.match(This.pattern, "${foo ")
    <_sre.SRE_Match object; span=(0, 5), match='${foo'>

    >>> re.match(This.pattern, "${foo}")
    <_sre.SRE_Match object; span=(0, 5), match='${foo'>

    >>> re.match(This.pattern, "${?foo ")
    <_sre.SRE_Match object; span=(0, 6), match='${?foo'>

    >>> re.match(This.pattern, "${?foo}")
    <_sre.SRE_Match object; span=(0, 6), match='${?foo'>

    >>> re.match(This.pattern, "${1}")
    <_sre.SRE_Match object; span=(0, 3), match='${1'>

    >>> re.match(This.pattern, "${1 ")
    <_sre.SRE_Match object; span=(0, 3), match='${1'>

    >>> re.match(This.pattern, "${1.")

    >>> re.match(This.pattern, "${?1 ")

    >>> re.match(This.pattern, "$${1}")

    >>> print(This("${foo "))
    MacroCallStart(('foo ', False))

    >>> print(This("${?foo "))
    MacroCallStart(('foo ', True))

    >>> print(This("${1 "))
    MacroCallStart(('1 ', False))
    """
    pattern = r'\${(\??[a-zA-Z_]\w*|\d+)(?=(\s|}))'

    @staticmethod
    def process(value):
        """
        The processed value of this token is a tuple of
        - macro name
        - optional call flag
        """
        name = value[2:]
        if name[0] == '?':
            return (name[1:], True)
        return (name, False)


class NonMacroCall(BaseTokenWithPattern):
    """
    Matches anything up to a MacroCallStart.

    >>> import re; This = NonMacroCall
    >>> re.match(This.pattern, "foo ${bar ")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>

    >>> re.match(This.pattern, "foo ${bar ${bin")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>

    >>> re.match(This.pattern, "foo bar\\n")
    <_sre.SRE_Match object; span=(0, 7), match='foo bar'>

    >>> re.match(This.pattern, "${bar foo")
    """
    pattern = r'(.|\n)+?(?=(' + MacroCallStart.pattern + r'|\n))'


class MacroCallEnd(BaseTokenWithPattern):
    """
    Matches the end of a macro call.
    """
    pattern = r'}'

    @staticmethod
    def process(value):
        return None
