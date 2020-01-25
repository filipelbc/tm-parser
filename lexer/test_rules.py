from unittest import TestCase

from utils import RewindableStream, TupleFilter
from lexer import Lexer
from rules import E, V, N, C, AndRule, OrRule
from tokens import String, PositiveInteger

r_eoi = E()
r_bar = N('bar')
r_foo = N('foo')
r_str = V(String)
r_int = V(PositiveInteger)
r_ob = C('{')
r_lte = C('<=')

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


class FooOrBar2(AndRule):
    is_repeatable = True
    rules = [FooOrBar()]


class ThisFooBar(AndRule):
    rules = [N('this'), C('{'), FooOrBar2(), C('}'), E()]


foo_bar = FooBar()
foo_foo = FooFoo()
m_foo_2 = MFoo2()
m_foo_0 = MFoo0()
foo_or_bar = FooOrBar()
this_foo_bar = ThisFooBar()


def _make_token_stream(text):
    return RewindableStream(TupleFilter(Lexer(text), '_location'))


class TestBottomRules(TestCase):

    def assert_match(self, token_stream, rule, e_value=None, e_is_match=True):
        is_match, value, _ = rule.match(token_stream)
        self.assertEqual(is_match, e_is_match)
        self.assertEqual(value, e_value)

    def assert_no_match(self, token_stream, rule):
        self.assert_match(token_stream, rule, e_is_match=False)

    def test_bottom_rules_1(self):
        token_s = _make_token_stream('foo bar')

        self.assert_no_match(token_s, r_eoi)
        self.assert_no_match(token_s, r_bar)
        self.assert_match(token_s, r_foo, 'foo')

        next(token_s)  # skip the whitespace

        self.assert_match(token_s, r_bar, 'bar')
        self.assert_match(token_s, r_eoi)

    def test_bottom_rules_2(self):
        token_s = _make_token_stream('1 "foo"')

        self.assert_no_match(token_s, r_str)
        self.assert_match(token_s, r_int, 1)

        next(token_s)  # skip the whitespace

        self.assert_no_match(token_s, r_foo)
        self.assert_match(token_s, r_str, 'foo')

    def test_bottom_rules_3(self):
        token_s = _make_token_stream('<=')

        self.assert_no_match(token_s, r_ob)
        self.assert_match(token_s, r_lte, '<=')

    def test_and_rule(self):
        token_s = _make_token_stream('foo bar')

        self.assert_match(token_s, empty_and)
        self.assert_no_match(token_s, foo_foo)
        self.assert_match(token_s, foo_bar, ('foo', 'bar'))

    def test_and_rule_repeatable(self):
        token_s = _make_token_stream('foo foo bar')

        self.assert_match(token_s, m_foo_2, (('foo',), ('foo',)))

        token_s = _make_token_stream('foo foo foo bar')

        self.assert_match(token_s, m_foo_2, (('foo',), ('foo',), ('foo',)))

    def test_and_rule_optional(self):
        token_s = _make_token_stream('bar')

        self.assert_match(token_s, m_foo_0, None)

        token_s = _make_token_stream('foo bar')

        self.assert_match(token_s, m_foo_0, (('foo',),))

    def test_or_rule(self):
        token_s = _make_token_stream('foo bar')

        self.assert_no_match(token_s, empty_or)
        self.assert_match(token_s, foo_or_bar, 'foo')

        token_s = _make_token_stream('bar foo')

        self.assert_match(token_s, foo_or_bar, 'bar')

        token_s = _make_token_stream('wololo')

        self.assert_no_match(token_s, foo_or_bar)

    def test_composed_rule(self):
        token_s = _make_token_stream('this { no }')

        self.assert_no_match(token_s, this_foo_bar)

        token_s = _make_token_stream('this { foo bar }  ')

        self.assert_match(token_s, this_foo_bar, ('this', '{', ('foo',), ('bar',), '}', None))
