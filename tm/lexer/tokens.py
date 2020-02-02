import json
import re
from abc import ABC
from datetime import datetime, timedelta
from textwrap import dedent


class Token(ABC):
    """
    @value Instance attribute. The value that was matched, after being
           processed.

    @pattern Class attribute. The regular expression that matches the token
             type. Use it to check if the next token on a string is of this
             type.

             Concrete tokens must set this to a regular expression pattern
             string.
    """
    pattern = None

    def __init__(self, matched_string):
        self.matched_string = matched_string
        self.value = self.process(matched_string)

    @staticmethod
    def process(value):
        """
        Override this method to perform any necessary post-processing on the
        matched string.
        """
        return value

    def __repr__(self):
        """
        >>> Token('foo')
        Token('foo')
        """
        return '%s(%r)' % (self.kind, self.value)

    @property
    def kind(self):
        return self.__class__.__name__


def _anything_up_to(pattern):
    """
    Creates a pattern that matches anything up to @pattern or newline.

    >>> import re; pattern = _anything_up_to('foo')
    >>> re.match(pattern, "\\n")
    <_sre.SRE_Match object; span=(0, 1), match='\\n'>

    >>> re.match(pattern, "ab\\n")
    <_sre.SRE_Match object; span=(0, 3), match='ab\\n'>

    >>> re.match(pattern, "abfoo")
    <_sre.SRE_Match object; span=(0, 2), match='ab'>

    >>> re.match(pattern, "abfoo\\n")
    <_sre.SRE_Match object; span=(0, 2), match='ab'>

    >>> re.match(pattern, "abfoo foo")
    <_sre.SRE_Match object; span=(0, 2), match='ab'>

    >>> re.match(pattern, "abfoo foo\\n")
    <_sre.SRE_Match object; span=(0, 2), match='ab'>

    Note that the pattern will also match if @pattern is at the begining of the
    string.

    >>> re.match(pattern, "foo")
    <_sre.SRE_Match object; span=(0, 3), match='foo'>

    >>> re.match(pattern, "foo\\n")
    <_sre.SRE_Match object; span=(0, 4), match='foo\\n'>

    >>> re.match(pattern, "foo foo")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>

    >>> re.match(pattern, "foo foo\\n")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>

    >>> re.match(pattern, "foobar")
    <_sre.SRE_Match object; span=(0, 6), match='foobar'>

    >>> re.match(pattern, "foobar\\n")
    <_sre.SRE_Match object; span=(0, 7), match='foobar\\n'>

    >>> re.match(pattern, "foo foobar")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>

    >>> re.match(pattern, "foo foobar\\n")
    <_sre.SRE_Match object; span=(0, 4), match='foo '>
    """
    return r'\n|.+?(?=(' + pattern + r'|$))\n?'


class Comment(Token, ABC):
    """
    Helper class for "comment" tokens.
    """

    @property
    def kind(self):
        return Comment.__name__

    @staticmethod
    def process(_):
        return None


class String(Token, ABC):
    """
    Helper class for "string" tokens.
    """

    @property
    def kind(self):
        return String.__name__


