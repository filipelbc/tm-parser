from unittest import TestCase

from utils import UntilNoneIterator

from lexer import Lexer


CASE_BASIC = """\
foo {
  bar
}
---
(Name('foo'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(Other('{'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 5))
(WhiteSpace('  '), Location(None, 1, 0))
(Name('bar'), Location(None, 1, 2))
(EndOfLine('\\n'), Location(None, 1, 5))
(Other('}'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 1))
"""

CASE_COMMENT = """\
foo {
  # comment
  bar # another comment
}
---
(Name('foo'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(Other('{'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 5))
(WhiteSpace('  '), Location(None, 1, 0))
(Comment(None), Location(None, 1, 2))
(EndOfLine('\\n'), Location(None, 1, 11))
(WhiteSpace('  '), Location(None, 1, 0))
(Name('bar'), Location(None, 1, 2))
(WhiteSpace(' '), Location(None, 1, 5))
(Comment(None), Location(None, 1, 6))
(EndOfLine('\\n'), Location(None, 1, 23))
(Other('}'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 1))
"""

CASE_STRING = """\
foo "bar"
bar "f\\"o\\"o"
---
(Name('foo'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(String('bar'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 9))
(Name('bar'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(String('f"o"o'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 13))
"""

CASE_INTEGER = """\
foo 1
bar 2
---
(Name('foo'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(PositiveInteger(1), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 5))
(Name('bar'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(PositiveInteger(2), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 5))
"""

CASE_MULTILINE_STRING_1 = """\
foo -8<-
  line 1
  line 2
->8-
bar
---
"""

CASE_MACRO_BASIC = """\
macro foo [ bar ]
${foo} bin ${foo}
---
(WhiteSpace(' '), Location(None, 1, 0))
(Name('bar'), Location(None, 1, 1))
(WhiteSpace(' '), Location(None, 1, 4))
(WhiteSpace(' '), Location(None, 1, 0))
(Name('bin'), Location(None, 1, 1))
(WhiteSpace('  '), Location(None, 1, 4))
(Name('bar'), Location(None, 1, 6))
(WhiteSpace(' '), Location(None, 1, 9))
(EndOfLine('\\n'), Location(None, 1, 0))
"""

CASE_MACRO_ARG = """\
macro foo [ bar ${1} ]
m ${foo "no"} g
---
(Name('m'), Location(None, 1, 0))
(WhiteSpace('  '), Location(None, 1, 1))
(Name('bar'), Location(None, 1, 3))
(WhiteSpace(' '), Location(None, 1, 6))
(Name('no'), Location(None, 1, 7))
(WhiteSpace(' '), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 0))
(Name('g'), Location(None, 1, 1))
(EndOfLine('\\n'), Location(None, 1, 2))
"""

CASE_MACRO_MULTILINE_1 = """\
macro foo [line 1
  line ${2} line ${1}
]
bar ${foo
        "2" "1"}
"bar"
---
(Name('bar'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(Name('line'), Location(None, 1, 4))
(WhiteSpace(' '), Location(None, 1, 8))
(PositiveInteger(1), Location(None, 1, 9))
(EndOfLine('\\n'), Location(None, 1, 10))
(WhiteSpace('  '), Location(None, 1, 0))
(Name('line'), Location(None, 1, 2))
(WhiteSpace(' '), Location(None, 1, 6))
(PositiveInteger(1), Location(None, 1, 7))
(WhiteSpace(' '), Location(None, 1, 0))
(Name('line'), Location(None, 1, 1))
(WhiteSpace(' '), Location(None, 1, 5))
(PositiveInteger(2), Location(None, 1, 6))
(EndOfLine('\\n'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 0))
(String('bar'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 5))
"""

CASE_MACRO_MULTILINE_2 = """\
macro foo [ line 1
  line ${2}
  line ${1}
]
bar ${foo
        "2"
    "1"
} "bar"
---
(Name('bar'), Location(None, 1, 0))
(WhiteSpace('  '), Location(None, 1, 3))
(Name('line'), Location(None, 1, 5))
(WhiteSpace(' '), Location(None, 1, 9))
(PositiveInteger(1), Location(None, 1, 10))
(EndOfLine('\\n'), Location(None, 1, 11))
(WhiteSpace('  '), Location(None, 1, 0))
(Name('line'), Location(None, 1, 2))
(WhiteSpace(' '), Location(None, 1, 6))
(PositiveInteger(1), Location(None, 1, 7))
(EndOfLine('\\n'), Location(None, 1, 0))
(WhiteSpace('  '), Location(None, 1, 0))
(Name('line'), Location(None, 1, 2))
(WhiteSpace(' '), Location(None, 1, 6))
(PositiveInteger(2), Location(None, 1, 7))
(EndOfLine('\\n'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 0))
(String('bar'), Location(None, 1, 1))
(EndOfLine('\\n'), Location(None, 1, 6))
"""

CASE_MACRO_CONCAT_1 = """\
macro foo [bar]
fo${foo}in bin "ba${foo}oo"
---
(Name('fobar'), Location(None, 1, 0))
(Name('in'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 2))
(Name('bin'), Location(None, 1, 3))
(WhiteSpace(' '), Location(None, 1, 6))
(Other('"'), Location(None, 1, 7))
(Name('babar'), Location(None, 1, 8))
(Name('oo'), Location(None, 1, 0))
(Other('"'), Location(None, 1, 2))
(EndOfLine('\\n'), Location(None, 1, 3))
"""


CASE_MACRO_CONCAT_2 = """\
macro foo [o
own line
b]
fo${foo}in bin fo${foo}in
---
(Name('foo'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 3))
(Name('own'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(Name('line'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 8))
(Name('b'), Location(None, 1, 0))
(Name('in'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 2))
(Name('bin'), Location(None, 1, 3))
(WhiteSpace(' '), Location(None, 1, 6))
(Name('foo'), Location(None, 1, 7))
(EndOfLine('\\n'), Location(None, 1, 10))
(Name('own'), Location(None, 1, 0))
(WhiteSpace(' '), Location(None, 1, 3))
(Name('line'), Location(None, 1, 4))
(EndOfLine('\\n'), Location(None, 1, 8))
(Name('b'), Location(None, 1, 0))
(Name('in'), Location(None, 1, 0))
(EndOfLine('\\n'), Location(None, 1, 2))
"""

class Test(TestCase):

    maxDiff = None

    def check(self, case):
        source, expected_tokens = case.split('---\n')
        tokens = '\n'.join(str(x) for x in UntilNoneIterator(Lexer(source)))
        self.assertEqual(expected_tokens, tokens + '\n')

    def test_basic(self):
        self.check(CASE_BASIC)

    def test_comment(self):
        self.check(CASE_COMMENT)

    def test_string(self):
        self.check(CASE_STRING)

    def test_integer(self):
        self.check(CASE_INTEGER)

    def test_macro_basic(self):
        self.check(CASE_MACRO_BASIC)

    def test_macro_arg(self):
        self.check(CASE_MACRO_ARG)

    def test_macro_multiline_1(self):
        self.check(CASE_MACRO_MULTILINE_1)

    def test_macro_multiline_2(self):
        self.check(CASE_MACRO_MULTILINE_2)

    def test_macro_concat_1(self):
        self.check(CASE_MACRO_CONCAT_1)

    def test_macro_concat_2(self):
        self.check(CASE_MACRO_CONCAT_2)
