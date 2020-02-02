from unittest import TestCase

from ..lexer import lex
from ..lexer.tokens import String, PositiveInteger

from .base_rules import E, V, N, C, AndRule, OrRule

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


class Foo(AndRule):
    rules = [r_foo]


class Foo2(AndRule):
    rules = [Foo(repeatable=True)]


class Foo0(AndRule):
    rules = [Foo(optional=True)]


class FooOrBar(OrRule):
    rules = [r_foo, r_bar]


class ThisBrace(AndRule):
    rules = [N('this'), C('{')]


class ThisBraceNoSkip(ThisBrace):
    tokens_to_skip = ()


class ThisFooBar(AndRule):
    rules = [N('this'), C('{'), FooOrBar(repeatable=True), C('}'), E()]


foo_bar = FooBar()
foo_foo = FooFoo()
foo_2 = Foo2()
foo_0 = Foo0()
foo_or_bar = FooOrBar()
this_brace = ThisBrace()
this_brace_no_skip = ThisBraceNoSkip()
this_brace_optional_skip = ThisBrace(optional_skip=True)
this_foo_bar = ThisFooBar()


class TestBottomRules(TestCase):

    def assert_match(self, token_stream, rule, e_value=None, e_is_match=True):
        is_match, value, _ = rule.match(None, token_stream)
        self.assertEqual(is_match, e_is_match)
        self.assertEqual(value, e_value)

    def assert_no_match(self, token_stream, rule):
        self.assert_match(token_stream, rule, e_is_match=False)

    def test_bottom_rules_1(self):
        token_s = lex('foo bar')

        self.assert_no_match(token_s, r_eoi)
        self.assert_no_match(token_s, r_bar)
        self.assert_match(token_s, r_foo, 'foo')

        next(token_s)  # skip the whitespace

        self.assert_match(token_s, r_bar, 'bar')
        self.assert_match(token_s, r_eoi)

    def test_bottom_rules_2(self):
        token_s = lex('1 "foo"')

        self.assert_no_match(token_s, r_str)
        self.assert_match(token_s, r_int, 1)

        next(token_s)  # skip the whitespace

        self.assert_no_match(token_s, r_foo)
        self.assert_match(token_s, r_str, 'foo')

    def test_bottom_rules_3(self):
        token_s = lex('<=')

        self.assert_no_match(token_s, r_ob)
        self.assert_match(token_s, r_lte, '<=')

    def test_and_rule(self):
        token_s = lex('foo bar')

        self.assert_match(token_s, empty_and)
        self.assert_no_match(token_s, foo_foo)
        self.assert_match(token_s, foo_bar, ('foo', 'bar'))

    def test_and_rule_skip(self):
        token_s = lex('this {')
        self.assert_no_match(token_s, this_brace_no_skip)
        self.assert_match(token_s, this_brace, ('this', '{'))

        token_s = lex('this{')
        self.assert_no_match(token_s, this_brace)
        self.assert_match(token_s, this_brace_no_skip, ('this', '{'))

        token_s = lex('this{')
        self.assert_match(token_s, this_brace_optional_skip, ('this', '{'))

    def test_and_rule_repeatable(self):
        token_s = lex('foo foo bar')

        self.assert_match(token_s, foo_2, (('foo',), ('foo',)))

        token_s = lex('foo foo foo bar')

        self.assert_match(token_s, foo_2, (('foo',), ('foo',), ('foo',)))

    def test_and_rule_optional(self):
        token_s = lex('bar')

        self.assert_match(token_s, foo_0, None)

        token_s = lex('foo bar')

        self.assert_match(token_s, foo_0, (('foo',),))

    def test_or_rule(self):
        token_s = lex('foo bar')

        self.assert_no_match(token_s, empty_or)
        self.assert_match(token_s, foo_or_bar, 'foo')

        token_s = lex('bar foo')

        self.assert_match(token_s, foo_or_bar, 'bar')

        token_s = lex('wololo')

        self.assert_no_match(token_s, foo_or_bar)

    def test_composed_rule(self):
        token_s = lex('this { no }')

        self.assert_no_match(token_s, this_foo_bar)

        token_s = lex('this { foo bar }  ')

        self.assert_match(token_s, this_foo_bar, ('this', '{', 'foo', 'bar', '}', None))