class SharpComment(Comment):
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

    >>> This('# comment text')
    Comment(None)
    """
    delimiter = r'#'
    pattern = delimiter + r'.*'


class DoubleQuotedString(String):
    """
    Matches a standard, double quoted, string. Examples:

    "foo bar"
    "string containing scaped double quote: \\" here"

    >>> import re; This = DoubleQuotedString
    >>> re.match(This.pattern, r'"foo \\"bar\\" buu" "wololo"')
    <_sre.SRE_Match object; span=(0, 17), match='"foo \\\\"bar\\\\" buu"'>

    >>> re.match(This.pattern, r'""')
    <_sre.SRE_Match object; span=(0, 2), match='""'>

    >>> This('""')
    String('')

    >>> This('"foo"')
    String('foo')

    >>> This(r'"foo\\"bar\\"foo"')
    String('foo"bar"foo')
    """
    pattern = r'"(\\"|[^"])*"'

    @staticmethod
    def process(value):
        """
        Handle escaped characters, especially the double quote.
        """
        return json.loads(value)


class MultilineString(String):
    """
    Token type for multiline strings. Does not have a pattern attached to it.
    Its kind is the same as the String token.

    >>> MultilineString("foo bar")
    String('foo bar')

    >>> MultilineString("foo bar\\n  buu\\n")
    String('foo bar\\n  buu\\n')

    >>> MultilineString("   foo bar\\n  buu\\n")
    String(' foo bar\\nbuu\\n')

    >>> MultilineString("\\n foo bar\\n   buu\\n")
    String('foo bar\\n  buu\\n')
    """

    @staticmethod
    def process(text):
        return dedent(text.lstrip('\n'))


class MultilineStringStart(Token):
    """
    Matches the start delimiter of a multiline string. It can follow another
    token in the same line, but may only be followed by whitespace.

    >>> import re; This = MultilineStringStart
    >>> re.match(This.pattern, "-8<-")
    <_sre.SRE_Match object; span=(0, 4), match='-8<-'>

    >>> re.match(This.pattern, "-8<-foo")
    <_sre.SRE_Match object; span=(0, 4), match='-8<-'>
    """
    pattern = r'-8<-'

    @staticmethod
    def process(value):
        return None


class MultilineStringEnd(Token):
    """
    Matches the end delimiter of a multiline string. It must be alone in the
    line.

    >>> import re; This = MultilineStringEnd
    >>> re.match(This.pattern, "->8-")
    <_sre.SRE_Match object; span=(0, 4), match='->8-'>

    >>> re.match(This.pattern, "->8-foo")
    <_sre.SRE_Match object; span=(0, 4), match='->8-'>

    >>> re.match(MultilineStringStart.pattern, " ->8-")

    >>> re.match(MultilineStringStart.pattern, "f->8-")
    """
    pattern = r'->8-'

    @staticmethod
    def process(value):
        return None


class MultilineStringContent(Token):
    """
    Matches anything up to a MultilineStringEnd.
    """
    pattern = _anything_up_to(MultilineStringEnd.pattern)


class WholeLine(Token):
    """
    Matches everything next. Only used for testing macro expansions.

    >>> import re; This = WholeLine
    >>> re.match(This.pattern, "foo bar \\n")
    <_sre.SRE_Match object; span=(0, 9), match='foo bar \\n'>

    >>> re.match(This.pattern, "\\n")
    <_sre.SRE_Match object; span=(0, 1), match='\\n'>
    """
    pattern = r'(.|\n)+$'


class Name(Token):
    """
    Matches a Python-style identifier. For instance:

        foo_bar
        _FOO_123
    """
    pattern = r'[a-zA-Z_]\w*'


class PositiveInteger(Token):
    """
    Matches a positive integer.

    >>> PositiveInteger('123')
    PositiveInteger(123)
    """
    pattern = r'[1-9]\d*'

    @staticmethod
    def process(value):
        """
        Converts the value from string to integer.
        """
        return int(value)


def _cast_values(d, t=int):
    return {k: t(v) if v else 0 for k, v in d.items()}


class Datetime(Token):
    """
    Matches a date with optional time.

    >>> Datetime('2018-03-24-15:40')
    Datetime(datetime.datetime(2018, 3, 24, 15, 40))
    >>> Datetime('2018-03-24')
    Datetime(datetime.datetime(2018, 3, 24, 0, 0))
    """
    pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(-(?P<hour>\d{2}):(?P<minute>\d{2}))?'

    @classmethod
    def process(cls, value):
        m = re.match(cls.pattern, value)
        return datetime(**_cast_values(m.groupdict()))


class Timedelta(Token):
    """
    Matches a time duration value.

    >>> Timedelta('1w2d13h25min')
    Timedelta(datetime.timedelta(9, 48300))
    >>> Timedelta('1w25min')
    Timedelta(datetime.timedelta(7, 1500))
    >>> Timedelta('2d13h25min')
    Timedelta(datetime.timedelta(2, 48300))
    >>> Timedelta('2d13h')
    Timedelta(datetime.timedelta(2, 46800))
    >>> Timedelta('2d')
    Timedelta(datetime.timedelta(2))
    >>> Timedelta('13h25min')
    Timedelta(datetime.timedelta(0, 48300))
    >>> Timedelta('25min')
    Timedelta(datetime.timedelta(0, 1500))
    >>> Timedelta('13h')
    Timedelta(datetime.timedelta(0, 46800))
    """
    pattern = r'(?=\d+(w|d|h|min))((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)min)?'

    @classmethod
    def process(cls, value):
        m = re.match(cls.pattern, value)
        return timedelta(**_cast_values(m.groupdict()))


class EndOfLine(Token):
    """
    Matches the end of a line.
    """
    pattern = r'\n'


class WhiteSpace(Token):
    """
    Matches any positive amount of whitespace, but not the newline.

    >>> import re; This = WhiteSpace
    >>> re.match(This.pattern, "   ")
    <_sre.SRE_Match object; span=(0, 3), match='   '>

    >>> re.match(This.pattern, "   \\n")
    <_sre.SRE_Match object; span=(0, 3), match='   '>

    >>> re.match(This.pattern, "   a")
    <_sre.SRE_Match object; span=(0, 3), match='   '>
    """
    pattern = r'\s+?(?=($|[^\s]|[\n]))'


class Character(Token):
    """
    Matches any single character.
    """
    pattern = r'.'


class MacroDefinitionStart(Token):
    """
    Matches the start of a macro defition. It must happen at the begining of a
    line (i.e. match only happens at position 0), although whitespace is not
    considered.

    >>> import re; This = MacroDefinitionStart
    >>> p = re.compile(This.pattern)
    >>> p.match(" macro foo [", 0)
    <_sre.SRE_Match object; span=(0, 12), match=' macro foo ['>

    >>> p.match(" macro foo [", 1)

    >>> This("macro foo [")
    MacroDefinitionStart('foo')
    """
    pattern = r'^\s*macro\s+([a-zA-Z_]\w*)\s+\['

    @classmethod
    def process(cls, value):
        return re.match(cls.pattern, value).group(1)


class MacroDefinitionEnd(Token):
    """
    >>> import re; This = MacroDefinitionEnd
    >>> re.match(This.pattern, "] \\n")
    <_sre.SRE_Match object; span=(0, 3), match='] \\n'>

    >>> re.match(This.pattern, "] a\\n")
    """
    pattern = r']\s+$'

    @classmethod
    def process(cls, value):
        return None


class MacroContent(Token):
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


class MacroArgument(Token):
    """
    Matches a macro argument.

    >>> import re; This = MacroArgument
    >>> re.match(This.pattern, "${1}")
    <_sre.SRE_Match object; span=(0, 4), match='${1}'>

    >>> This("${1}")
    MacroArgument(0)
    """
    pattern = r'\$\{[1-9]\d*}'

    @staticmethod
    def process(value):
        return int(value[2:-1]) - 1


class MacroCallStart(Token):
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

    >>> re.match(This.pattern, "${?foo")
    <_sre.SRE_Match object; span=(0, 6), match='${?foo'>

    >>> re.match(This.pattern, "${foo.")

    >>> re.match(This.pattern, "$${foo ")

    >>> This("${foo ")
    MacroCallStart(('foo', False))

    >>> This("${?foo ")
    MacroCallStart(('foo', True))
    """
    pattern = r'\${(\??[a-zA-Z_]\w*)(?=(\s|}|$))'

    @staticmethod
    def process(value):
        """
        The processed value of this token is a tuple of
        - macro name
        - optional call flag
        """
        name = value[2:].strip()
        if name[0] == '?':
            return (name[1:], True)
        return (name, False)


class NonMacroCall(Token):
    """
    Matches anything up to a MacroArgument or MacroCallStart.
    """
    pattern = _anything_up_to(r'|'.join([
        MacroCallStart.pattern,
        MacroArgument.pattern,
        SharpComment.delimiter,
    ]))


class MacroCallEnd(Token):
    """
    Matches the end of a macro call.
    """
    pattern = r'}'

    @staticmethod
    def process(value):
        return None


class Include(Token):
    """
    Matches a "include" directive.

        include "./foo/bar"

    >>> import re; This = Include; string = '  include  "./foo"  \\n'
    >>> re.match(This.pattern, string)
    <_sre.SRE_Match object; span=(0, 21), match='  include  "./foo"  \\n'>

    >>> This(string)
    Include('./foo')
    """
    pattern = r'^\s*include\s+' + DoubleQuotedString.pattern + r'\s*$'

    @staticmethod
    def process(value):
        return DoubleQuotedString.process(value.strip()[7:])
