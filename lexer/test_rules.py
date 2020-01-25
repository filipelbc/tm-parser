from unittest import TestCase

from utils import RewindableStream, TupleFilter
from lexer import Lexer
from rules import E, V, N, AndRule, OrRule
from tokens import String, PositiveInteger

r_eoi = E()
r_bar = N('bar')
r_foo = N('foo')
r_str = V(String)
r_int = V(PositiveInteger)

empty_and = AndRule()
empty_or = OrRule()


class FooBar(AndRule):
    rules = [r_foo, r_bar]


class FooFoo(AndRule):
    rules = [r_foo, r_foo]


class Foo2(AndRule):
    is_repeatable = True
    rules = [r_foo]


class Foo0(AndRule):
    is_optional = True
    rules = [r_foo]


class MFoo2(AndRule):
    rules = [Foo2()]


class MFoo0(AndRule):
    rules = [Foo0()]


class FooOrBar(OrRule):
    rules = [r_foo, r_bar]


foo_bar = FooBar()
foo_foo = FooFoo()
m_foo_2 = MFoo2()
m_foo_0 = MFoo0()
foo_or_bar = FooOrBar()


class TestBottomRules(TestCase):

    def assert_match(self, token_stream, rule, e_value=None, e_is_match=True):
        is_match, value, _ = rule.match(token_stream)
        self.assertEqual(is_match, e_is_match)
        self.assertEqual(value, e_value)

    def assert_no_match(self, token_stream, rule):
        self.assert_match(token_stream, rule, e_is_match=False)

    def test_bottom_rules_1(self):
        token_s = RewindableStream(TupleFilter(Lexer('foo bar'), '_location'))

        self.assert_no_match(token_s, r_eoi)
        self.assert_no_match(token_s, r_bar)
        self.assert_match(token_s, r_foo, 'foo')

        next(token_s)  # skip the whitespace

        self.assert_match(token_s, r_bar, 'bar')
        self.assert_match(token_s, r_eoi)

    def test_bottom_rules_2(self):
        token_s = RewindableStream(TupleFilter(Lexer('1 "foo"'), '_location'))

        self.assert_no_match(token_s, r_str)
        self.assert_match(token_s, r_int, 1)

        next(token_s)  # skip the whitespace

        self.assert_no_match(token_s, r_foo)
        self.assert_match(token_s, r_str, 'foo')

    def test_and_rule(self):
        token_s = RewindableStream(TupleFilter(Lexer('foo bar'), '_location'))

        self.assert_match(token_s, empty_and)
        self.assert_no_match(token_s, foo_foo)
        self.assert_match(token_s, foo_bar, ('foo', 'bar'))

    def test_and_rule_repeatable(self):
        token_s = RewindableStream(TupleFilter(Lexer('foo foo bar'), '_location'))

        self.assert_match(token_s, m_foo_2, (('foo',), ('foo',)))

        token_s = RewindableStream(TupleFilter(Lexer('foo foo foo bar'), '_location'))

        self.assert_match(token_s, m_foo_2, (('foo',), ('foo',), ('foo',)))

    def test_and_rule_optional(self):
        token_s = RewindableStream(TupleFilter(Lexer('bar'), '_location'))

        self.assert_match(token_s, m_foo_0, None)

        token_s = RewindableStream(TupleFilter(Lexer('foo bar'), '_location'))

        self.assert_match(token_s, m_foo_0, (('foo',),))

    def test_or_rule(self):
        token_s = RewindableStream(TupleFilter(Lexer('foo bar'), '_location'))

        self.assert_no_match(token_s, empty_or)
        self.assert_match(token_s, foo_or_bar, 'foo')

        token_s = RewindableStream(TupleFilter(Lexer('bar foo'), '_location'))

        self.assert_match(token_s, foo_or_bar, 'bar')
