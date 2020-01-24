from unittest import TestCase

from utils import BufferedStream, TupleFilter
from lexer import Lexer
from rules import E, V, N
from tokens import String, PositiveInteger


class TestBottomRules(TestCase):

    def assert_match(self, lexer, rule, e_is_match, e_value):
        is_match, value = rule.match(lexer)
        self.assertEqual(is_match, e_is_match)
        self.assertEqual(value, e_value)

    def test_bottom_rules_1(self):
        lexer = BufferedStream(TupleFilter(Lexer('foo bar'), '_location'))

        e = E()
        n1 = N('bar')
        n2 = N('foo')

        self.assert_match(lexer, e, False, None)
        self.assert_match(lexer, n1, False, None)
        self.assert_match(lexer, n2, True, 'foo')

        next(lexer)  # skip the whitespace

        self.assert_match(lexer, n1, True, 'bar')
        self.assert_match(lexer, e, True, None)

    def test_bottom_rules_2(self):
        lexer = BufferedStream(TupleFilter(Lexer('1 "foo"'), '_location'))

        n1 = V(String)
        n2 = V(PositiveInteger)

        self.assert_match(lexer, n1, False, None)
        self.assert_match(lexer, n2, True, 1)

        next(lexer)  # skip the whitespace

        self.assert_match(lexer, n1, True, 'foo')
