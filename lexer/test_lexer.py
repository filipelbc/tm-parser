from pathlib import Path
from unittest import TestCase

from utils import UntilNoneIterator

from lexer import Lexer


CASE_BASIC = """\
foo {
  bar
}
---
Name('foo')
WhiteSpace(' ')
Other('{')
EndOfLine('\\n')
WhiteSpace('  ')
Name('bar')
EndOfLine('\\n')
Other('}')
EndOfLine('\\n')
"""

CASE_WHITESPACE = """\
   foo   bar   
---
WhiteSpace('   ')
Name('foo')
WhiteSpace('   ')
Name('bar')
WhiteSpace('   ')
EndOfLine('\\n')
"""

CASE_COMMENT = """\
foo {
  # comment
  bar # another comment
}
---
Name('foo')
WhiteSpace(' ')
Other('{')
EndOfLine('\\n')
WhiteSpace('  ')
Comment(None)
EndOfLine('\\n')
WhiteSpace('  ')
Name('bar')
WhiteSpace(' ')
Comment(None)
EndOfLine('\\n')
Other('}')
EndOfLine('\\n')
"""

CASE_INTEGER = """\
foo 1 bar 123 bin88
---
Name('foo')
WhiteSpace(' ')
PositiveInteger(1)
WhiteSpace(' ')
Name('bar')
WhiteSpace(' ')
PositiveInteger(123)
WhiteSpace(' ')
Name('bin88')
EndOfLine('\\n')
"""

CASE_STRING = """\
foo "bar" bar "f\\"o\\"o" foo"bar"
---
Name('foo')
WhiteSpace(' ')
String('bar')
WhiteSpace(' ')
Name('bar')
WhiteSpace(' ')
String('f"o"o')
WhiteSpace(' ')
Name('foo')
String('bar')
EndOfLine('\\n')
"""

CASE_MULTILINE_STRING_1 = """\
foo -8<-
  a
    b
->8-
bar
---
Name('foo')
WhiteSpace(' ')
String('a\\n  b\\n')
EndOfLine('\\n')
Name('bar')
EndOfLine('\\n')
"""

CASE_MULTILINE_STRING_2 = """\
foo -8<- a
  b
   c ->8-
bar
---
Name('foo')
WhiteSpace(' ')
String('a\\n b\\n  c ')
EndOfLine('\\n')
Name('bar')
EndOfLine('\\n')
"""

CASE_MACRO_BASIC = """\
macro foo [ bar ]
${foo} bin ${foo}
---
WhiteSpace(' ')
Name('bar')
WhiteSpace('  ')
Name('bin')
WhiteSpace('  ')
Name('bar')
WhiteSpace(' ')
EndOfLine('\\n')
"""

CASE_MACRO_OPTION = """\
a ${?foo} b
---
Name('a')
WhiteSpace('  ')
Name('b')
EndOfLine('\\n')
"""

CASE_MACRO_ARG_1 = """\
macro foo [ bar ${1} ]
a ${foo "b"} c
---
Name('a')
WhiteSpace('  ')
Name('bar')
WhiteSpace(' ')
Name('b')
WhiteSpace('  ')
Name('c')
EndOfLine('\\n')
"""

CASE_MACRO_ARG_2 = """\
macro foo [b${1}r]
a ${foo "a"} c
---
Name('a')
WhiteSpace(' ')
Name('bar')
WhiteSpace(' ')
Name('c')
EndOfLine('\\n')
"""

CASE_MACRO_ARG_3 = """\
macro foo [ ${1}${2} ]
a ${foo "\\"b" "c\\""} d
---
Name('a')
WhiteSpace('  ')
String('bc')
WhiteSpace('  ')
Name('d')
EndOfLine('\\n')
"""

CASE_MACRO_ARG_4 = """\
macro foo [x ${1} y]
a ${foo -8<-
    b
    "c"
  ->8-
  "d"
}
e
---
Name('a')
WhiteSpace(' ')
Name('x')
WhiteSpace(' ')
Name('b')
EndOfLine('\\n')
String('c')
EndOfLine('\\n')
WhiteSpace(' ')
Name('y')
EndOfLine('\\n')
Name('e')
EndOfLine('\\n')
"""

CASE_MACRO_MULTILINE_1 = """\
macro foo [
  b ${2} d
  e ${1} g
]
a ${foo
     "f"
     "c"
   } h
---
Name('a')
WhiteSpace(' ')
EndOfLine('\\n')
WhiteSpace('  ')
Name('b')
WhiteSpace(' ')
Name('c')
WhiteSpace(' ')
Name('d')
EndOfLine('\\n')
WhiteSpace('  ')
Name('e')
WhiteSpace(' ')
Name('f')
WhiteSpace(' ')
Name('g')
EndOfLine('\\n')
WhiteSpace(' ')
Name('h')
EndOfLine('\\n')
"""

CASE_MACRO_MULTILINE_2 = """\
macro foo [a
  b ${2}
  d
  e ]
x ${foo
    "b"
    "c"
} y
---
Name('x')
WhiteSpace(' ')
Name('a')
EndOfLine('\\n')
WhiteSpace('  ')
Name('b')
WhiteSpace(' ')
Name('c')
EndOfLine('\\n')
WhiteSpace('  ')
Name('d')
EndOfLine('\\n')
WhiteSpace('  ')
Name('e')
WhiteSpace('  ')
Name('y')
EndOfLine('\\n')
"""

CASE_MACRO_CONCAT_1 = """\
macro foo [a]
b${foo}r x "f${foo}a"
---
Name('bar')
WhiteSpace(' ')
Name('x')
WhiteSpace(' ')
String('faa')
EndOfLine('\\n')
"""

CASE_MACRO_CONCAT_2 = """\
macro foo [a
b
o]
b${foo}r x f${foo}r
---
Name('ba')
EndOfLine('\\n')
Name('b')
EndOfLine('\\n')
Name('or')
WhiteSpace(' ')
Name('x')
WhiteSpace(' ')
Name('fa')
EndOfLine('\\n')
Name('b')
EndOfLine('\\n')
Name('or')
EndOfLine('\\n')
"""

CASE_MACRO_IN_MULTILINE_STRING = """\
macro foo [b ${1} d]
bar -8<-
a ${foo "c"}
e
->8-
---
Name('bar')
WhiteSpace(' ')
String('a b c d\\ne\\n')
EndOfLine('\\n')
"""

PCASE_INCLUDE_IN_STRING = """\
samples/a
---
Name('a')
WhiteSpace(' ')
String('ia\\nb -8<-\\nib\\n  c\\n  c\\nib\\n->8-\\nb\\nia\\n')
EndOfLine('\\n')
Name('a')
EndOfLine('\\n')
WhiteSpace('  ')
Name('b')
WhiteSpace(' ')
String('ib\\n  c\\n  c\\nib\\n')
EndOfLine('\\n')
WhiteSpace('  ')
Name('b')
EndOfLine('\\n')
"""


def with_cases(cls):
    g = globals()
    for c in g:
        if c.startswith(('CASE_', 'PCASE_')):

            def test_case(self, case=g[c], p=c.startswith('P')):
                self.run_case(case, p=p)

            setattr(cls, 'test_' + c.split('_', 1)[1].lower(), test_case)
    return cls


@with_cases
class Test(TestCase):

    maxDiff = None

    @staticmethod
    def _tokenize(source):
        return '\n'.join(str(x[0]) for x in UntilNoneIterator(Lexer(source)))

    def run_case(self, case, p):
        source, expected_tokens = case.split('---\n')
        if p:
            tokens = self._tokenize(Path(source.strip()))
        else:
            tokens = self._tokenize(source)
        self.assertEqual(expected_tokens, tokens + '\n')
